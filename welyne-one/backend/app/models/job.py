"""Table jobs — fiche de poste. job_spec produit par l'agent A1 (Annexe A1)."""
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class Job(Base, UUIDPk, Timestamped):
    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft|published|closed
    job_spec: Mapped[dict] = mapped_column(JSONB, default=dict)       # schéma JobSpec
    weights: Mapped[dict] = mapped_column(JSONB, default=dict)        # pondérations par critère
    # Catégorie de gabarit d'onboarding (§6-A8) choisie par le recruteur à la
    # création de l'offre (ou plus tard). NULL = pas encore choisie -> A8
    # retombe sur la détection auto par mot-clé du titre (compat offres
    # existantes, cf. services/generation/onboarding_checklist.py).
    onboarding_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    applications: Mapped[list["Application"]] = relationship(back_populates="job")
