"""
Masquage PII avant le juge LLM (§7, contrôle des biais).
Le juge ne voit JAMAIS nom, photo, âge, genre, adresse, nationalité, situation
familiale. Ce module retire ces champs du CandidateProfile avant l'appel LLM.
"""
from __future__ import annotations

from app.schemas.candidate_profile import CandidateProfile


def mask_profile_for_judge(profile: CandidateProfile) -> dict:
    """
    Retourne un dict prêt à être injecté dans le prompt juge, sans identité,
    localisation précise, ni signaux de genre/âge indirects (ex: titres civils).
    """
    data = profile.model_dump()
    data["identity"] = {
        "full_name": "[CANDIDAT MASQUÉ]",
        "email": None,
        "phone": None,
        "location": None,
        "links": [],
    }
    return data
