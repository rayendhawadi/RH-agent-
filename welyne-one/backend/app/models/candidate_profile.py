"""Table candidate_profiles — sortie A3, schéma CandidateProfile (Annexe A)."""
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class CandidateProfileRow(Base, UUIDPk, Timestamped):
    __tablename__ = "candidate_profiles"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), unique=True
    )
    profile: Mapped[dict] = mapped_column(JSONB, default=dict)   # CandidateProfile JSON
    language: Mapped[str] = mapped_column(String(5), default="fr")
    parser_version: Mapped[str] = mapped_column(String(30), default="a3@v1")

    application: Mapped["Application"] = relationship(back_populates="profile")
