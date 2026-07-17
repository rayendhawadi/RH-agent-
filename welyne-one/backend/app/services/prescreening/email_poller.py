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


import tempfile
import os

_LAST_UID_PATH = os.path.join(tempfile.gettempdir(), "welyne_a5_last_uid.txt")


def _load_last_uid() -> int:
    try:
        with open(_LAST_UID_PATH, "r") as f:
            return int(f.read().strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


def _save_last_uid(uid: int) -> None:
    try:
        with open(_LAST_UID_PATH, "w") as f:
            f.write(str(uid))
    except OSError as exc:  # noqa: BLE001 — ne doit jamais casser le poll
        logger.warning("Impossible d'enregistrer le dernier UID traité (%s) : %s", uid, exc)


def fetch_unseen_replies() -> list[tuple[str, str]]:
    """
    Se connecte à la boîte IMAP dédiée aux réponses A5 et retourne les
    (adresse_expediteur, texte_du_message) reçus depuis le dernier poll.

    IMPORTANT : on ne se base plus sur le flag \\Seen pour la déduplication
    (voir historique — une lecture webmail le fausse silencieusement). On
    suit à la place le dernier UID IMAP traité (entier croissant, stable) :
    à chaque poll, on ne va chercher QUE les messages dont l'UID est
    strictement supérieur au dernier traité — jamais un scan complet de la
    boîte (qui serait lent et pourrait bloquer le worker sur une grosse
    boîte mail).
    """
    if not (settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASS):
        raise ImapNotConfigured("IMAP_HOST/IMAP_USER/IMAP_PASS absents de la config (.env).")

    last_uid = _load_last_uid()
    results: list[tuple[str, str]] = []
    imap_cls = imaplib.IMAP4_SSL if settings.IMAP_USE_SSL else imaplib.IMAP4
    conn = imap_cls(settings.IMAP_HOST, settings.IMAP_PORT)
    try:
        conn.login(settings.IMAP_USER, settings.IMAP_PASS)
        conn.select(settings.IMAP_MAILBOX)

        if last_uid == 0:
            # Premier lancement : on ne traite pas tout l'historique de la
            # boîte, seulement ce qui arrivera à partir de maintenant.
            status, uidnext_data = conn.status(settings.IMAP_MAILBOX, "(UIDNEXT)")
            uidnext = 1
            if status == "OK" and uidnext_data:
                raw = uidnext_data[0].decode() if isinstance(uidnext_data[0], bytes) else str(uidnext_data[0])
                digits = "".join(ch for ch in raw.split("UIDNEXT")[-1] if ch.isdigit())
                uidnext = int(digits) if digits else 1
            _save_last_uid(uidnext - 1)
            return results

        status, data = conn.uid("search", None, f"UID {last_uid + 1}:*")
        if status != "OK" or not data or not data[0]:
            return results

        max_uid = last_uid
        for uid_bytes in data[0].split():
            uid = int(uid_bytes.decode())
            if uid <= last_uid:  # certains serveurs renvoient le dernier UID connu même s'il n'y a rien de neuf
                continue
            status, msg_data = conn.uid("fetch", str(uid), "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            _, sender = parseaddr(_decode(msg.get("From")))
            body = _extract_plain_text(msg)
            if sender and body:
                results.append((sender.strip().lower(), body))
            max_uid = max(max_uid, uid)
        _save_last_uid(max_uid)
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001 — la déconnexion ne doit jamais casser le poll
            pass
    return results


def _find_open_conversation(db: Session, sender_email: str) -> Conversation | None:
    """
    Conversation OPEN canal=email la plus récente pour cet expéditeur —
    UNIQUEMENT si la candidature est encore PRESCREENING.

    Sans ce 2e filtre, une réponse à N'IMPORTE QUEL AUTRE email Welyne (accusé
    A3, confirmation d'entretien A6, bienvenue onboarding A8...) — la boîte
    IMAP relevée ici est partagée, seul A5 a un poller entrant — peut se faire
    aspirer par ce matcher si une conversation est restée techniquement OPEN
    (ex. incohérence de statut, double-canal) alors que le pipeline a déjà
    avancé bien au-delà de la pré-qualification. On vérifie donc explicitement
    que Application.status == "PRESCREENING" avant de router quoi que ce soit
    vers le dialogue A5 (bug observé : réponse à l'email d'onboarding relancée
    dans une conversation de prescreen complétée depuis longtemps).
    """
    from app.models.candidate import Candidate
    from app.models.application import Application

    conv = (
        db.query(Conversation)
        .join(Application, Application.id == Conversation.application_id)
        .filter(
            Conversation.channel == "email",
            Conversation.status == "OPEN",
            Conversation.external_ref == sender_email,
            Application.status == "PRESCREENING",
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if conv:
        return conv

    # Repli : candidat dont l'email correspond, au cas où external_ref n'a
    # pas pu être renseigné à l'ouverture (ex. conversation créée avant que
    # A3 ait rattaché l'email au candidat). Même garde-fou sur le statut.
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
            Application.status == "PRESCREENING",
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
        logger.warning("DEBUG A5: aucun candidat en base avec email='%s'", sender_email)
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
        all_apps = db.query(Application).filter(Application.candidate_id == candidate.id).all()
        logger.warning(
            "DEBUG A5: candidat %s trouvé (id=%s) mais aucune application SHORTLISTED/PRESCREENING. "
            "Applications existantes et statuts: %s",
            sender_email, candidate.id, [(a.id, a.status) for a in all_apps],
        )
        return None

    already_screened = (
        db.query(Conversation).filter(Conversation.application_id == application.id).first()
    )
    if already_screened:
        logger.warning(
            "DEBUG A5: application %s a déjà une conversation (id=%s, channel=%s, status=%s) — pas de double-démarrage",
            application.id, already_screened.id, already_screened.channel, already_screened.status,
        )
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