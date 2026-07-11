"""
Tables conversations/messages — A5 pré-qualification conversationnelle (§4, §6-A5).
Une Conversation = un fil de screening pour une candidature (canal web/email/whatsapp).
Message = chaque tour (candidat ou agent), append-only.
"""
import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped

CONVERSATION_STATUSES = ("OPEN", "COMPLETED", "PRESCREEN_INCOMPLETE", "FLAGGED")


class Conversation(Base, UUIDPk, Timestamped):
    __tablename__ = "conversations"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), default="web")  # web|email|whatsapp
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    plan: Mapped[list] = mapped_column(JSONB, default=list)          # questions générées (slots)
    extracted: Mapped[dict] = mapped_column(JSONB, default=dict)     # réponses fusionnées au profil
    flags: Mapped[list] = mapped_column(JSONB, default=list)         # contradictions / signaux
    consent_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_sent_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    external_ref: Mapped[str] = mapped_column(String(255), nullable=True)  # id thread WhatsApp/email

    application: Mapped["Application"] = relationship()
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")


class Message(Base, UUIDPk, Timestamped):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(10))          # agent|candidate|system
    body: Mapped[str] = mapped_column(Text, default="")
    slot_id: Mapped[str] = mapped_column(String(50), nullable=True)  # question ciblée, si applicable

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")