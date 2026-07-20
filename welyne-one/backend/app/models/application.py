"""
Table applications — pivot candidat x offre. `status` = machine à états A0 (§2.1).
`stage_history` conserve chaque transition (redondant avec audit_log, mais rapide à lire).
"""
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped

# Valeurs valides — répliquées ici pour validation Python (voir orchestrator/state_machine.py)
APPLICATION_STATUSES = (
    "RECEIVED", "PARSED", "SCORED",
    "SHORTLISTED", "POOL", "DECLINE_PENDING", "DECLINED",
    "PRESCREENING", "PRESCREENED",
    "INTERVIEW_SCHEDULED", "INTERVIEWED",
    "OFFER", "HIRED", "ONBOARDING",
    "NEEDS_ATTENTION",
)


class Application(Base, UUIDPk, Timestamped):
    __tablename__ = "applications"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED", index=True)
    source: Mapped[str] = mapped_column(String(50), default="upload")  # upload|email|linkedin_assist...
    stage_history: Mapped[list] = mapped_column(JSONB, default=list)
    # Archivage réversible (masque des vues par défaut sans effacer l'historique/RGPD,
    # contrairement à la suppression définitive — voir DELETE /applications/{id}).
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="applications")
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    documents: Mapped[list["Document"]] = relationship(back_populates="application")
    profile: Mapped["CandidateProfileRow"] = relationship(back_populates="application", uselist=False)
    scores: Mapped[list["Score"]] = relationship(back_populates="application")
