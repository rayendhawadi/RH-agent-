"""
POST /applications/{id}/invite-interview, POST /applications/{id}/mark-interviewed.
Version minimale de l'agent A6 : pas encore d'intégration Cal.com réelle,
lien de réservation placeholder — à remplacer quand A6 sera construit.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.orchestrator.state_machine import transition
from app.services.messaging.service import send_message

router = APIRouter(prefix="/applications", tags=["interviews"])


@router.post("/{application_id}/invite-interview")
def invite_interview(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    if application.status != "PRESCREENED":
        raise HTTPException(status_code=400, detail="La candidature doit être PRESCREENED")

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    if candidate and candidate.email:
        send_message(
            db, application.id, candidate.email, "invite_interview",
            {
                "candidate_name": candidate.full_name,
                "job_title": job.title if job else "",
                "booking_link": f"https://welyne.example/book/{application.id}",
            },
            validated_by=user.email,
        )

    return transition(db, application, "INTERVIEW_SCHEDULED", actor=f"user:{user.email}")


@router.post("/{application_id}/mark-interviewed")
def mark_interviewed(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    if application.status != "INTERVIEW_SCHEDULED":
        raise HTTPException(status_code=400, detail="La candidature doit être INTERVIEW_SCHEDULED")

    return transition(db, application, "INTERVIEWED", actor=f"user:{user.email}")