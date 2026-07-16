"""Réexport pratique des dépendances FastAPI communes."""
from app.core.database import get_db
from app.auth.security import get_current_user, require_role, normalize_email

__all__ = ["get_db", "get_current_user", "require_role", "normalize_email"]
