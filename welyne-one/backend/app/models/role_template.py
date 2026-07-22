"""
Table role_templates (§6-A8) — un gabarit par grande catégorie de poste
("engineering", "sales"...), géré en base par un admin. A8 pioche dedans au
moment de générer la checklist d'un candidat HIRED (voir services/onboarding).
Volontairement PAS de LLM ici : un moteur de checklist, pas un générateur
créatif (cf. §6-A8 "moteur de checklist").
"""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class RoleTemplate(Base, UUIDPk, Timestamped):
    __tablename__ = "role_templates"

    role_category: Mapped[str] = mapped_column(String(50), unique=True)
    required_documents: Mapped[list] = mapped_column(JSONB, default=list)   # ["CIN", "RIB", ...]
    equipment: Mapped[list] = mapped_column(JSONB, default=list)            # ["Laptop dev", ...]
    accounts_to_create: Mapped[list] = mapped_column(JSONB, default=list)   # ["Email", "GitHub", ...]
    week_one_agenda: Mapped[list] = mapped_column(JSONB, default=list)      # ["Intro équipe", ...]