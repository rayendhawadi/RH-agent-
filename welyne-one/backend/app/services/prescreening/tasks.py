"""
Tâches Celery périodiques de l'agent A5 (§6-A5), enregistrées dans le
beat_schedule de celery_app.py :
  - check_timeouts() : relance à 48h puis PRESCREEN_INCOMPLETE.
  - poll_prescreen_emails() : relevé de la boîte IMAP dédiée aux réponses
    candidats par email (voir email_poller.py).
"""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.prescreening.dialogue import check_timeouts
from app.services.prescreening.email_poller import poll_prescreen_emails

logger = logging.getLogger("welyne.a5.tasks")


@celery_app.task(name="prescreen.check_timeouts")
def check_prescreen_timeouts_task() -> int:
    db = SessionLocal()
    try:
        treated = check_timeouts(db)
        if treated:
            logger.info("A5 timeouts: %s conversation(s) traitée(s).", treated)
        return treated
    finally:
        db.close()


@celery_app.task(name="prescreen.poll_emails")
def poll_prescreen_emails_task() -> int:
    db = SessionLocal()
    try:
        treated = poll_prescreen_emails(db)
        if treated:
            logger.info("A5 email poll: %s réponse(s) traitée(s).", treated)
        return treated
    finally:
        db.close()