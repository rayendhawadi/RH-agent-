"""GET /reports/funnel — version minimale phase 1 (A9 complet = phase 4)."""
from __future__ import annotations

import uuid
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.application import Application
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/funnel")
def funnel(job: uuid.UUID | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    q = db.query(Application)
    if job:
        q = q.filter(Application.job_id == job)
    statuses = [a.status for a in q.all()]
    counts = Counter(statuses)
    return {"total": len(statuses), "by_status": dict(counts)}
