"""
Cœur de l'agent A3 : texte brut -> CandidateProfile validé.

Pipeline : ingestion -> extraction texte -> repli OCR -> détection langue ->
découpage si > 8k tokens -> extraction LLM (schéma) -> post-traitement (calcul
des durées en code, PAS par le LLM) -> dédoublonnage.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

from app.schemas.candidate_profile import CandidateProfile
from app.services.llm_gateway import complete_structured

MAX_CHARS = 32_000  # ~8k tokens, découpage grossier suffisant pour un CV

SYSTEM_PROMPT = """Tu es un extracteur d'informations de CV, précis et factuel.
Extrait UNIQUEMENT ce qui est explicitement présent dans le texte. N'invente rien.
Si une information est absente, laisse le champ vide ou null.
Normalise les dates au format AAAA-MM quand possible ; "present" pour un poste en cours.
Ne calcule pas duration_months ni total_experience_months : laisse-les à 0, ils
sont recalculés en code après extraction."""


def extract_candidate_profile(raw_text: str, detected_language: str, parser_version: str = "a3@v1") -> CandidateProfile:
    text = raw_text[:MAX_CHARS]

    profile = complete_structured(
        task="extract",
        system=SYSTEM_PROMPT,
        user=f"Texte du CV (langue détectée: {detected_language}) :\n\n{text}",
        schema=CandidateProfile,
        temperature=0.0,
        seed=42,
        trace_name="a3_extract_profile",
    )

    profile.detected_language = detected_language if detected_language in ("fr", "en", "ar") else "fr"
    profile.parser_version = parser_version

    # Post-traitement déterministe : durées calculées en code, jamais par le LLM.
    total_months = 0
    for exp in profile.experiences:
        months = _months_between(exp.start, exp.end)
        exp.duration_months = months
        total_months += months
    profile.total_experience_months = total_months

    return profile


def _months_between(start: str | None, end: str | None) -> int:
    if not start:
        return 0
    try:
        y1, m1 = (int(x) for x in start.split("-")[:2])
    except (ValueError, AttributeError):
        return 0

    if not end or end.lower() == "present":
        now = datetime.utcnow()
        y2, m2 = now.year, now.month
    else:
        try:
            y2, m2 = (int(x) for x in end.split("-")[:2])
        except (ValueError, AttributeError):
            return 0

    months = (y2 - y1) * 12 + (m2 - m1)
    return max(months, 0)


def dedup_key(email: str | None, phone: str | None) -> str | None:
    """Hash de dédoublonnage sur email/téléphone normalisés (§4, table candidates)."""
    if not email and not phone:
        return None
    norm_email = (email or "").strip().lower()
    norm_phone = re.sub(r"\D", "", phone or "")
    raw = f"{norm_email}|{norm_phone}"
    return hashlib.sha256(raw.encode()).hexdigest()
