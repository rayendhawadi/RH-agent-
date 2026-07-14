"""
POST /chat/webhook/whatsapp, POST /chat/{conv_id}/message, GET /chat/{conv_id}
— Annexe D. A5 pré-qualification conversationnelle (§6-A5).
"""
from __future__ import annotations

import uuid

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.conversation import Conversation, Message
from app.services.messaging.service import normalize_phone
from app.services.prescreening.dialogue import start_conversation, process_incoming

logger = logging.getLogger("welyne.a5.webhook")
settings = get_settings()

router = APIRouter(prefix="/chat", tags=["prescreening"])


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    role: str
    body: str

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    channel: str
    status: str
    language: str
    extracted: dict
    flags: list
    messages: list[MessageOut]

    class Config:
        from_attributes = True


@router.post("/applications/{application_id}/start", response_model=ConversationOut)
def start(application_id: uuid.UUID, channel: str | None = None, db: Session = Depends(get_db)):
    """
    Démarre un dialogue A5 pour une candidature SHORTLISTED/PRESCREENING (déclenché par A0/A7).
    Sans `channel` explicite, le canal est choisi automatiquement (email > whatsapp > web).
    """
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    conv = start_conversation(db, application, channel=channel)
    return conv


@router.get("/applications/{application_id}/latest", response_model=ConversationOut | None)
def get_latest_for_application(application_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrouve la conversation A5 la plus récente d'une candidature (pour l'UI dashboard)."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.application_id == application_id)
        .order_by(Conversation.created_at.desc())
        .first()
    )
    return conv


@router.get("/{conv_id}", response_model=ConversationOut)

def get_conversation(conv_id: uuid.UUID, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conv


@router.post("/{conv_id}/message", response_model=ConversationOut)
def post_message(conv_id: uuid.UUID, body: MessageIn, db: Session = Depends(get_db)):
    """Canal chat web (widget portail candidat)."""
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return process_incoming(db, conv, body.text)


def _find_open_whatsapp_conversation(db: Session, phone: str) -> Conversation | None:
    """
    Conversation OPEN canal=whatsapp la plus récente pour ce numéro. Cherche
    d'abord par `external_ref` (posé à l'ouverture, voir dialogue.py), puis
    par téléphone candidat en repli (conversation ouverte avant que le
    numéro n'ait été rattaché au candidat par A3).
    """
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.channel == "whatsapp",
            Conversation.status == "OPEN",
            Conversation.external_ref == phone,
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if conv:
        return conv

    candidates_with_phone = (
        db.query(Candidate)
        .filter(Candidate.phone.isnot(None))
        .all()
    )
    match = next((c for c in candidates_with_phone if normalize_phone(c.phone) == phone), None)
    if not match:
        return None
    return (
        db.query(Conversation)
        .join(Application, Application.id == Conversation.application_id)
        .filter(
            Conversation.channel == "whatsapp",
            Conversation.status == "OPEN",
            Application.candidate_id == match.id,
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )


@router.get("/webhook/whatsapp")
def verify_whatsapp_webhook(request: Request):
    """
    Handshake de vérification exigé par Meta à la configuration du webhook
    (dashboard developers.facebook.com) : renvoie `hub.challenge` tel quel si
    `hub.verify_token` correspond à WHATSAPP_VERIFY_TOKEN, sinon 403.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN and challenge is not None:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Vérification webhook WhatsApp échouée")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Reçoit le payload natif de l'API Meta WhatsApp Business Cloud (messages
    entrants). Format (simplifié) :
      entry[].changes[].value.messages[] = [{from, text: {body}}, ...]
    Le numéro `from` (sans '+', format Meta) est normalisé puis utilisé pour
    retrouver la conversation OPEN correspondante — aucun conversation_id
    n'est envoyé par Meta, contrairement au widget web.
    """
    payload = await request.json()
    treated = 0
    skipped: list[str] = []

    entries = payload.get("entry", []) if isinstance(payload, dict) else []
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue  # médias/boutons non gérés en MVP (§6-A5 : texte libre)
                sender = normalize_phone(message.get("from", ""))
                text = message.get("text", {}).get("body", "")
                if not sender or not text:
                    continue
                conv = _find_open_whatsapp_conversation(db, sender)
                if not conv:
                    logger.warning(
                        "Message WhatsApp reçu de %s sans conversation OPEN correspondante — ignoré.",
                        sender,
                    )
                    skipped.append(sender)
                    continue
                process_incoming(db, conv, text)
                treated += 1

    # Meta exige un 200 rapide, même si aucun message pertinent n'a été trouvé,
    # sous peine de désactivation automatique du webhook après échecs répétés.
    return {"status": "ok", "treated": treated, "skipped": skipped}