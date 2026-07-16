"""GET /audit-log — réservé à admin (§2.1 : "chaque transition écrite dans audit_log")."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-log", tags=["audit"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    entity: str
    entity_id: uuid.UUID
    action: str
    actor: str
    payload: dict
    at: object

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditLogOut])
def list_audit_log(
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    q = db.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    return q.order_by(AuditLog.at.desc()).limit(min(limit, 500)).all()