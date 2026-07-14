"""
Config Celery — jobs de fond (parsing/scoring en lot). Sans Docker : lancez un
Redis local (`redis-server`) puis `celery -A app.celery_app worker --loglevel=info`.
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "welyne_one",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.orchestrator.tasks", "app.services.prescreening.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Africa/Tunis",
    enable_utc=True,
    task_acks_late=True,          # ne pas perdre une tâche si le worker crashe (CA A0)
    worker_prefetch_multiplier=1,
)

# Tâches périodiques A5 (§6-A5) — nécessite un worker Celery beat en plus du
# worker classique : `celery -A app.celery_app beat --loglevel=info`.
celery_app.conf.beat_schedule = {
    "a5-check-prescreen-timeouts": {
        "task": "prescreen.check_timeouts",
        "schedule": 3600.0,  # toutes les heures ; 48h est le seuil métier, pas la fréquence du check
    },
    "a5-poll-prescreen-emails": {
        "task": "prescreen.poll_emails",
        "schedule": float(settings.PRESCREEN_EMAIL_POLL_SECONDS),
    },
}

# Upstash (et tout Redis managé) exposent Redis en TLS via l'URL "rediss://".
# Celery/kombu exigent une config SSL explicite dans ce cas, sinon le worker
# ne démarre pas. Sans impact si REDIS_URL est en "redis://" classique (local).
if settings.CELERY_BROKER_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": "required"}
if settings.CELERY_RESULT_BACKEND.startswith("rediss://"):
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": "required"}