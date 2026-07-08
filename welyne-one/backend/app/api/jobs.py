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
from app.models.user import User
from app.schemas.job_spec import JobSpec, JobWeights

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    title: str
    job_spec: JobSpec | None = None
    weights: JobWeights | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    job_spec: dict
    weights: dict

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