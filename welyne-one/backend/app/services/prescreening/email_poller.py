"""
Canal "email" de l'agent A5 (§6-A5 / §4 conversations.channel).

Contrairement au widget web (réponse directe sur /chat/{conv_id}/message) et
au webhook WhatsApp (push temps réel de Meta), l'email n'a pas de webhook
entrant simple à exploiter en MVP : on relève donc périodiquement une boîte
IMAP dédiée (même principe que le poll IMAP prévu pour A3 sur les CV, §6-A3),
et on route chaque réponse vers `process_incoming()` comme n'importe quel
autre canal.

Matching réponse -> conversation : par adresse expéditeur, sur la conversation
la plus récente encore OPEN dont `external_ref` (ou, à défaut, l'email du
candidat) correspond. Pas de threading par Message-ID / In-Reply-To en MVP —
un candidat n'a normalement qu'une seule pré-qualification OPEN à la fois.
"""
from __future__ import annotations

import email
import imaplib
import logging
from email.header import decode_header
from email.utils import parseaddr

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.services.prescreening.dialogue import process_incoming, start_conversation

logger = logging.getLogger("welyne.a5.email")
settings = get_settings()


class ImapNotConfigured(Exception):
    """Levée si IMAP_HOST/IMAP_USER/IMAP_PASS manquent — poll ignoré, pas fatal."""


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        out.append(text.decode(enc or "utf-8", errors="replace") if isinstance(text, bytes) else text)
    return "".join(out)


def _extract_plain_text(msg: email.message.Message) -> str:
    """Préfère text/plain ; retombe sur un strip HTML minimal sinon."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace").strip()
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                html = part.get_payload(decode=True).decode(charset, errors="replace")
                return _strip_html(html)
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True) or b""
    text = payload.decode(charset, errors="replace")
    if msg.get_content_type() == "text/html":
        return _strip_html(text)
    return text.strip()


def _strip_html(html: str) -> str:
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_unseen_replies() -> list[tuple[str, str]]:
    """
    Se connecte à la boîte IMAP dédiée aux réponses A5 et retourne les
    (adresse_expediteur, texte_du_message) non encore lus. Les messages
    récupérés sont marqués \\Seen par le FETCH lui-même (pas de BODY.PEEK) :
    c'est notre mécanisme de déduplication, un message n'est traité qu'une fois.
    """
    if not (settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASS):
        raise ImapNotConfigured("IMAP_HOST/IMAP_USER/IMAP_PASS absents de la config (.env).")

    results: list[tuple[str, str]] = []
    imap_cls = imaplib.IMAP4_SSL if settings.IMAP_USE_SSL else imaplib.IMAP4
    conn = imap_cls(settings.IMAP_HOST, settings.IMAP_PORT)
    try:
        conn.login(settings.IMAP_USER, settings.IMAP_PASS)
        conn.select(settings.IMAP_MAILBOX)
        status, data = conn.search(None, "UNSEEN")
        if status != "OK":
            return results
        for num in data[0].split():
            status, msg_data = conn.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            _, sender = parseaddr(_decode(msg.get("From")))
            body = _extract_plain_text(msg)
            if sender and body:
                results.append((sender.strip().lower(), body))
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001 — la déconnexion ne doit jamais casser le poll
            pass
    return results


def _find_open_conversation(db: Session, sender_email: str) -> Conversation | None:
    """Conversation OPEN canal=email la plus récente pour cet expéditeur."""
    from app.models.candidate import Candidate
    from app.models.application import Application

    conv = (
        db.query(Conversation)
        .filter(
            Conversation.channel == "email",
            Conversation.status == "OPEN",
            Conversation.external_ref == sender_email,
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if conv:
        return conv

    # Repli : candidat dont l'email correspond, au cas où external_ref n'a
    # pas pu être renseigné à l'ouverture (ex. conversation créée avant que
    # A3 ait rattaché l'email au candidat).
    candidate = db.query(Candidate).filter(Candidate.email == sender_email).first()
    if not candidate:
        return None
    return (
        db.query(Conversation)
        .join(Application, Application.id == Conversation.application_id)
        .filter(
            Conversation.channel == "email",
            Conversation.status == "OPEN",
            Application.candidate_id == candidate.id,
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )


def _find_or_start_conversation(db: Session, sender_email: str) -> Conversation | None:
    """
    1) conversation OPEN existante (candidat a cliqué le lien web, ou a déjà
       répondu une fois par email) -> on continue le fil.
    2) sinon : le candidat a répondu directement dans sa boîte mail SANS
       jamais cliquer sur le lien "chat/{id}" de l'invitation A7. Dans ce
       cas aucune Conversation n'existe encore en base. On démarre alors la
       pré-qualification à la volée (comme le ferait un clic sur le lien),
       uniquement si sa candidature est SHORTLISTED ou PRESCREENING (statut
       déjà posé par invite-prescreen avant toute conversation, cf.
       api/applications.py) et n'a encore aucune
       conversation (pour ne jamais relancer un screening déjà terminé).
    """
    conv = _find_open_conversation(db, sender_email)
    if conv:
        return conv

    from app.models.candidate import Candidate
    from app.models.application import Application

    candidate = db.query(Candidate).filter(Candidate.email == sender_email).first()
    if not candidate:
        return None

    application = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate.id,
            Application.status.in_(("SHORTLISTED", "PRESCREENING")),
        )
        .order_by(Application.created_at.desc())
        .first()
    )
    if not application:
        return None

    already_screened = (
        db.query(Conversation).filter(Conversation.application_id == application.id).first()
    )
    if already_screened:
        return None  # un screening existe déjà (autre canal, ou déjà complété) : pas de double-démarrage

    logger.info(
        "Réponse email de %s sans lien cliqué au préalable — démarrage auto du screening (application %s).",
        sender_email, application.id,
    )
    return start_conversation(db, application, channel="email")


def poll_prescreen_emails(db: Session) -> int:
    """
    À appeler périodiquement (Celery beat, cf. PRESCREEN_EMAIL_POLL_SECONDS).
    Relève la boîte, route chaque réponse vers process_incoming() — en
    démarrant le screening à la volée si besoin (voir
    _find_or_start_conversation) — et retourne le nombre de messages
    traités. Ne lève jamais si IMAP n'est pas configuré (dev sans boîte
    mail) : retourne 0.
    """
    try:
        replies = fetch_unseen_replies()
    except ImapNotConfigured:
        logger.debug("Poll email A5 ignoré : IMAP non configuré.")
        return 0
    except Exception as exc:  # noqa: BLE001 — jamais fatal pour le beat
        logger.warning("Échec du relevé IMAP A5 : %s", exc)
        return 0

    treated = 0
    for sender_email, body in replies:
        conv = _find_or_start_conversation(db, sender_email)
        if not conv:
            logger.warning(
                "Réponse email A5 reçue de %s sans candidature éligible correspondante — ignorée.",
                sender_email,
            )
            continue
        process_incoming(db, conv, body)
        treated += 1
    return treated