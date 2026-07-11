"""
Cœur de l'agent A3 : texte brut -> CandidateProfile validé.

Pipeline : ingestion -> extraction texte -> repli OCR -> détection langue ->
découpage si > 8k tokens -> extraction LLM (schéma) -> post-traitement (calcul
des durées en code, PAS par le LLM) -> dédoublonnage.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
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

    # Filet de sécurité déterministe (jamais par le LLM) : les CV en mise en page
    # 2 colonnes font parfois lire le bloc contact (icône + email/tel) hors contexte,
    # et le LLM d'extraction le rate. On complète par regex si le champ est vide.
    if not profile.identity.email:
        found = _extract_email(text)
        if found:
            profile.identity.email = found
    if not profile.identity.phone:
        found = _extract_phone(text)
        if found:
            profile.identity.phone = found

    return profile


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Tunisie : 8 chiffres locaux, avec ou sans indicatif +216 / 00216
_PHONE_RE = re.compile(r"(?:\+216|00216)?[\s.-]?(\d[\s.-]?){7,8}\d")


def _extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else None


def _extract_phone(text: str) -> str | None:
    for m in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 11:
            return m.group(0).strip()
    return None


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


_PRESENT_SYNONYMS = {
    "present", "présent", "actuel", "aujourd'hui", "en cours", "ongoing", "now", "current",
}


def _parse_year_month(value: str) -> tuple[int, int] | None:
    """Accepte 'AAAA-MM' ou juste 'AAAA' (mois par défaut = 06, milieu d'année,
    pour ne pas biaiser systématiquement vers le bas)."""
    parts = value.strip().split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return None
    month = 6
    if len(parts) > 1 and parts[1].strip():
        try:
            month = int(parts[1])
        except ValueError:
            month = 6
    return year, month


def _months_between(start: str | None, end: str | None) -> int:
    if not start:
        return 0
    parsed_start = _parse_year_month(start)
    if parsed_start is None:
        return 0
    y1, m1 = parsed_start

    end_normalized = (end or "").strip().lower()
    if not end_normalized or _strip_accents(end_normalized) in _PRESENT_SYNONYMS:
        now = datetime.utcnow()
        y2, m2 = now.year, now.month
    else:
        parsed_end = _parse_year_month(end)
        if parsed_end is None:
            return 0
        y2, m2 = parsed_end

    months = (y2 - y1) * 12 + (m2 - m1)
    return max(months, 0)


def dedup_key(email: str | None, phone: str | None) -> str | None:
    """Hash de dédoublonnage sur email/téléphone normalisés (§4, table candidates)."""
    if not email and not phone:
        return None
    norm_email = (email or "").strip().lower()
    norm_phone = re.sub(r"\D", "", phone or "")[-8:]
    raw = f"{norm_email}|{norm_phone}"
    return hashlib.sha256(raw.encode()).hexdigest()
