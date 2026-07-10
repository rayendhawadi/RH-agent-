"""
POST /applications/{id}/make-offer, POST /applications/{id}/confirm-hire.
`confirm-hire` = porte humaine explicite (§7) — voir HUMAN_GATES (OFFER, HIRED).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.user import User
from app.orchestrator.state_machine import transition, confirm_hire, IllegalTransitionError
from app.services.messaging.service import send_message, resolve_recipient, resolve_language

router = APIRouter(prefix="/applications", tags=["offers"])


@router.post("/{application_id}/make-offer")
def make_offer(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    if application.status != "INTERVIEWED":
        raise HTTPException(status_code=400, detail="La candidature doit être INTERVIEWED")

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "offer",
            {"candidate_name": candidate.full_name, "job_title": job.title if job else ""},
            language=resolve_language(db, application.id),
            channel=channel,
            validated_by=user.email,
        )

    return transition(db, application, "OFFER", actor=f"user:{user.email}")


class ConfirmHireBody(BaseModel):
    note: str = ""


@router.post("/{application_id}/confirm-hire")
def confirm_hire_endpoint(
    application_id: uuid.UUID,
    body: ConfirmHireBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    try:
        application = confirm_hire(db, application, user.email, body.note)
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return application