"""
API agent A6 — Planification d'entretiens (§6-A6). Remplace le stub minimal
(booking_link placeholder) par l'intégration réelle : proposition de 3
créneaux (Cal.com ou repli), réservation, replanification, annulation,
no-show, marquage "passé" (-> INTERVIEWED).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.application import Application
from app.models.interview import Interview
from app.models.user import User
from app.schemas.interview import (
    BookInterviewRequest, CancelRequest, InterviewOut, ProposeSlotsRequest, RescheduleRequest,
)
from app.services.scheduling import scheduler
from app.services.scheduling.scheduler import SchedulingError

router = APIRouter(prefix="/applications", tags=["interviews"])


def _get_application(db: Session, application_id: uuid.UUID) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    return application


def _get_interview(db: Session, interview_id: str, application_id: uuid.UUID) -> Interview:
    try:
        iid = uuid.UUID(interview_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="interview_id invalide")
    interview = db.get(Interview, iid)
    if interview is None or interview.application_id != application_id:
        raise HTTPException(status_code=404, detail="Entretien introuvable pour cette candidature")
    return interview


@router.post("/{application_id}/propose-interview-slots", response_model=InterviewOut)
def propose_interview_slots(
    application_id: uuid.UUID,
    body: ProposeSlotsRequest = ProposeSlotsRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    try:
        interview = scheduler.propose_interview_slots(db, application, user.email, body.candidate_tz)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)


@router.post("/{application_id}/book-interview", response_model=InterviewOut)
def book_interview(
    application_id: uuid.UUID,
    body: BookInterviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    interview = _get_interview(db, body.interview_id, application_id)

    if body.slot_index is not None:
        slots = interview.proposed_slots or []
        if not (0 <= body.slot_index < len(slots)):
            raise HTTPException(status_code=400, detail="slot_index hors limites")
        from datetime import datetime
        chosen = slots[body.slot_index]
        start, end = datetime.fromisoformat(chosen["start"]), datetime.fromisoformat(chosen["end"])
    elif body.start and body.end:
        start, end = body.start, body.end
    else:
        raise HTTPException(status_code=400, detail="Fournir slot_index ou start/end")

    try:
        interview = scheduler.book_interview(db, interview, application, user.email, start, end, body.candidate_tz)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)


@router.post("/{application_id}/reschedule-interview", response_model=InterviewOut)
def reschedule_interview(
    application_id: uuid.UUID,
    body: RescheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    interview = _get_interview(db, body.interview_id, application_id)
    try:
        interview = scheduler.reschedule_interview(db, interview, application, user.email, body.start, body.end, body.reason)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)


@router.post("/{application_id}/cancel-interview", response_model=InterviewOut)
def cancel_interview(
    application_id: uuid.UUID,
    body: CancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    interview = _get_interview(db, body.interview_id, application_id)
    try:
        interview = scheduler.cancel_interview(db, interview, application, user.email, body.reason)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)


@router.post("/{application_id}/interviews/{interview_id}/no-show", response_model=InterviewOut)
def mark_no_show(
    application_id: uuid.UUID,
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    interview = _get_interview(db, interview_id, application_id)
    try:
        interview = scheduler.mark_no_show(db, interview, application, user.email)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)


@router.post("/{application_id}/mark-interviewed")
def mark_interviewed(
    application_id: uuid.UUID,
    interview_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = _get_application(db, application_id)
    if interview_id:
        interview = _get_interview(db, interview_id, application_id)
    else:
        interview = (
            db.query(Interview)
            .filter(Interview.application_id == application_id, Interview.status == "BOOKED")
            .order_by(Interview.slot_start.desc())
            .first()
        )
        if interview is None:
            raise HTTPException(status_code=400, detail="Aucun entretien réservé trouvé pour cette candidature")
    try:
        application = scheduler.mark_completed(db, interview, application, user.email)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"application_id": str(application.id), "status": application.status}


@router.get("/{application_id}/interviews", response_model=list[InterviewOut])
def list_interviews(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur", "lecteur")),
):
    _get_application(db, application_id)
    rows = (
        db.query(Interview)
        .filter(Interview.application_id == application_id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [_to_out(r) for r in rows]


def _to_out(interview: Interview) -> InterviewOut:
    return InterviewOut(
        id=str(interview.id),
        application_id=str(interview.application_id),
        status=interview.status,
        proposed_slots=interview.proposed_slots or [],
        slot_start=interview.slot_start,
        slot_end=interview.slot_end,
        candidate_tz=interview.candidate_tz,
        calendar_ref=interview.calendar_ref,
        reschedule_count=interview.reschedule_count,
    )


# ── Portail candidat (public, pas de rôle recruteur) ────────────────────────
# Le lien envoyé par A7 (invite_interview) pointe vers
# {FRONTEND_BASE_URL}/interviews/{id}/book, qui consomme ces routes. Le
# candidat n'a pas de compte ; l'UUID de l'entretien fait office de capacité
# (même logique que le lien de pré-qualification A5).
public_router = APIRouter(prefix="/public/interviews", tags=["interviews-public"])


@public_router.get("/{interview_id}", response_model=InterviewOut)
def public_get_interview(interview_id: uuid.UUID, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Entretien introuvable")
    return _to_out(interview)


@public_router.post("/{interview_id}/choose-slot", response_model=InterviewOut)
def public_choose_slot(interview_id: uuid.UUID, body: BookInterviewRequest, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Entretien introuvable")
    application = _get_application(db, interview.application_id)

    if body.slot_index is not None:
        slots = interview.proposed_slots or []
        if not (0 <= body.slot_index < len(slots)):
            raise HTTPException(status_code=400, detail="slot_index hors limites")
        from datetime import datetime
        chosen = slots[body.slot_index]
        start, end = datetime.fromisoformat(chosen["start"]), datetime.fromisoformat(chosen["end"])
    elif body.start and body.end:
        start, end = body.start, body.end
    else:
        raise HTTPException(status_code=400, detail="Fournir slot_index ou start/end")

    try:
        interview = scheduler.book_interview(db, interview, application, "candidate:self", start, end, body.candidate_tz)
    except SchedulingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_out(interview)