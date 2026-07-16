"""
Gestion des comptes utilisateurs — réservé au rôle admin.
Complète scripts/seed_admin.py (qui ne crée qu'un admin en CLI) : ici on peut
créer recruteur/lecteur, lister, et désactiver un compte sans le supprimer
(traçabilité — cohérent avec §7 : rien n'est effacé sans raison explicite).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.auth.security import hash_password
from app.models.user import ROLES, User

router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class CreateUserIn(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "recruteur"


class UpdateUserRoleIn(BaseModel):
    role: str


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _user: User = Depends(require_role("admin"))):
    return db.query(User).order_by(User.created_at).all()


@router.post("", response_model=UserOut)
def create_user(body: CreateUserIn, db: Session = Depends(get_db), _user: User = Depends(require_role("admin"))):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle invalide. Attendu : {', '.join(ROLES)}")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Un compte existe déjà avec cet email")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserOut)
def update_role(user_id: uuid.UUID, body: UpdateUserRoleIn, db: Session = Depends(get_db), _user: User = Depends(require_role("admin"))):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Rôle invalide. Attendu : {', '.join(ROLES)}")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.role = body.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/toggle-active", response_model=UserOut)
def toggle_active(user_id: uuid.UUID, db: Session = Depends(get_db), current: User = Depends(require_role("admin"))):
    """Active/désactive un compte. Ne supprime jamais (traçabilité de l'audit_log intacte)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")
    user.is_active = not user.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user