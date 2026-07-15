"""
Tâches périodiques A6 (§6-A6) : rappel 24h avant l'entretien, des deux côtés
(candidat + recruteur). Enregistrée dans le beat_schedule de celery_app.py.
Idempotent : chaque colonne *_reminder_sent_at n'est écrite qu'une fois par
entretien (reset à None lors d'une replanification, cf. scheduler.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.job import Job
from app.services.messaging.service import resolve_language, resolve_recipient, send_message

logger = logging.getLogger("welyne.a6.tasks")

REMINDER_WINDOW_START = timedelta(hours=23)
REMINDER_WINDOW_END = timedelta(hours=25)


@celery_app.task(name="interviews.send_reminders")
def send_interview_reminders_task() -> int:
    db = SessionLocal()
    sent = 0
    try:
        now = datetime.now(timezone.utc)
        window_from = now + REMINDER_WINDOW_START
        window_to = now + REMINDER_WINDOW_END

        due = (
            db.query(Interview)
            .filter(
                Interview.status == "BOOKED",
                Interview.slot_start >= window_from,
                Interview.slot_start <= window_to,
            )
            .all()
        )
        for interview in due:
            application = db.get(Application, interview.application_id)
            if application is None:
                continue
            candidate = db.get(Candidate, application.candidate_id)
            job = db.get(Job, application.job_id)
            lang = resolve_language(db, application.id)

            if not interview.candidate_reminder_sent_at:
                recipient = resolve_recipient(candidate) if candidate else None
                if recipient:
                    channel, to = recipient
                    send_message(
                        db, application.id, to, "interview_reminder",
                        {
                            "candidate_name": candidate.full_name if candidate else "",
                            "job_title": job.title if job else "",
                            "slot_text": interview.slot_start.isoformat(),
                        },
                        language=lang, channel=channel, validated_by="system:a6_reminder",
                    )
                interview.candidate_reminder_sent_at = now
                sent += 1

            if not interview.recruiter_reminder_sent_at:
                # Rappel recruteur : journalisé (pas de canal recruteur dédié en MVP,
                # le dashboard NEEDS_ATTENTION/interviews affiche les entretiens du jour).
                logger.info(
                    "Rappel recruteur : entretien %s (candidature %s) à %s",
                    interview.id, application.id, interview.slot_start.isoformat(),
                )
                interview.recruiter_reminder_sent_at = now

            db.add(interview)
        db.commit()
        return sent
    finally:
        db.close()