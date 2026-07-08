"""Table scores — une ligne par passage (répétable pour l'éval de cohérence §5.4)."""
import uuid
from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class Score(Base, UUIDPk, Timestamped):
    __tablename__ = "scores"

    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"))
    total: Mapped[float] = mapped_column(Float)
    subscores: Mapped[dict] = mapped_column(JSONB, default=dict)
    verdict: Mapped[str] = mapped_column(String(30))  # SHORTLIST|POOL|DECLINE_PENDING
    justification: Mapped[str] = mapped_column(String)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(30))
    run_seed: Mapped[int] = mapped_column(Integer, default=0)

    application: Mapped["Application"] = relationship(back_populates="scores")
