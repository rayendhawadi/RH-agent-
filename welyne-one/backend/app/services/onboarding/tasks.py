"""
Tâche Celery périodique A8 (§6-A8) : relances et escalade des tâches
d'onboarding en attente. Enregistrée dans le beat_schedule de celery_app.py
sous le nom "onboarding.check_tasks" (jusqu'ici référencée mais jamais
définie -> "Received unregistered task" côté worker).

Deux seuils métier (la fréquence du check, toutes les heures, n'est PAS ce
seuil — même logique que A5/A6) :
  - 48h  : relance candidat pour un document pas encore déposé.
  - 5j   : escalade — la tâche part vers le responsable RH. Aucun canal RH
    dédié n'existe en MVP (comme le rappel recruteur de A6) : on journalise
    clairement (escalated_at + log) plutôt que d'inventer un envoi. Le
    dashboard onboarding (frontend) peut surfacer escalated_at si besoin.
Idempotent : reminder_sent_at / escalated_at ne sont écrits qu'une fois par
tâche, jamais réinitialisés ici (pas de double relance/escalade en boucle).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.onboarding_task import OnboardingTask
from app.services.messaging.service import resolve_language, resolve_recipient, send_message

logger = logging.getLogger("welyne.a8.tasks")

REMINDER_AFTER = timedelta(hours=48)
ESCALATE_AFTER = timedelta(days=5)


@celery_app.task(name="onboarding.check_tasks")
def check_onboarding_tasks_task() -> dict:
    db = SessionLocal()
    reminded = 0
    escalated = 0
    try:
        now = datetime.now(timezone.utc)

        # ── Relance candidat (documents uniquement — c'est le seul type de
        # tâche où le candidat a une action concrète à faire sur le portail).
        due_reminder = (
            db.query(OnboardingTask)
            .filter(
                OnboardingTask.status == "PENDING",
                OnboardingTask.kind == "document",
                OnboardingTask.owner == "candidate",
                OnboardingTask.reminder_sent_at.is_(None),
                OnboardingTask.created_at <= now - REMINDER_AFTER,
            )
            .all()
        )
        for task in due_reminder:
            application = db.get(Application, task.application_id)
            if application is None:
                continue
            candidate = db.get(Candidate, application.candidate_id)
            job = db.get(Job, application.job_id)
            recipient = resolve_recipient(candidate) if candidate else None
            if recipient:
                channel, to = recipient
                lang = resolve_language(db, application.id)
                send_message(
                    db, application.id, to, "onboarding_document_reminder",
                    {
                        "candidate_name": candidate.full_name if candidate else "",
                        "job_title": job.title if job else "",
                        "task_label": task.task,
                    },
                    language=lang, channel=channel, validated_by="system:a8_reminder",
                )
            task.reminder_sent_at = now
            db.add(task)
            reminded += 1
        if due_reminder:
            db.commit()

        # ── Escalade — tâche encore PENDING (document ou non) 5 jours après
        # sa création, pas de canal RH dédié en MVP -> journalisée (même
        # traitement que le rappel recruteur en A6).
        due_escalation = (
            db.query(OnboardingTask)
            .filter(
                OnboardingTask.status == "PENDING",
                OnboardingTask.escalated_at.is_(None),
                OnboardingTask.created_at <= now - ESCALATE_AFTER,
            )
            .all()
        )
        for task in due_escalation:
            application = db.get(Application, task.application_id)
            candidate = db.get(Candidate, application.candidate_id) if application else None
            job = db.get(Job, application.job_id) if application else None
            days_open = (now - task.created_at).days
            logger.warning(
                "A8 escalade : tâche %s (\"%s\") en attente depuis %s jour(s) — "
                "candidat=%s poste=%s. Vérification manuelle recommandée.",
                task.id, task.task, days_open,
                candidate.full_name if candidate else task.application_id,
                job.title if job else "?",
            )
            task.escalated_at = now
            db.add(task)
            escalated += 1
        if due_escalation:
            db.commit()

        if reminded or escalated:
            logger.info("A8 check_tasks : %s relance(s), %s escalade(s).", reminded, escalated)
        return {"reminded": reminded, "escalated": escalated}
    finally:
        db.close()