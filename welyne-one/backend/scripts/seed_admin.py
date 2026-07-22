#!/usr/bin/env python
"""
Crée (ou met à jour) le compte admin initial. Idempotent : relancé sur un
email déjà présent, met juste à jour le mot de passe/rôle plutôt que de
planter — pratique pour réinitialiser un accès admin perdu.

Usage : python scripts/seed_admin.py admin@welyne.com "MotDePasseSolide123"

Reconstruit après avoir été écrasé par erreur (le contenu qui se trouvait
sous ce nom de fichier était en réalité scripts/seed_role_templates.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.security import hash_password  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print('Usage : python scripts/seed_admin.py admin@welyne.com "MotDePasseSolide123"')
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]
    if len(password) < 8:
        print("Le mot de passe doit faire au moins 8 caractères.")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role="admin",
                full_name="Admin",
                is_active=True,
                email_verified=True,        # compte de bootstrap : pas de boucle de
                                             # verification email necessaire pour le 1er admin
                password_reset_required=False,
            )
            db.add(user)
            db.commit()
            print(f"Compte admin cree : {email}")
        else:
            user.password_hash = hash_password(password)
            user.role = "admin"
            user.is_active = True
            db.add(user)
            db.commit()
            print(f"Compte existant mis a jour (mot de passe reinitialise, role=admin) : {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()