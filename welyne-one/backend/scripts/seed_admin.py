#!/usr/bin/env python
"""
Crée le premier compte admin. Usage :
    python scripts/seed_admin.py admin@welyne.com "motdepasse-fort"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.auth.security import hash_password  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print("Usage : python scripts/seed_admin.py <email> <mot_de_passe>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"L'utilisateur {email} existe déjà.")
            return
        user = User(email=email, password_hash=hash_password(password), role="admin", full_name="Admin")
        db.add(user)
        db.commit()
        print(f"Admin créé : {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
