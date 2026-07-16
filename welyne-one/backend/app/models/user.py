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

    # §7 sécurité comptes — voir app/core/mailer.py et app/api/auth.py.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Posé par l'admin lors d'une réinitialisation forcée (POST /users/{id}/reset-password) :
    # le mot de passe temporaire fonctionne pour se connecter UNE fois, mais le frontend
    # doit alors forcer un changement via POST /auth/change-password avant de laisser
    # continuer — évite qu'un mot de passe temporaire circulant par email reste valide indéfiniment.
    password_reset_required: Mapped[bool] = mapped_column(Boolean, default=False)