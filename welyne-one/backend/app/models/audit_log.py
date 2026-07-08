"""Table audit_log — append-only, source de vérité sur qui a fait quoi (§2.1, §7)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk


class AuditLog(Base, UUIDPk):
    __tablename__ = "audit_log"

    entity: Mapped[str] = mapped_column(String(50))          # application, job, ...
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(80))          # ex: "status:RECEIVED->PARSED"
    actor: Mapped[str] = mapped_column(String(100))          # "agent:a3" ou "user:<email>"
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
