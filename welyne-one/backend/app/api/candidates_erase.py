"""POST /candidates/{id}/erase — droit à l'effacement RGPD / loi 2004-63 (§7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfileRow
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/{candidate_id}/erase")
def erase_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidat introuvable")

    applications = db.query(Application).filter(Application.candidate_id == candidate.id).all()
    for app_ in applications:
        db.query(CandidateProfileRow).filter(CandidateProfileRow.application_id == app_.id).delete()

    db.add(
        AuditLog(
            entity="candidate",
            entity_id=candidate.id,
            action="erase",
            actor=f"user:{user.email}",
            payload={},
        )
    )

    candidate.full_name = "[EFFACÉ]"
    candidate.email = None
    candidate.phone = None
    candidate.links = []
    db.add(candidate)
    db.commit()
    return {"status": "erased", "candidate_id": str(candidate_id)}
