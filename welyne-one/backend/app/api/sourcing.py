"""
API agent A2 — Sourcing (§6-A2). Mode assistance (pas de scraping, voir
décision de conformité de la spec) :
  - génère des requêtes de recherche que le recruteur lance lui-même
  - génère des brouillons de messages d'approche (envoi manuel)
  - importe un profil collé/exporté par le recruteur dans le pipeline
    A3 (parsing) -> A4 (scoring), identique à un CV reçu par email,
    tagué source=linkedin_assist (CA §6-A2)
  - importe un LOT de profils via CSV (mêmes règles, une ligne = un profil)
"""
from __future__ import annotations

import csv
import io
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.application import Application
from app.models.candidate import Candidate
from app.services.parsing.dedup import get_or_create_candidate
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


def _create_linkedin_assist_application(
    db: Session, job: Job, user: User,
    full_name: str, email: str | None, phone: str | None,
    pasted_text: str | None,
) -> Application:
    """Coeur partagé par l'import unitaire et l'import bulk CSV (§6-A2, CA :
    même pipeline A3->A4, tagué source=linkedin_assist). N'accepte que du
    texte collé (le fichier reste géré à part, voir import_profile)."""
    candidate = get_or_create_candidate(db, full_name, email, phone)

    application = Application(job_id=job.id, candidate_id=candidate.id, status="RECEIVED", source="linkedin_assist")
    db.add(application)
    db.flush()

    dest = STORAGE_DIR / f"{application.id}_profile.txt"
    dest.write_text(pasted_text or "", encoding="utf-8")
    document = Document(application_id=application.id, kind="cv", storage_path=str(dest), mime="text/plain")
    db.add(document)
    db.commit()
    db.refresh(application)

    recipient = resolve_recipient(candidate)
    if recipient:
        channel, to = recipient
        send_message(
            db, application.id, to, "ack",
            {"candidate_name": candidate.full_name, "job_title": job.title},
            language=resolve_language(db, application.id),
            channel=channel, validated_by=f"user:{user.email}",
        )

    parse_application.delay(str(application.id))
    return application


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

    candidate = get_or_create_candidate(db, candidate_full_name, candidate_email, candidate_phone)

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


class BulkImportRow(BaseModel):
    row: int
    status: str  # "ok" | "error"
    detail: str
    application_id: uuid.UUID | None = None


class BulkImportOut(BaseModel):
    imported: int
    errors: int
    results: list[BulkImportRow]


@router.post("/{job_id}/sourcing/import-bulk", response_model=BulkImportOut)
def import_profiles_bulk(
    job_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """
    Import CSV en masse (§6-A2, Outils : "importeur CSV/URL") — une ligne =
    un profil trouvé manuellement (ex. plusieurs exports LinkedIn compilés
    par le recruteur). Colonnes attendues (en-tête requis) :
      full_name, email, phone, profile_text
    `full_name` et `profile_text` sont obligatoires par ligne ; `email` et
    `phone` optionnels. Chaque ligne traverse le même pipeline A3->A4 que
    l'import unitaire, tagué source="linkedin_assist". Une ligne en échec
    n'interrompt pas les suivantes (rapport détaillé retourné).
    """
    job = _get_job(db, job_id)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un .csv")

    raw = file.file.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames is None or "full_name" not in reader.fieldnames or "profile_text" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="En-têtes CSV requis : full_name, profile_text (email, phone optionnels).",
        )

    results: list[BulkImportRow] = []
    imported = 0
    for i, row in enumerate(reader, start=2):  # ligne 1 = en-tête
        full_name = (row.get("full_name") or "").strip()
        profile_text = (row.get("profile_text") or "").strip()
        if not full_name or not profile_text:
            results.append(BulkImportRow(row=i, status="error", detail="full_name et profile_text requis"))
            continue
        try:
            application = _create_linkedin_assist_application(
                db, job, user,
                full_name=full_name,
                email=(row.get("email") or "").strip() or None,
                phone=(row.get("phone") or "").strip() or None,
                pasted_text=profile_text,
            )
            results.append(BulkImportRow(row=i, status="ok", detail="importé", application_id=application.id))
            imported += 1
        except Exception as exc:  # noqa: BLE001 — une ligne en échec ne bloque pas le lot
            db.rollback()
            results.append(BulkImportRow(row=i, status="error", detail=str(exc)))

    return BulkImportOut(imported=imported, errors=len(results) - imported, results=results)