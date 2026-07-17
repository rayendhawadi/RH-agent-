"""Digest email hebdomadaire aux admins (§6-A9, livrable explicite)."""
from __future__ import annotations

import logging
from collections import Counter

from sqlalchemy.orm import Session

from app.core.mailer import send_account_email
from app.models.application import Application
from app.models.user import User
from app.services.reporting.aggregates import stage_timings, sla_parsing_scoring, cost_per_hire, needs_attention_queue

logger = logging.getLogger("welyne.a9.digest")


def _build_digest_body(db: Session) -> str:
    apps = db.query(Application).all()
    by_status = Counter(a.status for a in apps)
    timings = stage_timings(db)
    sla = sla_parsing_scoring(db)
    cost = cost_per_hire(db, days=7)
    na = needs_attention_queue(db, limit=5)

    timing_lines = [f"  - {s['stage']} : {s['avg_hours']}h (n={s['n']})" for s in timings] or ["  (pas assez de données)"]

    na_lines = []
    if na["total"]:
        na_lines = [
            "",
            f"⚠ {na['total']} candidature(s) en attente d'action (NEEDS_ATTENTION) :",
            *[f"  - {reason} : {n}" for reason, n in na["by_reason"].items()],
            "  Les plus anciennes :",
            *[f"    - {it['application_id']} ({it['reason']}, depuis {it['age_hours']}h)" for it in na["oldest"]],
        ]

    lines = [
        "Digest hebdomadaire Welyne One — reporting A9",
        *na_lines,
        "",
        f"Total candidatures actives : {len(apps)}",
        "",
        "Funnel par statut :",
        *[f"  - {status} : {count}" for status, count in sorted(by_status.items())],
        "",
        "Délais moyens par étape :",
        *timing_lines,
        "",
        f"SLA parsing — moyenne {sla['parsing']['avg_min']} min, p95 {sla['parsing']['p95_min']} min",
        f"SLA scoring — moyenne {sla['scoring']['avg_min']} min, p95 {sla['scoring']['p95_min']} min",
        "",
        f"7 derniers jours — {cost['hires']} embauche(s), {cost['total_tokens']} tokens, "
        f"~{cost['total_cost_usd_estimate']} USD estimés.",
        "",
        "Détail complet : /reports sur le dashboard.",
    ]
    return "\n".join(lines)


def send_weekly_digest(db: Session) -> int:
    """Envoie le digest à tous les comptes admin actifs. Retourne le nombre d'emails envoyés."""
    body = _build_digest_body(db)
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    for admin in admins:
        send_account_email(admin.email, "Digest hebdomadaire — reporting A9", body)
    logger.info("Digest A9 envoyé à %s admin(s)", len(admins))
    return len(admins)