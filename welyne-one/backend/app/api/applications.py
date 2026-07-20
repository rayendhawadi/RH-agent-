"""
POST /applications/upload, GET /applications, GET /applications/{id},
POST /applications/{id}/validate-decline (porte humaine §7),
POST /applications/{id}/invite-prescreen — Annexe D.

Phase 2 (A7) : accusé de réception automatique à l'upload, email de rejet
automatique après validation recruteur, invitation pré-qualification.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfileRow
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.interview import Interview
from app.models.job import Job
from app.models.message_log import MessageLog
from app.models.score import Score
from app.models.user import User
from app.orchestrator.state_machine import transition, validate_decline
from app.orchestrator.tasks import parse_application
from app.services.messaging.service import (
    send_message,
    personalize_note,
    resolve_recipient,
    resolve_language,
)

router = APIRouter(prefix="/applications", tags=["applications"])

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "documents"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ApplicationOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    source: str
    archived_at: datetime | None = None

    class Config:
        from_attributes = True


class ApplicationDetailOut(ApplicationOut):
    stage_history: list
    profile: dict | None = None
    latest_score: dict | None = None


@router.post("/upload", response_model=ApplicationOut)
def upload_application(
    job_id: uuid.UUID = Form(...),
    candidate_full_name: str = Form(...),
    candidate_email: str | None = Form(None),
    candidate_phone: str | None = Form(None),
    file: UploadFile = File(...),
    source: str = Form("upload"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    candidate = Candidate(
        full_name=candidate_full_name,
        email=candidate_email,
        phone=candidate_phone,
    )
    db.add(candidate)
    db.flush()




    application = Application(job_id=job.id, candidate_id=candidate.id, status="RECEIVED", source=source)
    db.add(application)
    db.flush()

    dest = STORAGE_DIR / f"{application.id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    document = Document(
        application_id=application.id,
        kind="cv",
        storage_path=str(dest),
        mime=file.content_type or "application/octet-stream",
    )
    db.add(document)
    db.commit()
    db.refresh(application)

    # A7 : accusé de réception — seul envoi entièrement automatique (§7, §5.2)
    # Email en priorité, repli WhatsApp si seul un téléphone est renseigné.
    recipient = resolve_recipient(candidate)
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "ack",
            {"candidate_name": candidate.full_name, "job_title": job.title},
            language=resolve_language(db, application.id),
            channel=channel,
            validated_by="system",
        )

    parse_application.delay(str(application.id))  # démarre A3 -> A4 de façon asynchrone

    return application


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    job: uuid.UUID | None = None,
    status: str | None = None,
    min_score: float | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(Application)
    if not include_archived:
        q = q.filter(Application.archived_at.is_(None))
    if job:
        q = q.filter(Application.job_id == job)
    if status:
        q = q.filter(Application.status == status)
    applications = q.order_by(Application.created_at.desc()).all()

    if min_score is not None:
        kept = []
        for a in applications:
            latest = (
                db.query(Score)
                .filter(Score.application_id == a.id)
                .order_by(Score.created_at.desc())
                .first()
            )
            if latest and latest.total >= min_score:
                kept.append(a)
        applications = kept

    return applications


@router.get("/{application_id}", response_model=ApplicationDetailOut)
def get_application(application_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    profile_row = db.query(CandidateProfileRow).filter(CandidateProfileRow.application_id == application.id).first()
    latest_score = (
        db.query(Score)
        .filter(Score.application_id == application.id)
        .order_by(Score.created_at.desc())
        .first()
    )

    return ApplicationDetailOut(
        id=application.id,
        job_id=application.job_id,
        candidate_id=application.candidate_id,
        status=application.status,
        source=application.source,
        stage_history=application.stage_history,
        profile=profile_row.profile if profile_row else None,
        latest_score=(
            {
                "total": latest_score.total,
                "subscores": latest_score.subscores,
                "verdict": latest_score.verdict,
                "justification": latest_score.justification,
                "evidence": latest_score.evidence,
            }
            if latest_score
            else None
        ),
    )


class DeclineValidation(BaseModel):
    reason: str = ""


@router.post("/{application_id}/archive", response_model=ApplicationOut)
def archive_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """
    Archivage réversible — masque la candidature des vues par défaut
    (GET /applications) sans rien effacer : l'historique, les scores, les
    conversations et l'audit_log restent intacts. À distinguer de la
    suppression définitive (DELETE ci-dessous), qui est irréversible.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    application.archived_at = datetime.now(timezone.utc)
    db.add(application)
    db.add(AuditLog(entity="application", entity_id=application.id, action="archived", actor=f"user:{user.email}", payload={}))
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/unarchive", response_model=ApplicationOut)
def unarchive_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    application.archived_at = None
    db.add(application)
    db.add(AuditLog(entity="application", entity_id=application.id, action="unarchived", actor=f"user:{user.email}", payload={}))
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """
    Suppression DÉFINITIVE — réservée admin (contrairement à l'archivage).
    Purge en cascade tout ce qui référence cette candidature (documents,
    profil parsé, scores, conversations A5 + messages, entretiens A6,
    message_log A7) avant de supprimer la ligne applications elle-même,
    pour éviter toute violation de clé étrangère. Le candidat lui-même
    (table candidates) n'est PAS touché : il peut avoir d'autres
    candidatures sur d'autres offres. Pour l'effacement RGPD complet d'un
    candidat, voir POST /candidates/{id}/erase (§7) — un besoin différent.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    conv_ids = [c.id for c in db.query(Conversation.id).filter(Conversation.application_id == application_id)]
    if conv_ids:
        db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(synchronize_session=False)

    db.query(Interview).filter(Interview.application_id == application_id).delete(synchronize_session=False)
    db.query(MessageLog).filter(MessageLog.application_id == application_id).delete(synchronize_session=False)
    db.query(Score).filter(Score.application_id == application_id).delete(synchronize_session=False)
    db.query(CandidateProfileRow).filter(CandidateProfileRow.application_id == application_id).delete(synchronize_session=False)
    db.query(Document).filter(Document.application_id == application_id).delete(synchronize_session=False)

    db.add(AuditLog(
        entity="application", entity_id=application.id, action="deleted",
        actor=f"user:{user.email}", payload={"status_at_deletion": application.status},
    ))
    db.delete(application)
    db.commit()
    return {"status": "deleted", "application_id": str(application_id)}


@router.post("/{application_id}/validate-decline", response_model=ApplicationOut)
def validate_decline_endpoint(
    application_id: uuid.UUID,
    body: DeclineValidation,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Porte humaine (§7) : SEUL endpoint qui peut faire passer DECLINE_PENDING -> DECLINED."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    try:
        application = validate_decline(db, application, user.email, body.reason)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))

    # A7 : message de rejet — envoyé UNIQUEMENT après validation recruteur ci-dessus
    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        ctx = {"candidate_name": candidate.full_name, "job_title": job.title if job else ""}
        ctx["personalized_note"] = personalize_note(ctx)
        send_message(
            db, application.id, to, "decline", ctx,
            language=resolve_language(db, application.id),
            channel=channel, validated_by=user.email,
        )

    return application


@router.post("/{application_id}/invite-prescreen", response_model=ApplicationOut)
def invite_prescreen(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """
    SHORTLISTED -> PRESCREENING (Annexe D). Envoie l'invitation A7 ; le
    traitement conversationnel complet (A5) arrive en phase 3.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    if application.status != "SHORTLISTED":
        raise HTTPException(status_code=400, detail="La candidature doit être SHORTLISTED")

    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        # Lien réel vers la page candidat frontend/app/chat/[id]/page.tsx
        # (auparavant https://welyne.example/... — domaine placeholder qui
        # ne résout jamais, et aucune page candidat n'existait de toute façon).
        prescreen_link = f"{get_settings().FRONTEND_BASE_URL}/chat/{application.id}"
        send_message(
            db, application.id, to, "invite_prescreen",
            {
                "candidate_name": candidate.full_name,
                "job_title": job.title if job else "",
                "prescreen_link": prescreen_link,
            },
            language=resolve_language(db, application.id),
            channel=channel,
            validated_by=user.email,
        )

    return transition(db, application, "PRESCREENING", actor=f"user:{user.email}")