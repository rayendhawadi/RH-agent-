"""Table users — auth JWT + rôles (admin/recruteur/lecteur)."""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped

ROLES = ("admin", "recruteur", "lecteur")


class User(Base, UUIDPk, Timestamped):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="recruteur")
    full_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # désactivation sans suppression (traçabilité)
