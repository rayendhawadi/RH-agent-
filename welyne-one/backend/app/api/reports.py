"""GET /reports/funnel, GET /reports/sources — version minimale phase 1 (A9 complet = phase 4)."""
from __future__ import annotations

import uuid
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.application import Application
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])

# Statuts comptant comme "conversion" pour le taux d'efficacité par source
# (au-delà du simple parsing/scoring : le candidat a passé le premier tri humain).
_CONVERTED_STATUSES = {"SHORTLISTED", "PRESCREENING", "PRESCREENED", "INTERVIEW_SCHEDULED",
                       "INTERVIEWED", "OFFER", "HIRED", "ONBOARDING"}


@router.get("/funnel")
def funnel(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    q = db.query(Application)
    if job:
        q = q.filter(Application.job_id == job)
    apps = q.all()
    statuses = [a.status for a in apps]
    sources = [a.source for a in apps]
    return {
        "total": len(statuses),
        "by_status": dict(Counter(statuses)),
        "by_source": dict(Counter(sources)),  # §6-A2 : livrable "flux d'analytics de sources pour A9"
    }


@router.get("/sources")
def source_efficacy(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """
    Efficacité par source (upload/email/linkedin_assist/...) — livrable A2 (§6-A2) :
    permet de savoir si le sourcing manuel LinkedIn ramène de bons candidats,
    pas seulement du volume.
    """
    q = db.query(Application)
    if job:
        q = q.filter(Application.job_id == job)
    apps = q.all()

    by_source: dict[str, list[Application]] = {}
    for a in apps:
        by_source.setdefault(a.source, []).append(a)

    result = []
    for source, items in sorted(by_source.items()):
        total = len(items)
        converted = sum(1 for a in items if a.status in _CONVERTED_STATUSES)
        result.append({
            "source": source,
            "total": total,
            "converted": converted,
            "conversion_rate": round(converted / total, 3) if total else 0.0,
            "by_status": dict(Counter(a.status for a in items)),
        })
    return {"sources": result}
