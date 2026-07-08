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
        if settings.SMTP_HOST and channel == "email":
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