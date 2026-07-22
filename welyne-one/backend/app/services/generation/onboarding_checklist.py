"""
Service A8, mission 1 — checklist personnalisée (§6-A8).

Pas de LLM ici (délibéré, cf. §6-A8 "moteur de checklist") : on choisit un
RoleTemplate par mot-clé sur le titre du poste, et chaque ligne du template
devient une ligne OnboardingTask en base. Simple, prévisible, auditable —
un admin ajuste un template sans toucher au code.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.onboarding_task import OnboardingTask
from app.models.role_template import RoleTemplate

# Mots-clés (minuscules, sans accent) -> catégorie de gabarit. Premier match
# gagne ; "general" sert de repli si rien ne correspond ou si le gabarit
# choisi n'existe pas encore en base (jamais bloquant).
_CATEGORY_KEYWORDS = {
    "engineering": ["ingenieur", "developpeur", "devops", "data", "backend", "frontend", "mlops"],
    "sales": ["commercial", "vente", "sales", "account executive"],
}


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def pick_role_category(job_title: str) -> str:
    title = _strip_accents(job_title.lower())
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return category
    return "general"


def generate_checklist(db: Session, application_id, job: Job) -> list[OnboardingTask]:
    """Idempotent : si des tâches existent déjà pour cette candidature (ex.
    onboarding redémarré), ne duplique rien."""
    existing = db.query(OnboardingTask).filter(OnboardingTask.application_id == application_id).first()
    if existing:
        return db.query(OnboardingTask).filter(OnboardingTask.application_id == application_id).all()

    category = pick_role_category(job.title if job else "")
    template = db.query(RoleTemplate).filter_by(role_category=category).first()
    if template is None:
        template = db.query(RoleTemplate).filter_by(role_category="general").first()
    if template is None:
        # Aucun gabarit configuré du tout (avant premier seed) : ne bloque
        # jamais la transition HIRED -> ONBOARDING pour autant, juste pas de
        # checklist tant qu'un admin n'a pas lancé scripts/seed_role_templates.py.
        return []

    tasks: list[OnboardingTask] = []
    for doc in template.required_documents:
        tasks.append(OnboardingTask(application_id=application_id, task=f"Déposer {doc}", kind="document", owner="candidate"))
    for acc in template.accounts_to_create:
        tasks.append(OnboardingTask(application_id=application_id, task=f"Créer accès {acc}", kind="account", owner="rh"))
    for eq in template.equipment:
        tasks.append(OnboardingTask(application_id=application_id, task=f"Commander {eq}", kind="equipment", owner="rh"))
    for item in template.week_one_agenda:
        tasks.append(OnboardingTask(application_id=application_id, task=item, kind="agenda", owner="rh"))

    db.add_all(tasks)
    db.commit()
    for t in tasks:
        db.refresh(t)
    return tasks