"""
Agent A6 — Planification d'entretiens (§6-A6). Logique coeur : proposer des
créneaux, réserver, replanifier, annuler, marquer no-show. Toujours stocké en
UTC (CA « sûr côté fuseaux horaires ») ; l'affichage candidat utilise
`candidate_tz` (IANA) uniquement à la génération du texte de message.
"""
from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.orchestrator.state_machine import transition
from app.services.messaging.service import resolve_language, resolve_recipient, send_message
from app.services.scheduling import calcom
from app.services.scheduling.ics import build_ics

logger = logging.getLogger("welyne.a6")
settings = get_settings()

_DAY_NAMES_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_DAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _local(dt: datetime, tz: str) -> datetime:
    try:
        return dt.astimezone(ZoneInfo(tz))
    except Exception:  # noqa: BLE001 — TZ invalide fournie par le client -> repli défaut
        return dt.astimezone(ZoneInfo("Africa/Tunis"))


def _fmt_slot(dt: datetime, tz: str, lang: str) -> str:
    local_dt = _local(dt, tz)
    names = _DAY_NAMES_EN if lang == "en" else _DAY_NAMES_FR
    day_name = names[local_dt.weekday()]
    return f"{day_name} {local_dt.strftime('%d/%m %H:%M')} ({tz})"


class SchedulingError(Exception):
    pass


def propose_interview_slots(db: Session, application: Application, user_email: str, candidate_tz: str | None = None) -> Interview:
    if application.status != "PRESCREENED":
        raise SchedulingError("La candidature doit être PRESCREENED pour proposer un entretien.")

    slots = calcom.get_available_slots(3)
    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    tz = candidate_tz or "Africa/Tunis"
    lang = resolve_language(db, application.id)

    interview = Interview(
        application_id=application.id,
        status="PROPOSED",
        proposed_slots=[{"start": s["start"].isoformat(), "end": s["end"].isoformat()} for s in slots],
        candidate_tz=tz,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        options_text = "\n".join(
            f"{i + 1}. {_fmt_slot(s['start'], tz, lang)}" for i, s in enumerate(slots)
        )
        booking_link = f"{settings.FRONTEND_BASE_URL}/interviews/{interview.id}/book"
        send_message(
            db, application.id, to, "invite_interview",
            {
                "candidate_name": candidate.full_name,
                "job_title": job.title if job else "",
                "booking_link": booking_link,
                "slot_options": options_text,
            },
            language=lang, channel=channel, validated_by=user_email,
        )

    transition(db, application, "INTERVIEW_SCHEDULED", actor=f"user:{user_email}", payload={"interview_id": str(interview.id)})
    return interview


def _send_ics_invite(to_email: str, interview: Interview, candidate_name: str, job_title: str, subject: str, body_text: str) -> None:
    ics = build_ics(
        uid=f"welyne-interview-{interview.id}",
        start=interview.slot_start, end=interview.slot_end,
        summary=f"Entretien — {job_title}",
        description=body_text.replace("\n", "\\n"),
        attendee_email=to_email,
    )
    if not settings.SMTP_HOST:
        logger.info("[DEV] ICS (pas de SMTP configuré) pour %s :\n%s", to_email, ics)
        return
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = to_email
        msg.attach(MIMEText(body_text))
        ics_part = MIMEText(ics, "calendar;method=REQUEST")
        ics_part.add_header("Content-Disposition", "attachment", filename="entretien.ics")
        msg.attach(ics_part)
        with smtplib.SMTP(settings.SMTP_HOST, 587) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 — jamais bloquant : le RDV reste booké même si l'ICS échoue
        logger.warning("Envoi ICS échoué pour %s : %s", to_email, exc)


def book_interview(
    db: Session, interview: Interview, application: Application, user_email: str,
    start: datetime, end: datetime, candidate_tz: str | None = None,
) -> Interview:
    if interview.status not in ("PROPOSED", "RESCHEDULED"):
        raise SchedulingError("Cet entretien n'est pas en attente de réservation.")
    if start.tzinfo is None or end.tzinfo is None:
        raise SchedulingError("Les horaires doivent être fournis avec fuseau (ISO 8601 + offset).")
    if end <= start:
        raise SchedulingError("L'heure de fin doit être après l'heure de début.")

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    ref = calcom.create_booking(start, end, candidate.full_name if candidate else "", getattr(candidate, "email", None))

    interview.slot_start = start.astimezone(timezone.utc)
    interview.slot_end = end.astimezone(timezone.utc)
    interview.calendar_ref = ref
    interview.status = "BOOKED"
    if candidate_tz:
        interview.candidate_tz = candidate_tz
    db.add(interview)
    db.commit()
    db.refresh(interview)

    lang = resolve_language(db, application.id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        when = _fmt_slot(interview.slot_start, interview.candidate_tz, lang)
        body = (
            f"Entretien confirmé pour {when}." if lang != "en" else f"Interview confirmed for {when}."
        )
        send_message(
            db, application.id, to, "interview_confirmed",
            {"candidate_name": candidate.full_name if candidate else "", "job_title": job.title if job else "", "slot_text": when},
            language=lang, channel=channel, validated_by=user_email,
        )
        if channel == "email":
            _send_ics_invite(to, interview, candidate.full_name if candidate else "", job.title if job else "", "Entretien — invitation", body)

    return interview


def reschedule_interview(db: Session, interview: Interview, application: Application, user_email: str, start: datetime, end: datetime, reason: str = "") -> Interview:
    if interview.status not in ("BOOKED", "PROPOSED"):
        raise SchedulingError("Seul un entretien réservé ou proposé peut être replanifié.")
    if start.tzinfo is None or end.tzinfo is None:
        raise SchedulingError("Les horaires doivent être fournis avec fuseau (ISO 8601 + offset).")

    if interview.calendar_ref:
        calcom.reschedule_booking(interview.calendar_ref, start, end)
    else:
        interview.calendar_ref = calcom.create_booking(start, end, "", None)

    interview.slot_start = start.astimezone(timezone.utc)
    interview.slot_end = end.astimezone(timezone.utc)
    interview.status = "BOOKED"
    interview.reschedule_count += 1
    interview.candidate_reminder_sent_at = None
    interview.recruiter_reminder_sent_at = None
    db.add(interview)
    db.commit()
    db.refresh(interview)

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    lang = resolve_language(db, application.id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        when = _fmt_slot(interview.slot_start, interview.candidate_tz, lang)
        send_message(
            db, application.id, to, "interview_rescheduled",
            {"candidate_name": candidate.full_name if candidate else "", "job_title": job.title if job else "", "slot_text": when, "reason": reason},
            language=lang, channel=channel, validated_by=user_email,
        )
    return interview


def cancel_interview(db: Session, interview: Interview, application: Application, user_email: str, reason: str = "") -> Interview:
    if interview.status not in ("BOOKED", "PROPOSED"):
        raise SchedulingError("Cet entretien ne peut pas être annulé (statut actuel).")
    if interview.calendar_ref:
        calcom.cancel_booking(interview.calendar_ref, reason)

    interview.status = "CANCELLED"
    interview.cancel_reason = reason
    db.add(interview)
    db.commit()
    db.refresh(interview)

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    lang = resolve_language(db, application.id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "interview_cancelled",
            {"candidate_name": candidate.full_name if candidate else "", "job_title": job.title if job else "", "reason": reason},
            language=lang, channel=channel, validated_by=user_email,
        )
    return interview


def mark_no_show(db: Session, interview: Interview, application: Application, user_email: str) -> Interview:
    if interview.status != "BOOKED":
        raise SchedulingError("Seul un entretien réservé peut être marqué no-show.")
    interview.status = "NO_SHOW"
    db.add(interview)
    db.commit()
    db.refresh(interview)
    # No-show n'est pas un rejet automatique (§7 : aucun rejet sans clic humain) —
    # la candidature part en NEEDS_ATTENTION pour décision recruteur explicite.
    from app.orchestrator.state_machine import route_to_needs_attention
    route_to_needs_attention(db, application, reason="interview_no_show", actor=f"user:{user_email}")
    return interview


def mark_completed(db: Session, interview: Interview, application: Application, user_email: str) -> Application:
    if interview.status != "BOOKED":
        raise SchedulingError("Seul un entretien réservé peut être marqué comme passé.")
    interview.status = "COMPLETED"
    db.add(interview)
    db.commit()
    return transition(db, application, "INTERVIEWED", actor=f"user:{user_email}")