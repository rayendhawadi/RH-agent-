"""
Agent A8 — checklist personnalisée (§6-A8).

POST /applications/{id}/start-onboarding : email de bienvenue + HIRED -> ONBOARDING
    + génère la checklist depuis le RoleTemplate correspondant au poste.
GET  /applications/{id}/onboarding-tasks  : vue recruteur de la checklist.
POST .../onboarding-tasks/{task_id}/complete : marque une tâche côté RH (compte,
    équipement, agenda) comme faite.
POST .../onboarding-tasks/{task_id}/reject   : renvoie un document déposé par le
    candidat (motif obligatoire) -> le candidat doit redéposer.

public_router (aucune auth, cf. pattern §6-A6 interviews) : portail candidat pour
consulter sa checklist et déposer ses documents lui-même.

Le RAG sur le manuel d'entreprise (mission 2 de la spec) reste à construire —
hors périmètre de ce fichier.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.api.applications import STORAGE_DIR
from app.core.config import get_settings
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.job import Job
from app.models.onboarding_task import OnboardingTask, TASK_STATUSES
from app.models.user import User
from app.orchestrator.state_machine import transition
from app.services.generation.onboarding_checklist import generate_checklist
from app.services.messaging.service import send_message, resolve_recipient, resolve_language

router = APIRouter(prefix="/applications", tags=["onboarding"])
public_router = APIRouter(prefix="/public/onboarding", tags=["onboarding-public"])


class TaskOut(BaseModel):
    id: uuid.UUID
    task: str
    kind: str
    owner: str
    status: str
    document_id: uuid.UUID | None
    reject_reason: str | None

    class Config:
        from_attributes = True


class RejectBody(BaseModel):
    reason: str


settings = get_settings()


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
    recipient = resolve_recipient(candidate) if candidate else None
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "onboarding_welcome",
            {
                "candidate_name": candidate.full_name, 
                "job_title": job.title if job else "",
                "checklist_link": f"{settings.FRONTEND_BASE_URL}/onboarding/{application.id}"
            },
            language=resolve_language(db, application.id),
            channel=channel,
            validated_by=user.email,
        )

    result = transition(db, application, "ONBOARDING", actor=f"user:{user.email}")
    # Idempotent (cf. generate_checklist) : un redémarrage d'onboarding ne duplique rien.
    generate_checklist(db, application.id, job)
    return result


@router.get("/{application_id}/onboarding-tasks", response_model=list[TaskOut])
def list_onboarding_tasks(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur", "lecteur")),
):
    return (
        db.query(OnboardingTask)
        .filter(OnboardingTask.application_id == application_id)
        .order_by(OnboardingTask.kind, OnboardingTask.created_at)
        .all()
    )


@router.post("/{application_id}/onboarding-tasks/{task_id}/complete", response_model=TaskOut)
def complete_onboarding_task(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Réservé aux tâches owner='rh' (compte, équipement, agenda) — un document
    déposé par le candidat se valide via validate/reject, pas ce endpoint."""
    task = db.get(OnboardingTask, task_id)
    if task is None or task.application_id != application_id:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.owner != "rh":
        raise HTTPException(status_code=400, detail="Cette tâche attend une action du candidat, pas du RH")

    task.status = "DONE"
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{application_id}/onboarding-tasks/{task_id}/validate", response_model=TaskOut)
def validate_onboarding_document(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Un document déposé (status=SUBMITTED) passe à DONE une fois vérifié par le RH."""
    task = db.get(OnboardingTask, task_id)
    if task is None or task.application_id != application_id:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.status != "SUBMITTED":
        raise HTTPException(status_code=400, detail="Aucun document en attente de validation sur cette tâche")

    task.status = "DONE"
    task.reject_reason = None
    db.add(task)
    db.commit()
    db.refresh(task)

    # Une fois TOUS les documents candidat validés (pas les tâches RH en
    # parallèle : comptes/équipement/agenda), on renvoie le lien du portail —
    # le candidat sait ainsi explicitement qu'il peut désormais utiliser
    # l'assistant Q&R (RAG) sans attendre le reste des tâches côté RH.
    remaining_docs = (
        db.query(OnboardingTask)
        .filter(
            OnboardingTask.application_id == application_id,
            OnboardingTask.kind == "document",
            OnboardingTask.status != "DONE",
        )
        .count()
    )
    if remaining_docs == 0:
        application = db.get(Application, application_id)
        candidate = db.get(Candidate, application.candidate_id) if application else None
        job = db.get(Job, application.job_id) if application else None
        recipient = resolve_recipient(candidate) if candidate else None
        if recipient and application:
            channel, to = recipient
            send_message(
                db, application.id, to, "onboarding_documents_complete",
                {
                    "candidate_name": candidate.full_name,
                    "job_title": job.title if job else "",
                    "checklist_link": f"{get_settings().FRONTEND_BASE_URL}/onboarding/{application.id}",
                },
                language=resolve_language(db, application.id),
                channel=channel,
                validated_by=user.email,
            )

    return task


@router.post("/{application_id}/onboarding-tasks/{task_id}/reject", response_model=TaskOut)
def reject_onboarding_document(
    application_id: uuid.UUID,
    task_id: uuid.UUID,
    body: RejectBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    task = db.get(OnboardingTask, task_id)
    if task is None or task.application_id != application_id:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.kind != "document":
        raise HTTPException(status_code=400, detail="Seul un document déposé peut être rejeté")

    task.status = "REJECTED"
    task.reject_reason = body.reason
    task.document_id = None
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── Portail candidat public (pas d'auth, cf. §6-A6 même pattern) ──────────

class PortalTaskOut(BaseModel):
    id: uuid.UUID
    task: str
    kind: str
    status: str
    reject_reason: str | None

    class Config:
        from_attributes = True


class PortalOut(BaseModel):
    application_id: uuid.UUID
    candidate_name: str
    job_title: str
    tasks: list[PortalTaskOut]


@public_router.get("/{application_id}", response_model=PortalOut)
def get_onboarding_portal(application_id: uuid.UUID, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Introuvable")
    candidate = db.get(Candidate, application.candidate_id)
    job = db.get(Job, application.job_id)
    # Seules les tâches du candidat (kind=document) sont exposées côté portail —
    # les tâches owner='rh' (comptes, équipement, agenda) n'ont rien à faire
    # dans une interface publique.
    tasks = (
        db.query(OnboardingTask)
        .filter(OnboardingTask.application_id == application_id, OnboardingTask.owner == "candidate")
        .order_by(OnboardingTask.created_at)
        .all()
    )
    return PortalOut(
        application_id=application.id,
        candidate_name=candidate.full_name if candidate else "",
        job_title=job.title if job else "",
        tasks=tasks,
    )


@public_router.post("/tasks/{task_id}/submit", response_model=PortalTaskOut)
def submit_onboarding_document(
    task_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    task = db.get(OnboardingTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.owner != "candidate" or task.kind != "document":
        raise HTTPException(status_code=400, detail="Cette tâche n'attend pas de dépôt de fichier")
    if task.status == "DONE":
        raise HTTPException(status_code=400, detail="Document déjà validé")

    dest = STORAGE_DIR / f"onboarding_{task.id}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    document = Document(
        application_id=task.application_id,
        kind="onboarding",
        storage_path=str(dest),
        mime=file.content_type or "application/octet-stream",
    )
    db.add(document)
    db.flush()

    task.document_id = document.id
    task.status = "SUBMITTED"
    task.reject_reason = None
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ── Assistant Q&R RAG (Manuel d'entreprise) ──────────

class ChatQuery(BaseModel):
    question: str

@public_router.post("/{application_id}/chat")
def ask_onboarding_question(
    application_id: uuid.UUID,
    query: ChatQuery,
    db: Session = Depends(get_db),
):
    from app.services.onboarding.rag import answer_question
    result = answer_question(query.question, db)
    return result

@router.post("/manual/upload")
def upload_manual(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    from app.services.onboarding.rag import process_manual
    
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = STORAGE_DIR / f"manual_{uuid.uuid4().hex}.pdf"
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
        
    process_manual(str(path), db)
    return {"status": "ok", "message": "Manuel importé et vectorisé avec succès."}