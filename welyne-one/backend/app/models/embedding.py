"""Table embeddings — pgvector, sections de fiche de poste + profil (bge-m3, 1024 dim)."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.models._base import UUIDPk


class Embedding(Base, UUIDPk):
    __tablename__ = "embeddings"

    owner_type: Mapped[str] = mapped_column(String(30))   # job | candidate_profile
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    section: Mapped[str] = mapped_column(String(50))       # ex: "skills", "experience"
    vector: Mapped[list[float]] = mapped_column(Vector(1024))
