"""Tâche Celery — digest hebdomadaire A9. Enregistrée dans app.celery_app.beat_schedule."""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.reporting.digest import send_weekly_digest

logger = logging.getLogger("welyne.a9.tasks")


@celery_app.task(name="reports.send_weekly_digest")
def send_weekly_digest_task() -> int:
    db = SessionLocal()
    try:
        return send_weekly_digest(db)
    finally:
        db.close()