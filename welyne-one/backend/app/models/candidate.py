"""Table candidates — identité dédupliquée (hash email/téléphone normalisés)."""
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class Candidate(Base, UUIDPk, Timestamped):
    __tablename__ = "candidates"

    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    links: Mapped[list] = mapped_column(JSONB, default=list)
    pii_masked_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")
