"""
Table onboarding_tasks (§4 de la spec — jamais créée avant ce correctif).
Une ligne = une tâche de checklist A8, générée à partir d'un RoleTemplate au
moment où l'application passe HIRED -> ONBOARDING (voir services/onboarding).
"""
import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped

TASK_KINDS = ("document", "account", "equipment", "agenda")
TASK_OWNERS = ("candidate", "rh")  # qui doit agir — détermine ce qui apparaît sur le portail candidat
TASK_STATUSES = ("PENDING", "SUBMITTED", "DONE", "REJECTED")


class OnboardingTask(Base, UUIDPk, Timestamped):
    __tablename__ = "onboarding_tasks"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True
    )
    task: Mapped[str] = mapped_column(String(255))          # libellé, ex. "Déposer CIN"
    kind: Mapped[str] = mapped_column(String(20))            # document|account|equipment|agenda
    owner: Mapped[str] = mapped_column(String(20))           # candidate|rh
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)