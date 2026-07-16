"""
Emails liés aux COMPTES (vérification d'email, notifications admin) — à ne
pas confondre avec le service de messagerie candidat (A7,
app/services/messaging/service.py) qui exige un application_id et journalise
dans message_log. Ici il n'y a ni candidature ni template Jinja : juste un
envoi SMTP direct, avec le même repli [DEV] en logs si SMTP_HOST est vide
(cohérent avec le comportement du reste de la plateforme en environnement
de dev sans SMTP configuré).
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger("welyne.accounts.mailer")
settings = get_settings()


def send_account_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("[DEV] Email compte '%s' à %s :\n%s", subject, to, body)
        return

    msg = MIMEText(body)
    msg["Subject"] = f"Welyne — {subject}"
    msg["From"] = settings.SMTP_USER
    msg["To"] = to

    try:
        with smtplib.SMTP(settings.SMTP_HOST, 587) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 — un échec d'envoi ne doit jamais bloquer la création du compte
        logger.warning("Échec d'envoi email compte (%s) à %s : %s", subject, to, exc)