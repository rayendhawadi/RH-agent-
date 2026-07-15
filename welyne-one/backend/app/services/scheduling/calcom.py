"""
Intégration Cal.com auto-hébergé (§3, §6-A6). Utilise l'API v2
(https://cal.com/docs/api-reference/v2) quand CALCOM_URL + CALCOM_API_KEY sont
renseignés dans .env. Sinon (dev / avant provisioning), repli déterministe :
3 créneaux ouvrés générés en code, réservation "interne" journalisée sans
appel réseau — pour ne jamais bloquer le développement du reste de l'agent
A6 en attendant que Cal.com soit provisionné (kit de survie tiers §3).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger("welyne.a6.calcom")
settings = get_settings()

BUSINESS_HOURS = (9, 17)  # 09h-17h, fuseau recruteur


def _configured() -> bool:
    return bool(settings.CALCOM_URL and settings.CALCOM_API_KEY)


def _fallback_slots(n: int = 3) -> list[dict]:
    """
    3 créneaux d'1h sur les prochains jours ouvrés (lun-ven), 10h/13h/15h UTC,
    en partant de demain. Utilisé uniquement si Cal.com n'est pas configuré.
    """
    slots: list[dict] = []
    hours = [10, 13, 15]
    day = datetime.now(timezone.utc) + timedelta(days=1)
    idx = 0
    while len(slots) < n:
        if day.weekday() < 5:  # lun-ven
            hour = hours[idx % len(hours)]
            start = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            slots.append({"start": start, "end": start + timedelta(hours=1)})
            idx += 1
        day += timedelta(days=1)
    return slots


def get_available_slots(n: int = 3) -> list[dict]:
    """Retourne n créneaux {"start": datetime UTC, "end": datetime UTC}."""
    if not _configured():
        logger.info("[DEV] Cal.com non configuré — créneaux de repli générés en code.")
        return _fallback_slots(n)

    try:
        resp = httpx.get(
            f"{settings.CALCOM_URL}/v2/slots",
            headers={"Authorization": f"Bearer {settings.CALCOM_API_KEY}"},
            params={
                "startTime": datetime.now(timezone.utc).isoformat(),
                "endTime": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        flat: list[dict] = []
        for day_slots in data.values():
            for s in day_slots:
                start = datetime.fromisoformat(s["time"].replace("Z", "+00:00"))
                flat.append({"start": start, "end": start + timedelta(hours=1)})
        return flat[:n] if flat else _fallback_slots(n)
    except Exception as exc:  # noqa: BLE001 — jamais bloquant, on retombe en repli
        logger.warning("Cal.com get_available_slots indisponible (%s) — repli.", exc)
        return _fallback_slots(n)


def create_booking(start: datetime, end: datetime, candidate_name: str, candidate_email: str | None) -> str:
    """Réserve le créneau ; renvoie une référence stable (calendar_ref)."""
    if not _configured():
        ref = f"internal:{uuid.uuid4()}"
        logger.info("[DEV] Réservation interne (pas de Cal.com) : %s %s->%s", ref, start, end)
        return ref

    try:
        resp = httpx.post(
            f"{settings.CALCOM_URL}/v2/bookings",
            headers={"Authorization": f"Bearer {settings.CALCOM_API_KEY}"},
            json={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "attendee": {"name": candidate_name, "email": candidate_email or ""},
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("uid") or f"internal:{uuid.uuid4()}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cal.com create_booking a échoué (%s) — réservation interne de secours.", exc)
        return f"internal:{uuid.uuid4()}"


def reschedule_booking(calendar_ref: str, start: datetime, end: datetime) -> None:
    if not _configured() or calendar_ref.startswith("internal:"):
        logger.info("[DEV] Replanification interne %s -> %s", calendar_ref, start)
        return
    try:
        httpx.patch(
            f"{settings.CALCOM_URL}/v2/bookings/{calendar_ref}/reschedule",
            headers={"Authorization": f"Bearer {settings.CALCOM_API_KEY}"},
            json={"start": start.isoformat(), "end": end.isoformat()},
            timeout=10.0,
        ).raise_for_status()
    except Exception as exc:  # noqa: BLE001 — non bloquant, l'état local reste la source de vérité
        logger.warning("Cal.com reschedule_booking a échoué (%s).", exc)


def cancel_booking(calendar_ref: str, reason: str = "") -> None:
    if not _configured() or calendar_ref.startswith("internal:"):
        logger.info("[DEV] Annulation interne %s (%s)", calendar_ref, reason)
        return
    try:
        httpx.post(
            f"{settings.CALCOM_URL}/v2/bookings/{calendar_ref}/cancel",
            headers={"Authorization": f"Bearer {settings.CALCOM_API_KEY}"},
            json={"reason": reason},
            timeout=10.0,
        ).raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cal.com cancel_booking a échoué (%s).", exc)