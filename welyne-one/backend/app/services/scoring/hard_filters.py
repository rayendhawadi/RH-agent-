"""Étage 1 du scoring A4 : filtres durs (code, sans LLM). §6 agent A4."""
from __future__ import annotations

from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec


def apply_hard_filters(profile: CandidateProfile, job_spec: JobSpec) -> list[str]:
    """Retourne la liste des critères éliminatoires échoués (vide = passe l'étage 1)."""
    failures: list[str] = []

    # Langues requises
    profile_langs = {l.lang.lower() for l in profile.languages}
    for required in job_spec.languages:
        if required.lower() not in profile_langs:
            failures.append(f"Langue requise manquante : {required}")

    # Critères éliminatoires génériques déclarés dans le JobSpec (texte libre,
    # vérification best-effort par mots-clés — le juge LLM affine ensuite).
    profile_text = " ".join(
        [profile.identity.location or ""]
        + [s.normalized or s.raw for s in profile.skills]
        + [e.title + " " + e.description for e in profile.experiences]
    ).lower()

    for criterion in job_spec.hard_filters:
        keyword = criterion.lower().strip()
        if keyword and keyword not in profile_text:
            failures.append(f"Critère éliminatoire non confirmé : {criterion}")

    return failures
