"""
Génération d'invitation ICS (§6-A6 : « invitation ICS »). Construction
manuelle minimale (RFC 5545) pour éviter une dépendance supplémentaire —
suffisant pour un VEVENT simple accepté par Gmail/Outlook/Google Calendar.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    *,
    uid: str,
    start: datetime,
    end: datetime,
    summary: str,
    description: str = "",
    organizer_email: str = "recrutement@welyne.example",
    attendee_email: str | None = None,
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Welyne One//Agent A6//FR",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_fmt(datetime.now(timezone.utc))}",
        f"DTSTART:{_fmt(start)}",
        f"DTEND:{_fmt(end)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"ORGANIZER:mailto:{organizer_email}",
    ]
    if attendee_email:
        lines.append(f"ATTENDEE;RSVP=TRUE:mailto:{attendee_email}")
    lines += ["STATUS:CONFIRMED", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines)