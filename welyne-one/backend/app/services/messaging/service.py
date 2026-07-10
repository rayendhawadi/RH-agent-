"""
Service de messagerie (§5.2) — point de passage unique pour email/WhatsApp.
Ne rend que des templates approuvés, personnalisation LLM bornée à 2 phrases,
journalise TOUT dans message_log, rate-limit 1 message/4h/candidat (hors accusés).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.message_log import MessageLog
from app.services.messaging.templates import render_template
from app.services.messaging.whatsapp import WhatsAppSendError, send_whatsapp_text

logger = logging.getLogger("welyne.messaging")
settings = get_settings()

RATE_LIMIT_EXEMPT = {"ack"}  # accusés = seul envoi entièrement automatique et non limité
RATE_LIMIT_WINDOW = timedelta(hours=4)


def _rate_limited(db: Session, to: str) -> bool:
    since = datetime.now(timezone.utc) - RATE_LIMIT_WINDOW
    recent = (
        db.query(MessageLog)
        .filter(MessageLog.to == to, MessageLog.created_at >= since)
        .count()
    )
    return recent >= 1


def personalize_note(context: dict) -> str:
    """
    Emplacement borné de personnalisation LLM (max 2 phrases, ton encadré).
    Best-effort : en cas d'échec (pas de clé API, etc.), renvoie une chaîne vide
    plutôt que de bloquer l'envoi du message.
    """
    try:
        from app.services.llm_gateway import complete

        system = (
            "Rédige EXACTEMENT 1 à 2 phrases professionnelles et bienveillantes "
            "pour accompagner un email de rejet de candidature. Pas de promesses, "
            "pas de détails inventés. Réponds uniquement avec ces phrases."
        )
        user = f"Poste : {context.get('job_title', '')}. Candidat : {context.get('candidate_name', '')}."
        return complete("chat", system, user, temperature=0.3, seed=None, trace_name="a7/personalize@v1").strip()
    except Exception as exc:  # noqa: BLE001 — jamais bloquant
        logger.debug("Personnalisation A7 indisponible : %s", exc)
        return ""


def send_message(
    db: Session,
    application_id,
    to: str,
    template_id: str,
    context: dict,
    *,
    language: str = "fr",
    channel: str = "email",
    validated_by: str = "system",
) -> MessageLog:
    if template_id != "ack" and _rate_limited(db, to):
        entry = MessageLog(
            application_id=application_id, to=to, channel=channel,
            template_id=template_id, rendered_body="", status="skipped_rate_limit",
            validated_by=validated_by,
        )
        db.add(entry)
        db.commit()
        return entry

    body = render_template(template_id, language, context)
    status = "sent"
    try:
        if channel == "whatsapp":
            if settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_ID:
                _send_whatsapp(to, body)
            else:
                logger.info("[DEV] WhatsApp '%s' à %s :\n%s", template_id, to, body)
        elif settings.SMTP_HOST and channel == "email":
            _send_smtp(to, template_id, body)
        else:
            logger.info("[DEV] Message '%s' à %s :\n%s", template_id, to, body)
    except Exception as exc:  # noqa: BLE001 — on journalise même en cas d'échec d'envoi
        logger.warning("Échec d'envoi (%s) : %s", template_id, exc)
        status = "failed"

    entry = MessageLog(
        application_id=application_id, to=to, channel=channel,
        template_id=template_id, rendered_body=body, status=status,
        validated_by=validated_by,
    )
    db.add(entry)
    db.commit()
    return entry


def _send_smtp(to: str, subject: str, body: str) -> None:
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = f"Welyne — {subject}"
    msg["From"] = settings.SMTP_USER
    msg["To"] = to

    with smtplib.SMTP(settings.SMTP_HOST, 587) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)


def _send_whatsapp(to: str, body: str) -> None:
    """
    `to` doit être un numéro E.164 sans '+' (ex: '21612345678'). Si le candidat
    a stocké son téléphone avec '+' ou espaces, on normalise a minima ici.
    """
    normalized = to.replace("+", "").replace(" ", "").replace("-", "")
    try:
        send_whatsapp_text(normalized, body)
    except WhatsAppSendError as exc:
        # on relance pour que send_message() marque bien status="failed"
        raise RuntimeError(str(exc)) from exc


def resolve_recipient(candidate) -> tuple[str, str] | None:
    """
    Choisit le canal d'envoi pour un candidat : email en priorité (canal
    principal, §5.2), repli WhatsApp si aucun email n'est renseigné mais
    qu'un téléphone existe. Retourne None si ni l'un ni l'autre n'est
    disponible (aucun message ne peut être envoyé).

    Utilisé par tous les endpoints api/ qui appellent send_message(), pour
    éviter de dupliquer `if candidate.email: ... elif candidate.phone: ...`
    dans chaque fichier.
    """
    email = getattr(candidate, "email", None)
    if email:
        return "email", email
    phone = getattr(candidate, "phone", None)
    if phone:
        return "whatsapp", phone
    return None