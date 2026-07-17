"""
GET /reports/* — A9 (§6-A9). 8 widgets couvrant l'exigence de la spec :
funnel, sources, délais par étape, SLA parsing/scoring, distribution des
scores, coût tokens estimé, export CSV, export PDF.
Le digest email hebdomadaire réutilise les mêmes fonctions d'agrégation
(app/services/reporting/aggregates.py) — voir app/services/reporting/digest.py.
"""
from __future__ import annotations

import csv
import io
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.application import Application
from app.models.user import User
from app.services.reporting.aggregates import (
    stage_timings, sla_parsing_scoring, score_distribution, cost_per_hire,
)
from app.services.reporting.pdf_export import build_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

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
        "by_source": dict(Counter(sources)),
    }


@router.get("/sources")
def source_efficacy(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
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
            "source": source, "total": total, "converted": converted,
            "conversion_rate": round(converted / total, 3) if total else 0.0,
            "by_status": dict(Counter(a.status for a in items)),
        })
    return {"sources": result}


@router.get("/timing")
def timing(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Délai moyen (heures) pour franchir chaque étape du funnel."""
    return {"stages": stage_timings(db, job)}


@router.get("/sla")
def sla(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """SLA A3/A4 : moyenne et p95 en minutes pour parsing et scoring."""
    return sla_parsing_scoring(db)


@router.get("/score-distribution")
def scores(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Distribution des scores par tranche de 20 points."""
    return {"buckets": score_distribution(db, job)}


@router.get("/cost")
def cost(days: int = 90, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Tokens & coût estimé par embauche sur les N derniers jours."""
    return cost_per_hire(db, days)


@router.get("/export.csv")
def export_csv(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Export brut des candidatures (une ligne = une candidature)."""
    q = db.query(Application)
    if job:
        q = q.filter(Application.job_id == job)
    apps = q.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["application_id", "job_id", "candidate_id", "status", "source", "created_at"])
    for a in apps:
        writer.writerow([a.id, a.job_id, a.candidate_id, a.status, a.source, a.created_at.isoformat() if a.created_at else ""])

    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=welyne-applications.csv"},
    )


@router.get("/export.pdf")
def export_pdf(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Rapport PDF synthétique (funnel + sources + délais + SLA + scores + coût)."""
    q = db.query(Application)
    if job:
        q = q.filter(Application.job_id == job)
    apps = q.all()

    data = {
        "total": len(apps),
        "by_status": dict(Counter(a.status for a in apps)),
        "by_source": dict(Counter(a.source for a in apps)),
        "stage_timings": stage_timings(db, job),
        "sla": sla_parsing_scoring(db),
        "score_distribution": score_distribution(db, job),
        "cost": cost_per_hire(db),
    }
    pdf_bytes = build_report_pdf(data)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=welyne-reporting.pdf"},
    )
