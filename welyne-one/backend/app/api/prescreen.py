"""
POST /chat/webhook/whatsapp, POST /chat/{conv_id}/message, GET /chat/{conv_id}
— Annexe D. A5 pré-qualification conversationnelle (§6-A5).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.application import Application
from app.models.conversation import Conversation, Message
from app.services.prescreening.dialogue import start_conversation, process_incoming

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
    extracted: dict
    flags: list
    messages: list[MessageOut]

    class Config:
        from_attributes = True


@router.post("/applications/{application_id}/start", response_model=ConversationOut)
def start(application_id: uuid.UUID, channel: str = "web", db: Session = Depends(get_db)):
    """Démarre un dialogue A5 pour une candidature SHORTLISTED/PRESCREENING (déclenché par A0/A7)."""
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    conv = start_conversation(db, application, channel=channel)
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


class WhatsAppWebhookIn(BaseModel):
    conversation_id: uuid.UUID  # résolu en amont via external_ref (mapping numéro -> conv) en phase 3
    text: str


@router.post("/webhook/whatsapp")
def whatsapp_webhook(payload: WhatsAppWebhookIn, db: Session = Depends(get_db)):
    conv = db.get(Conversation, payload.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    conv = process_incoming(db, conv, payload.text)
    return {"status": conv.status}