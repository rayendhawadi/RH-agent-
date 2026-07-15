"""
API agent A2 — Sourcing (§6-A2). Mode assistance (pas de scraping, voir
décision de conformité de la spec) :
  - génère des requêtes de recherche que le recruteur lance lui-même
  - génère des brouillons de messages d'approche (envoi manuel)
  - importe un profil collé/exporté par le recruteur dans le pipeline
    A3 (parsing) -> A4 (scoring), identique à un CV reçu par email,
    tagué source=linkedin_assist (CA §6-A2)
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.job import Job
from app.models.user import User
from app.orchestrator.tasks import parse_application
from app.schemas.job_spec import JobSpec
from app.schemas.sourcing import OutreachSet, SourcingQueries
from app.services.messaging.service import resolve_language, resolve_recipient, send_message
from app.services.sourcing.outreach import generate_outreach_messages
from app.services.sourcing.query_generator import generate_sourcing_queries

router = APIRouter(prefix="/jobs", tags=["sourcing"])

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "documents"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return job


@router.post("/{job_id}/sourcing/queries", response_model=SourcingQueries)
def get_sourcing_queries(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    """Génère synonymes + requêtes booléennes + X-ray à partir du JobSpec (§6-A2)."""
    job = _get_job(db, job_id)
    job_spec = JobSpec.model_validate(job.job_spec or {"title": job.title})
    return generate_sourcing_queries(job_spec)


class OutreachRequest(BaseModel):
    candidate_name: str
    candidate_highlight: str = ""


@router.post("/{job_id}/sourcing/outreach", response_model=OutreachSet)
def get_outreach_messages(
    job_id: uuid.UUID,
    body: OutreachRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    """Génère 3 brouillons de message d'approche (envoi manuel, §6-A2)."""
    job = _get_job(db, job_id)
    job_spec = JobSpec.model_validate(job.job_spec or {"title": job.title})
    return generate_outreach_messages(job_spec, body.candidate_name, body.candidate_highlight)


class ImportProfileOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    source: str

    class Config:
        from_attributes = True


@router.post("/{job_id}/sourcing/import", response_model=ImportProfileOut)
def import_profile(
    job_id: uuid.UUID,
    candidate_full_name: str = Form(...),
    candidate_email: str | None = Form(None),
    candidate_phone: str | None = Form(None),
    pasted_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """
    Importe un profil trouvé manuellement par le recruteur (export PDF/DOCX,
    ou texte collé) — même pipeline que /applications/upload (A3 parsing,
    A4 scoring), mais tagué source="linkedin_assist" (CA §6-A2). Fournir soit
    `file`, soit `pasted_text`.
    """
    job = _get_job(db, job_id)
    if not file and not pasted_text:
        raise HTTPException(status_code=400, detail="Fournir un fichier (file) ou du texte collé (pasted_text).")

    candidate = Candidate(full_name=candidate_full_name, email=candidate_email, phone=candidate_phone)
    db.add(candidate)
    db.flush()

    application = Application(job_id=job.id, candidate_id=candidate.id, status="RECEIVED", source="linkedin_assist")
    db.add(application)
    db.flush()

    if file:
        dest = STORAGE_DIR / f"{application.id}_{file.filename}"
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        mime = file.content_type or "application/octet-stream"
    else:
        dest = STORAGE_DIR / f"{application.id}_profile.txt"
        dest.write_text(pasted_text or "", encoding="utf-8")
        mime = "text/plain"

    document = Document(application_id=application.id, kind="cv", storage_path=str(dest), mime=mime)
    db.add(document)
    db.commit()
    db.refresh(application)

    # Accusé de réception (§5.2, A7) — même règle que pour un CV reçu par email.
    recipient = resolve_recipient(candidate)
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "ack",
            {"candidate_name": candidate.full_name, "job_title": job.title},
            language=resolve_language(db, application.id),
            channel=channel, validated_by=f"user:{user.email}",
        )

    parse_application.delay(str(application.id))  # A3 -> A4, identique à un upload direct
    return application