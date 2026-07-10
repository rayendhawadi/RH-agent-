"""
A0 — Orchestrateur : machine à états des candidatures (§2.1).

    RECEIVED -> PARSED -> SCORED -> {SHORTLISTED | POOL | DECLINE_PENDING}
    SHORTLISTED -> PRESCREENING -> PRESCREENED -> INTERVIEW_SCHEDULED -> INTERVIEWED
    INTERVIEWED -> {OFFER -> HIRED -> ONBOARDING} | DECLINE_PENDING
    DECLINE_PENDING -(validation recruteur)-> DECLINED
    OFFER -(validation recruteur)-> HIRED
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.application import Application, APPLICATION_STATUSES
from app.models.audit_log import AuditLog

_LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "RECEIVED": {"PARSED", "NEEDS_ATTENTION"},
    "PARSED": {"SCORED", "NEEDS_ATTENTION"},
    "SCORED": {"SHORTLISTED", "POOL", "DECLINE_PENDING", "NEEDS_ATTENTION"},
    "SHORTLISTED": {"PRESCREENING", "NEEDS_ATTENTION"},
    "PRESCREENING": {"PRESCREENED", "NEEDS_ATTENTION"},
    "PRESCREENED": {"INTERVIEW_SCHEDULED", "DECLINE_PENDING", "NEEDS_ATTENTION"},
    "INTERVIEW_SCHEDULED": {"INTERVIEWED", "NEEDS_ATTENTION"},
    "INTERVIEWED": {"OFFER", "DECLINE_PENDING", "NEEDS_ATTENTION"},
    "OFFER": {"HIRED", "DECLINE_PENDING", "NEEDS_ATTENTION"},
    "HIRED": {"ONBOARDING", "NEEDS_ATTENTION"},
    "ONBOARDING": {"NEEDS_ATTENTION"},
    "POOL": {"SHORTLISTED", "DECLINE_PENDING", "NEEDS_ATTENTION"},
    "DECLINE_PENDING": {"DECLINED", "NEEDS_ATTENTION"},
    "DECLINED": set(),
    "NEEDS_ATTENTION": set(APPLICATION_STATUSES) - {"NEEDS_ATTENTION"},
}

HUMAN_GATES = {
    ("DECLINE_PENDING", "DECLINED"),
    ("*", "PUBLISHED"),
    ("OFFER", "HIRED"),
}


class IllegalTransitionError(Exception):
    pass


class HumanGateRequiredError(Exception):
    pass


def transition(
    db: Session,
    application: Application,
    to_status: str,
    actor: str,
    payload: dict | None = None,
    *,
    _bypass_gate_check: bool = False,
) -> Application:
    from_status = application.status

    if (from_status, to_status) in HUMAN_GATES and not _bypass_gate_check:
        raise HumanGateRequiredError(
            f"Transition {from_status} -> {to_status} exige une validation recruteur explicite."
        )

    allowed = _LEGAL_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        application.status = "NEEDS_ATTENTION"
        _write_audit(db, application.id, f"illegal:{from_status}->{to_status}", actor, payload)
        db.add(application)
        db.commit()
        db.refresh(application)
        raise IllegalTransitionError(f"Transition illégale : {from_status} -> {to_status}")

    application.status = to_status
    history_entry = {
        "from": from_status,
        "to": to_status,
        "actor": actor,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    application.stage_history = [*application.stage_history, history_entry]

    _write_audit(db, application.id, f"status:{from_status}->{to_status}", actor, payload)

    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def validate_decline(db: Session, application: Application, recruiter_email: str, reason: str = "") -> Application:
    if application.status != "DECLINE_PENDING":
        raise IllegalTransitionError("La candidature n'est pas en attente de décision de rejet.")

    return transition(
        db, application, "DECLINED",
        actor=f"user:{recruiter_email}", payload={"reason": reason},
        _bypass_gate_check=True,
    )


def confirm_hire(db: Session, application: Application, recruiter_email: str, note: str = "") -> Application:
    """Seule voie légale pour OFFER -> HIRED (porte humaine §7)."""
    if application.status != "OFFER":
        raise IllegalTransitionError("La candidature n'est pas au statut OFFER.")

    return transition(
        db, application, "HIRED",
        actor=f"user:{recruiter_email}", payload={"note": note},
        _bypass_gate_check=True,
    )


def route_to_needs_attention(db: Session, application: Application, reason: str, actor: str = "system") -> Application:
    application.status = "NEEDS_ATTENTION"
    _write_audit(db, application.id, "routed:NEEDS_ATTENTION", actor, {"reason": reason})
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def _write_audit(db: Session, entity_id: uuid.UUID, action: str, actor: str, payload: dict | None) -> None:
    db.add(
        AuditLog(
            entity="application", entity_id=entity_id,
            action=action, actor=actor, payload=payload or {},
        )
    )
