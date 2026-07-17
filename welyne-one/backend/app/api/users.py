"""
Gestion des comptes utilisateurs - reserve au role admin.
Complete scripts/seed_admin.py (qui ne cree qu'un admin en CLI) : ici on peut
creer recruteur/lecteur, lister, et desactiver un compte sans le supprimer
(tracabilite - coherent avec S7 : rien n'est efface sans raison explicite).

Toute mutation de compte (creation, changement de role, activation/
desactivation, reinitialisation de mot de passe) ecrit une ligne dans
audit_log - S7 : "le journal d'audit prouve qui a decide quoi, quand".
"""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, normalize_email
from app.auth.security import hash_password, generate_secure_token
from app.core.mailer import send_account_email
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

# "admin" n'est JAMAIS assignable via l'API, même par un admin — uniquement
# via scripts/seed_admin.py côté serveur.
ASSIGNABLE_ROLES = ("recruteur", "lecteur")


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    email_verified: bool
    password_reset_required: bool

    class Config:
        from_attributes = True


class CreateUserIn(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "recruteur"


class UpdateUserRoleIn(BaseModel):
    role: str


class ResetPasswordOut(BaseModel):
    temporary_password: str


def _log(db: Session, actor: User, action: str, target: User, payload: dict | None = None) -> None:
    db.add(AuditLog(
        entity="user", entity_id=target.id, action=action,
        actor=f"user:{actor.email}", payload=payload or {},
    ))


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _user: User = Depends(require_role("admin"))):
    return db.query(User).order_by(User.created_at).all()


@router.post("", response_model=UserOut)
def create_user(body: CreateUserIn, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    if body.role not in ASSIGNABLE_ROLES:
    raise HTTPException(status_code=400, detail=f"Role invalide. Attendu : {', '.join(ASSIGNABLE_ROLES)}")

    email = normalize_email(body.email)
    # Comparaison normalisee : avant ce correctif, "admin@Welyne.com" et
    # "admin@welyne.com" etaient vus comme deux comptes distincts, ce qui
    # permettait de contourner ce controle "email deja utilise".
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Un compte existe deja avec cet email")

    verification_token = generate_secure_token()
    new_user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
        email_verified=False,
        verification_token=verification_token,
    )
    db.add(new_user)
    db.flush()  # obtient new_user.id avant l'audit log

    _log(db, user, "created", new_user, payload={"role": new_user.role, "email": new_user.email})
    db.commit()
    db.refresh(new_user)

    verify_link = f"{_frontend_base_url()}/verify-email?token={verification_token}"
    send_account_email(
        new_user.email, "Confirmez votre adresse email",
        f"Bonjour {new_user.full_name or ''},\n\n"
        f"Un compte Welyne One ({new_user.role}) a ete cree pour vous.\n"
        f"Confirmez votre adresse email ici : {verify_link}\n\n"
        f"L'equipe Welyne",
    )
    return new_user


def _frontend_base_url() -> str:
    from app.core.config import get_settings
    return get_settings().FRONTEND_BASE_URL


@router.patch("/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: uuid.UUID, body: UpdateUserRoleIn,
    db: Session = Depends(get_db), current: User = Depends(require_role("admin")),
):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role invalide. Attendu : {', '.join(ROLES)}")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    old_role = target.role
    target.role = body.role
    db.add(target)
    _log(db, current, "role_changed", target, payload={"from": old_role, "to": body.role})
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/toggle-active", response_model=UserOut)
def toggle_active(user_id: uuid.UUID, db: Session = Depends(get_db), current: User = Depends(require_role("admin"))):
    """Active/desactive un compte. Ne supprime jamais (tracabilite via audit_log)."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if target.id == current.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas desactiver votre propre compte")

    target.is_active = not target.is_active
    db.add(target)
    _log(db, current, "activated" if target.is_active else "deactivated", target)
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/reset-password", response_model=ResetPasswordOut)
def reset_password(user_id: uuid.UUID, db: Session = Depends(get_db), current: User = Depends(require_role("admin"))):
    """
    Admin force un nouveau mot de passe temporaire (l'utilisateur oublie le
    sien et n'a aujourd'hui aucun moyen de le recuperer lui-meme). Le
    compte est marque password_reset_required=True : au prochain login, le
    frontend doit rediriger vers /auth/change-password avant de laisser
    continuer, pour que ce mot de passe temporaire ne reste jamais valide
    durablement.
    """
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    temporary_password = secrets.token_urlsafe(9)  # ~12 caracteres lisibles
    target.password_hash = hash_password(temporary_password)
    target.password_reset_required = True
    db.add(target)
    _log(db, current, "password_reset", target)
    db.commit()

    send_account_email(
        target.email, "Reinitialisation de votre mot de passe",
        f"Bonjour {target.full_name or ''},\n\n"
        f"Un administrateur a reinitialise votre mot de passe.\n"
        f"Mot de passe temporaire : {temporary_password}\n\n"
        f"Connectez-vous puis changez-le immediatement (vous y serez invite).\n\n"
        f"L'equipe Welyne",
    )
    return ResetPasswordOut(temporary_password=temporary_password)