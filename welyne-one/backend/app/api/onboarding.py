"""
POST /applications/{id}/start-onboarding. Version minimale de l'agent A8 :
envoie l'email de bienvenue, fait passer HIRED -> ONBOARDING. La checklist
personnalisée et le RAG manuel (§6-A8) restent à construire (phase 4).
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

router = APIRouter(prefix="/applications", tags=["onboarding"])


@router.post("/{application_id}/start-onboarding")
def start_onboarding(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    if application.status != "HIRED":
        raise HTTPException(status_code=400, detail="La candidature doit être HIRED")

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    if candidate and candidate.email:
        send_message(
            db, application.id, candidate.email, "onboarding_welcome",
            {"candidate_name": candidate.full_name, "job_title": job.title if job else ""},
            validated_by=user.email,
        )

    return transition(db, application, "ONBOARDING", actor=f"user:{user.email}")