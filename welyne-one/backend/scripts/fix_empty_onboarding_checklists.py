#!/usr/bin/env python
"""
Répare les candidatures passées en ONBOARDING avant l'application de la
migration 0011 / le seed des RoleTemplate — generate_checklist() avait
échoué silencieusement (table absente, ou role_templates vide) et n'a
jamais été rejoué depuis (la transition HIRED -> ONBOARDING ne se
redéclenche pas d'elle-même).

Sûr à relancer plusieurs fois : generate_checklist() est idempotent, une
candidature qui a déjà des tâches est laissée intacte.

Prérequis : avoir lancé scripts/seed_role_templates.py avant (sinon les
gabarits sont vides et rien ne sera généré, comme au départ).

Usage : python scripts/fix_empty_onboarding_checklists.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.application import Application  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.onboarding_task import OnboardingTask  # noqa: E402
from app.services.generation.onboarding_checklist import generate_checklist  # noqa: E402


def main():
    db = SessionLocal()
    try:
        stuck = (
            db.query(Application)
            .filter(Application.status == "ONBOARDING")
            .filter(~db.query(OnboardingTask.id)
                    .filter(OnboardingTask.application_id == Application.id)
                    .exists())
            .all()
        )
        if not stuck:
            print("Aucune candidature bloquée trouvée.")
            return

        still_empty = []
        for app_ in stuck:
            job = db.get(Job, app_.job_id)
            tasks = generate_checklist(db, app_.id, job)
            print(f"{app_.id} ({job.title if job else '?'}) -> {len(tasks)} tâche(s) générée(s)")
            if not tasks:
                still_empty.append(app_.id)

        if still_empty:
            print(f"\n⚠ {len(still_empty)} candidature(s) toujours à 0 tâche : "
                  "avez-vous bien lancé scripts/seed_role_templates.py avant ?")
    finally:
        db.close()


if __name__ == "__main__":
    main()