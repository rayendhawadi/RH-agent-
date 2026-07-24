"""
Calculs partagés A9 (§6-A9) — utilisés à la fois par l'API /reports/* et le
digest email hebdomadaire (app/services/reporting/digest.py), pour ne jamais
faire dériver les deux.
"""
from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.llm_usage import LLMUsage
from app.models.score import Score

FUNNEL_STAGES = [
    "RECEIVED", "PARSED", "SCORED", "SHORTLISTED", "PRESCREENING", "PRESCREENED",
    "INTERVIEW_SCHEDULED", "INTERVIEWED", "OFFER", "HIRED", "ONBOARDING",
]


def _status_timeline_by_application(db: Session, job_id: uuid.UUID | None = None) -> dict[uuid.UUID, dict[str, datetime]]:
    """Pour chaque candidature : {statut: horodatage de première entrée dans ce statut}."""
    q = db.query(AuditLog).filter(AuditLog.entity == "application", AuditLog.action.like("status:%"))
    rows = q.order_by(AuditLog.at).all()

    app_q = db.query(Application.id, Application.created_at)
    if job_id:
        app_q = app_q.filter(Application.job_id == job_id)
    app_data = {r.id: r.created_at for r in app_q.all()}

    if job_id:
        rows = [r for r in rows if r.entity_id in app_data]

    timeline: dict[uuid.UUID, dict[str, datetime]] = defaultdict(dict)
    
    # Rétroactif : on utilise la date de création de la candidature comme date de RECEIVED
    for app_id, created_at in app_data.items():
        timeline[app_id]["RECEIVED"] = created_at

    for r in rows:
        to_status = r.action.split("->")[-1]
        if to_status not in timeline[r.entity_id]:
            timeline[r.entity_id][to_status] = r.at
    return timeline


def stage_timings(db: Session, job_id: uuid.UUID | None = None) -> list[dict]:
    """Délai moyen (heures) pour franchir chaque étape du funnel (§6-A9 : "délais")."""
    timeline = _status_timeline_by_application(db, job_id)
    deltas: dict[str, list[float]] = defaultdict(list)

    for stamps in timeline.values():
        for prev, curr in zip(FUNNEL_STAGES, FUNNEL_STAGES[1:]):
            if prev in stamps and curr in stamps:
                hours = (stamps[curr] - stamps[prev]).total_seconds() / 3600
                if hours >= 0:
                    deltas[f"{prev}->{curr}"].append(hours)

    return [
        {"stage": f"{prev}->{curr}", "avg_hours": round(statistics.mean(deltas[f"{prev}->{curr}"]), 1), "n": len(deltas[f"{prev}->{curr}"])}
        for prev, curr in zip(FUNNEL_STAGES, FUNNEL_STAGES[1:])
        if deltas[f"{prev}->{curr}"]
    ]


def sla_parsing_scoring(db: Session) -> dict:
    """SLA A3/A4 (§6-A9 : "SLAs parsing/scoring") — moyenne et p95 en minutes."""
    timeline = _status_timeline_by_application(db)
    parsing_minutes, scoring_minutes = [], []

    for stamps in timeline.values():
        if "RECEIVED" in stamps and "PARSED" in stamps:
            parsing_minutes.append((stamps["PARSED"] - stamps["RECEIVED"]).total_seconds() / 60)
        if "PARSED" in stamps and "SCORED" in stamps:
            scoring_minutes.append((stamps["SCORED"] - stamps["PARSED"]).total_seconds() / 60)

    def _summary(values: list[float]) -> dict:
        if not values:
            return {"avg_min": 0.0, "p95_min": 0.0, "n": 0}
        values_sorted = sorted(values)
        p95_idx = min(len(values_sorted) - 1, int(len(values_sorted) * 0.95))
        return {"avg_min": round(statistics.mean(values), 1), "p95_min": round(values_sorted[p95_idx], 1), "n": len(values)}

    return {"parsing": _summary(parsing_minutes), "scoring": _summary(scoring_minutes)}


def score_distribution(db: Session, job_id: uuid.UUID | None = None) -> list[dict]:
    """Distribution des scores par tranche de 20 points (§6-A9)."""
    q = db.query(Score.total, Score.application_id)
    if job_id:
        q = q.join(Application, Application.id == Score.application_id).filter(Application.job_id == job_id)
    totals = [t for t, _ in q.all()]

    buckets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    return [
        {"range": f"{lo}-{hi}", "count": sum(1 for t in totals if lo <= t < hi or (hi == 100 and t == 100))}
        for lo, hi in buckets
    ]


def needs_attention_queue(db: Session, limit: int = 50) -> dict:
    """
    File d'attente NEEDS_ATTENTION (§2.1, §7) — candidatures bloquées en
    attente d'une décision recruteur explicite (retries épuisés, no-show
    d'entretien, transition illégale...). Absent des widgets précédents
    (funnel/SLA/coût), mais c'est le signal opérationnel le plus direct pour
    un manager RH : "combien de dossiers attendent une action humaine, et
    depuis quand ?"

    Deux origines possibles dans audit_log (voir orchestrator/state_machine.py) :
      - "routed:NEEDS_ATTENTION" avec payload.reason explicite (ex.
        "interview_no_show", "unclear_after_retry")
      - "illegal:{from}->{to}" (transition inattendue, bug potentiel)
    """
    apps = db.query(Application).filter(Application.status == "NEEDS_ATTENTION").all()
    if not apps:
        return {"total": 0, "by_reason": {}, "oldest": []}

    app_ids = [a.id for a in apps]
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.entity == "application", AuditLog.entity_id.in_(app_ids))
        .filter((AuditLog.action == "routed:NEEDS_ATTENTION") | (AuditLog.action.like("illegal:%")))
        .order_by(AuditLog.at.desc())
        .all()
    )
    latest_by_app: dict[uuid.UUID, AuditLog] = {}
    for log in logs:  # déjà trié desc -> le premier vu par application est le plus récent
        latest_by_app.setdefault(log.entity_id, log)

    now = datetime.now(timezone.utc)
    by_reason: dict[str, int] = defaultdict(int)
    items = []
    for app in apps:
        log = latest_by_app.get(app.id)
        if log and log.action == "routed:NEEDS_ATTENTION":
            reason = log.payload.get("reason", "non précisée")
        elif log:
            reason = f"transition inattendue ({log.action.removeprefix('illegal:')})"
        else:
            reason = "non précisée"
        since = log.at if log else app.updated_at
        by_reason[reason] += 1
        items.append({
            "application_id": str(app.id),
            "job_id": str(app.job_id),
            "reason": reason,
            "since": since.isoformat() if since else None,
            "age_hours": round((now - since).total_seconds() / 3600, 1) if since else None,
        })

    items.sort(key=lambda x: x["age_hours"] or 0, reverse=True)
    return {"total": len(apps), "by_reason": dict(by_reason), "oldest": items[:limit]}


def cost_per_hire(db: Session, days: int = 90) -> dict:
    """
    Coût tokens estimé par embauche (§6-A9). Approximation assumée et documentée :
    somme des tokens de TOUS les appels LLM sur la fenêtre / nombre d'embauches
    (HIRED) sur la même fenêtre — pas un ledger exact par candidat (ça
    demanderait de faire remonter application_id à travers A1-A5, hors
    scope de cette itération), mais une estimation défendable pour piloter
    le coût global de la plateforme.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total_tokens = db.query(func.coalesce(func.sum(LLMUsage.total_tokens), 0)).filter(LLMUsage.created_at >= since).scalar()
    hires = db.query(AuditLog).filter(
        AuditLog.entity == "application", AuditLog.action == "status:OFFER->HIRED", AuditLog.at >= since,
    ).count()

    usd_per_1k = 0.0002  # tarif indicatif open-weight hébergé — à ajuster si facturation réelle
    total_cost_usd = round((total_tokens / 1000) * usd_per_1k, 4)

    return {
        "window_days": days,
        "total_tokens": int(total_tokens),
        "total_cost_usd_estimate": total_cost_usd,
        "hires": hires,
        "tokens_per_hire": int(total_tokens / hires) if hires else None,
        "cost_usd_per_hire_estimate": round(total_cost_usd / hires, 4) if hires else None,
    }