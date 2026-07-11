"""Étage 1 du scoring A4 : filtres durs (code, sans LLM). §6 agent A4.

Correctif : la version initiale comparait job_spec.languages et
job_spec.hard_filters par simple sous-chaîne littérale contre le texte du
profil. Deux faux positifs en découlaient :
  1. "français" ne matchait pas si le parseur A3 avait écrit "French"/"Francais".
  2. Un critère "3-5 ans" ne matchait jamais, car total_experience_months est
     une valeur calculée, jamais écrite en toutes lettres dans le CV.
Ce fichier corrige les deux : normalisation langue (accents/casse/synonymes)
et extraction numérique des critères d'ancienneté.
"""
from __future__ import annotations

import re
import unicodedata

from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec

# Texte libre recruteur (job_spec.languages) -> code canonique CandidateProfile.Language.lang
_LANGUAGE_CODES = {
    "fr": "fr", "french": "fr", "francais": "fr", "francaise": "fr",
    "en": "en", "english": "en", "anglais": "en", "anglaise": "en",
    "ar": "ar", "arabic": "ar", "arabe": "ar",
}


def _lang_code(text: str) -> str:
    """Ramène un libellé de langue en texte libre à un code canonique (fr/en/ar)
    comparable directement à CandidateProfile.Language.lang."""
    normalized = _strip_accents(text).lower().strip()
    return _LANGUAGE_CODES.get(normalized, normalized[:2])

# Détecte "3 ans", "3-5 ans", "3 à 5 ans", "minimum 3 ans", etc.
_YEARS_PATTERN = re.compile(
    r"(\d+)\s*(?:-|à|a|to)?\s*(\d+)?\s*an", re.IGNORECASE
)


def _extract_language_requirement(normalized_criterion: str) -> str | None:
    """Si un critère éliminatoire en texte libre (job_spec.hard_filters) mentionne
    une langue connue (ex. "maîtrise du français", "bon niveau d'anglais"),
    retourne son code canonique fr/en/ar. Sinon None.

    Correctif bug : ces critères en texte libre étaient comparés par sous-chaîne
    littérale contre profile_text (location + skills + experiences), qui
    n'inclut PAS profile.languages. Un candidat avec languages=[{"lang":"fr"}]
    était donc refusé à tort dès que le recruteur formulait l'exigence de
    langue dans hard_filters plutôt que dans le champ languages structuré.
    """
    for token in re.findall(r"[a-z]+", normalized_criterion):
        if token in _LANGUAGE_CODES:
            return _LANGUAGE_CODES[token]
    return None


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )



def apply_hard_filters(profile: CandidateProfile, job_spec: JobSpec) -> list[str]:
    """Retourne la liste des critères éliminatoires échoués (vide = passe l'étage 1)."""
    failures: list[str] = []

    # Langues requises — profile.lang est désormais un code canonique (fr/en/ar/other,
    # cf. schéma CandidateProfile.Language) ; seule la saisie recruteur (job_spec,
    # texte libre) doit encore être ramenée à un préfixe comparable.
    # Langues requises — _lang_code() normalise les DEUX côtés, que le profil
    # contienne déjà un code canonique ("fr") ou du texte libre ("Français")
    # selon que le schéma CandidateProfile.Language a été mis à jour ou non.
    profile_langs = {_lang_code(l.lang) for l in profile.languages}
    for required in job_spec.languages:
        if _lang_code(required) not in profile_langs:
            failures.append(f"Langue requise manquante : {required}")

    profile_text = _strip_accents(" ".join(
        [profile.identity.location or ""]
        + [s.normalized or s.raw for s in profile.skills]
        + [e.title + " " + e.description for e in profile.experiences]
    ).lower())

    for criterion in job_spec.hard_filters:
        keyword = _strip_accents(criterion.lower().strip())
        if not keyword:
            continue

        # Critère de langue en texte libre (ex. "maîtrise du français") :
        # comparer contre profile_langs (structuré) plutôt que par sous-chaîne
        # littérale, qui échoue systématiquement puisque profile_text ne
        # contient pas profile.languages. Voir docstring de la fonction.
        lang_req = _extract_language_requirement(keyword)
        if lang_req is not None:
            if lang_req not in profile_langs:
                failures.append(f"Langue requise manquante : {criterion}")
            continue

        years_match = _YEARS_PATTERN.search(keyword)
        if years_match:
            # Critère d'ancienneté numérique : comparer à total_experience_months
            # (calculé en code, cf. §6-A3) au lieu d'un match texte littéral.
            low = int(years_match.group(1))
            high = int(years_match.group(2)) if years_match.group(2) else low
            candidate_years = profile.total_experience_months / 12
            if candidate_years < low:
                failures.append(
                    f"Critère éliminatoire non confirmé : {criterion} "
                    f"(profil : {candidate_years:.1f} ans)"
                )
            continue  # ne pas aussi tenter le match texte pour ce critère

        if keyword not in profile_text:
            failures.append(f"Critère éliminatoire non confirmé : {criterion}")

    return failures
