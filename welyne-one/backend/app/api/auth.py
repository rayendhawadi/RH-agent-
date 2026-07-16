"""POST /auth/login, POST /auth/change-password, GET /auth/verify-email (§Annexe D, §7)."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, normalize_email
from app.auth.security import verify_password, hash_password, create_access_token
from app.core.rate_limit import is_rate_limited
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 300  # 10 tentatives / 5 min / IP — large pour ne pas gêner un usage normal


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    password_reset_required: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class VerifyEmailResponse(BaseModel):
    verified: bool


def _client_ip(request: Request) -> str:
    # Derriere un proxy/reverse-proxy (deploiement prod), X-Forwarded-For
    # porte la vraie IP cliente ; en dev sans proxy, request.client suffit.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    # §7 - sans ceci, un brute-force de mot de passe etait possible sans
    # aucune friction (aucune limite de tentatives). Fenetre glissante
    # simple par IP, fail-open si Redis est indisponible (voir rate_limit.py).
    if is_rate_limited(f"login:{ip}", LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives de connexion. Reessayez dans quelques minutes.",
        )

    email = normalize_email(body.email)
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte desactive")

    return LoginResponse(
        access_token=create_access_token(user),
        role=user.role,
        password_reset_required=user.password_reset_required,
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Self-service : un utilisateur connecte change son propre mot de passe.
    Absent jusqu'ici - un utilisateur ne pouvait ni changer son mot de passe
    ni sortir d'un mot de passe temporaire pose par un admin
    (POST /users/{id}/reset-password) sans repasser par l'admin.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe actuel incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit faire au moins 8 caracteres")

    user.password_hash = hash_password(body.new_password)
    user.password_reset_required = False
    db.add(user)
    db.commit()
    return {"status": "ok"}


@router.get("/verify-email", response_model=VerifyEmailResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Confirme la possession de l'adresse email d'un compte cree par un admin
    (POST /users). Le lien est envoye a la creation (voir app/api/users.py).
    Ne bloque pas la connexion si non verifie (l'admin a deja vouche pour le
    compte) - c'est un signal de confiance additionnel, pas une porte dure,
    tant qu'il n'existe pas d'inscription libre (auto-registration) sur
    cette plateforme.
    """
    user = db.query(User).filter(User.verification_token == token).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Lien de verification invalide ou deja utilise")
    user.email_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    return VerifyEmailResponse(verified=True)
