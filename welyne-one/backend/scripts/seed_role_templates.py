#!/usr/bin/env python
"""
Crée les gabarits d'onboarding par défaut (§6-A8). Idempotent : relance sans
risque, un role_category déjà présent est laissé tel quel (pas d'écrasement
d'une config déjà ajustée par un admin).
Usage : python scripts/seed_role_templates.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.role_template import RoleTemplate  # noqa: E402

DEFAULTS = [
    {
        "role_category": "engineering",
        "required_documents": ["CIN", "RIB", "Diplôme", "Contrat signé"],
        "equipment": ["Laptop dev", "Accès VPN", "Licence IDE"],
        "accounts_to_create": ["Email", "GitHub", "Slack", "Jira"],
        "week_one_agenda": ["Intro équipe", "Setup environnement dev", "1:1 avec le manager"],
    },
    {
        "role_category": "sales",
        "required_documents": ["CIN", "RIB", "Diplôme", "Contrat signé"],
        "equipment": ["Laptop", "Téléphone pro"],
        "accounts_to_create": ["Email", "CRM", "Slack"],
        "week_one_agenda": ["Intro équipe", "Formation produit", "Shadowing d'un appel client"],
    },
    {
        "role_category": "general",
        "required_documents": ["CIN", "RIB", "Diplôme", "Contrat signé"],
        "equipment": ["Laptop"],
        "accounts_to_create": ["Email", "Slack"],
        "week_one_agenda": ["Intro équipe", "1:1 avec le manager"],
    },
]


def main():
    db = SessionLocal()
    try:
        created = 0
        for tpl in DEFAULTS:
            if db.query(RoleTemplate).filter_by(role_category=tpl["role_category"]).first():
                continue
            db.add(RoleTemplate(**tpl))
            created += 1
        db.commit()
        print(f"{created} gabarit(s) créé(s) ({len(DEFAULTS) - created} déjà présents).")
    finally:
        db.close()


if __name__ == "__main__":
    main()