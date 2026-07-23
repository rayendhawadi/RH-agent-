"""GET/POST /jobs, PATCH /jobs/{id}/weights (§Annexe D). Publication = phase 2 (A1/A7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.schemas.job_content import ChannelContent
from app.services.publishing.jobspec_agent import generate_jobspec_from_brief, generate_channel_content
from app.models.audit_log import AuditLog
from app.api.deps import get_db, get_current_user, require_role
from app.models.job import Job
from app.models.application import Application
from app.models.user import User
from app.schemas.job_spec import JobSpec, JobWeights

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    title: str
    job_spec: JobSpec | None = None
    weights: JobWeights | None = None
    onboarding_category: str | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    job_spec: dict
    weights: dict
    onboarding_category: str | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.post("", response_model=JobOut)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    job = Job(
        title=body.title,
        job_spec=(body.job_spec or JobSpec(title=body.title)).model_dump(),
        weights=(body.weights or JobWeights()).model_dump(),
        onboarding_category=body.onboarding_category,
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return job


@router.patch("/{job_id}/weights", response_model=JobOut)
def update_weights(
    job_id: uuid.UUID,
    weights: JobWeights,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    job.weights = weights.model_dump()
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class OnboardingCategoryBody(BaseModel):
    onboarding_category: str | None = None


@router.patch("/{job_id}/onboarding-category", response_model=JobOut)
def update_onboarding_category(
    job_id: uuid.UUID,
    body: OnboardingCategoryBody,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    """Corrige la catégorie de gabarit A8 après coup (§6-A8). Bloqué dès qu'un
    candidat de cette offre est déjà HIRED/ONBOARDING : sa checklist a déjà
    été générée sur l'ancienne catégorie, changer sous ses pieds serait
    trompeur — mieux vaut ajuster le gabarit lui-même dans ce cas."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    already_hired = (
        db.query(Application.id)
        .filter(Application.job_id == job.id, Application.status.in_(["HIRED", "ONBOARDING"]))
        .first()
        is not None
    )
    if already_hired:
        raise HTTPException(
            status_code=409,
            detail="Impossible de changer la catégorie : un candidat de cette offre est déjà embauché ou en onboarding.",
        )

    job.onboarding_category = body.onboarding_category
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class GenerateSpecBody(BaseModel):
    raw_brief: str


@router.post("/{job_id}/generate-spec", response_model=JobOut)
def generate_spec(
    job_id: uuid.UUID,
    body: GenerateSpecBody,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin", "recruteur")),
):
    """A1 : brief brut -> JobSpec structuré + variantes par canal (stockées dans job_spec.channel_content)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    job_spec = generate_jobspec_from_brief(body.raw_brief)
    channel_content: ChannelContent = generate_channel_content(job_spec)

    merged = job_spec.model_dump()
    merged["channel_content"] = channel_content.model_dump()
    job.job_spec = merged
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/publish", response_model=JobOut)
def publish_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Porte humaine (§2.1, §7) : publication externe = clic recruteur obligatoire."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    job.status = "published"
    db.add(job)
    db.add(AuditLog(entity="job", entity_id=job.id, action="published", actor=f"user:{user.email}", payload={}))
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/close", response_model=JobOut)
def close_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Archive une offre (statut 'closed') sans supprimer ses candidatures —
    alternative sûre à la suppression pour une offre qui a déjà du historique."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    job.status = "closed"
    db.add(job)
    db.add(AuditLog(entity="job", entity_id=job.id, action="closed", actor=f"user:{user.email}", payload={}))
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/reopen", response_model=JobOut)
def reopen_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Réactive une offre archivée -> repasse en brouillon (republication = nouveau clic explicite)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if job.status != "closed":
        raise HTTPException(status_code=400, detail="Seule une offre archivée peut être réactivée")

    job.status = "draft"
    db.add(job)
    db.add(AuditLog(entity="job", entity_id=job.id, action="reopened", actor=f"user:{user.email}", payload={}))
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/duplicate", response_model=JobOut)
def duplicate_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Repart d'une fiche existante (job_spec + pondérations) pour un poste similaire
    -> toujours créée en brouillon, jamais publiée automatiquement (§7 porte humaine)."""
    source = db.get(Job, job_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    spec = dict(source.job_spec or {})
    spec["title"] = f"{source.title} (copie)"
    spec.pop("channel_content", None)  # contenus de publication à régénérer, pas à recopier tels quels

    clone = Job(
        title=f"{source.title} (copie)",
        status="draft",
        job_spec=spec,
        weights=dict(source.weights or JobWeights().model_dump()),
        created_by=user.id,
    )
    db.add(clone)
    db.add(AuditLog(entity="job", entity_id=clone.id, action="duplicated_from", actor=f"user:{user.email}", payload={"source_job_id": str(source.id)}))
    db.commit()
    db.refresh(clone)
    return clone


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "recruteur")),
):
    """Suppression définitive — refusée si des candidatures existent déjà (intégrité
    des données candidat, §7) : archiver (close_job) est l'action à proposer à la place."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Offre introuvable")

    has_applications = db.query(Application.id).filter(Application.job_id == job.id).first() is not None
    if has_applications:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer une offre qui a déjà des candidatures — archivez-la plutôt.",
        )

    db.add(AuditLog(entity="job", entity_id=job.id, action="deleted", actor=f"user:{user.email}", payload={"title": job.title}))
    db.delete(job)
    db.commit()