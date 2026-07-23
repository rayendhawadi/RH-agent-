"""
Tâche Celery de l'orchestrateur A0 — déclenche le graphe LangGraph
(app/orchestrator/graph.py) qui enchaîne parsing (A3) et scoring (A4) en un
seul run checkpointé (§2.1, §3).

Célery reste le mécanisme de file d'attente + retry (backoff, 3 tentatives) ;
LangGraph + son checkpointer Postgres gèrent la résilience *à l'intérieur*
d'une tentative : reprendre après un crash ne rejoue pas un noeud déjà
commité en base.

Lancement local sans Docker :
    celery -A app.celery_app worker --loglevel=info

Nom de tâche et signature d'appel INCHANGÉS (`parse_application.delay(...)`)
pour ne pas casser les 3 endroits qui la déclenchent (applications.py,
sourcing.py x2) — seule l'implémentation interne change.
"""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.orchestrator.graph import run_pipeline
from app.orchestrator.state_machine import route_to_needs_attention

logger = logging.getLogger("welyne.orchestrator.tasks")

MAX_ATTEMPTS = 3


@celery_app.task(bind=True, max_retries=MAX_ATTEMPTS, default_retry_delay=5)
def parse_application(self, application_id: str):
    """Déclenche le graphe A0 (parse -> score) pour une candidature."""
    try:
        run_pipeline(application_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec pipeline A0 (graphe) application %s", application_id)
        if self.request.retries >= MAX_ATTEMPTS - 1:
            db = SessionLocal()
            application = db.get(Application, application_id)
            if application is not None:
                route_to_needs_attention(db, application, f"pipeline A0 : {exc}")
            db.close()
        else:
            raise self.retry(exc=exc)


# Alias conservé : d'anciens appels référençaient parfois ce nom directement
# (`score_application_task.delay(...)`) — désormais un no-op explicite, le
# scoring fait partie intégrante du graphe déclenché par parse_application.
# Si un appelant existe encore quelque part, il vaut mieux un log clair
# qu'un échec silencieux.
@celery_app.task(name="score_application_task")
def score_application_task(application_id: str):
    logger.warning(
        "score_application_task appelée directement pour %s — obsolète depuis la migration "
        "LangGraph (le scoring fait partie du graphe déclenché par parse_application). "
        "Vérifier l'appelant.",
        application_id,
    )