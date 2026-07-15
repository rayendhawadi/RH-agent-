"""
Table interviews — agent A6 (§6-A6, §4). Une ligne = un entretien pour une
candidature. `slot_start`/`slot_end` sont TOUJOURS stockés en UTC (CA §6-A6
« sûr côté fuseaux horaires »); `candidate_tz` garde le fuseau IANA du
candidat pour le ré-affichage / les rappels.
"""
import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped

INTERVIEW_STATUSES = (
    "PROPOSED",     # créneaux envoyés au candidat, en attente de choix
    "BOOKED",       # créneau confirmé (Cal.com ou repli interne)
    "RESCHEDULED",  # a existé, remplacé par une nouvelle ligne/valeurs (garde l'historique via stage_history)
    "CANCELLED",
    "COMPLETED",    # entretien passé, marqué par le recruteur (-> INTERVIEWED)
    "NO_SHOW",
)


class Interview(Base, UUIDPk, Timestamped):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PROPOSED", index=True)

    # Créneaux proposés (avant choix candidat) — liste de {"start": iso_utc, "end": iso_utc}
    proposed_slots: Mapped[list] = mapped_column(JSONB, default=list)

    # Créneau retenu (UTC, aware) — nul tant que non réservé
    slot_start: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    slot_end: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)

    # Fuseau du candidat (IANA, ex. "Africa/Tunis", "Europe/Paris") — détecté
    # côté portail (Intl.DateTimeFormat) ou déclaré au choix du créneau.
    candidate_tz: Mapped[str] = mapped_column(String(64), default="Africa/Tunis")
    recruiter_tz: Mapped[str] = mapped_column(String(64), default="Africa/Tunis")

    # Référence externe : uid de booking Cal.com, ou "internal:<uuid>" en repli
    # sans Cal.com configuré (§3 kit de survie tiers gratuits).
    calendar_ref: Mapped[str] = mapped_column(String(255), nullable=True)

    cancel_reason: Mapped[str] = mapped_column(Text, default="")
    reschedule_count: Mapped[int] = mapped_column(default=0)

    # Anti-doublon des rappels 24h (§6-A6) : un rappel par côté par entretien.
    candidate_reminder_sent_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
    recruiter_reminder_sent_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)

    application: Mapped["Application"] = relationship()