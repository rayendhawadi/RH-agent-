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



_AVAILABILITY_ORDER = {"immediate": 0, "1_month": 1, "3_months": 3, "unspecified": 99}

# Mots-clés détectant un critère de disponibilité en texte libre, et le délai
# maximal (mois) qu'ils expriment — ex. "dans le mois qui vient" -> 1.
_AVAILABILITY_HINTS = [
    (("immediat", "des que possible", "sans delai"), 0),
    (("mois qui vient", "1 mois", "un mois", "30 jours"), 1),
    (("3 mois", "trois mois", "preavis"), 3),
]

_WORK_AUTH_HINTS = ("droit de travail", "sponsoring", "visa", "autorisation de travail", "work permit")

_COUNTRY_CODES = {
    "tunisie": "TN", "tunisia": "TN", "france": "FR", "maroc": "MA", "morocco": "MA",
    "algerie": "DZ", "algeria": "DZ",
}


def _match_availability(keyword: str) -> int | None:
    for hints, max_months in _AVAILABILITY_HINTS:
        if any(h in keyword for h in hints):
            return max_months
    return None


def _match_work_auth_country(keyword: str) -> str | None:
    if not any(h in keyword for h in _WORK_AUTH_HINTS):
        return None
    for name, code in _COUNTRY_CODES.items():
        if name in keyword:
            return code
    return ""  # critère de droit de travail détecté mais pays non identifié


def apply_hard_filters(profile: CandidateProfile, job_spec: JobSpec) -> list[str]:
    """Retourne la liste des critères éliminatoires échoués (vide = passe l'étage 1).

    Un critère en texte libre qui ne correspond à AUCUN champ structuré connu
    (langue, ancienneté, disponibilité, droit de travail) n'est plus rejeté par
    sous-chaîne littérale contre un texte restreint (location+skills+expériences) :
    ce match échouait quasi systématiquement même pour un candidat éligible (ex.
    "Ressortissante tunisienne, autorisée à travailler..." dans le profil du CV
    ne match jamais "Droit de travail en Tunisie (pas de sponsoring visa)" mot
    pour mot). Un critère non vérifiable en code n'est plus auto-décliné ; il
    reste silencieux ici (le juge LLM, étage 3, voit toujours le profil complet)."""
    failures: list[str] = []

    profile_langs = {_lang_code(l.lang) for l in profile.languages}
    for required in job_spec.languages:
        if _lang_code(required) not in profile_langs:
            failures.append(f"Langue requise manquante : {required}")

    for criterion in job_spec.hard_filters:
        keyword = _strip_accents(criterion.lower().strip())
        if not keyword:
            continue

        lang_req = _extract_language_requirement(keyword)
        if lang_req is not None:
            if lang_req not in profile_langs:
                failures.append(f"Langue requise manquante : {criterion}")
            continue

        years_match = _YEARS_PATTERN.search(keyword)
        if years_match:
            low = int(years_match.group(1))
            candidate_years = profile.total_experience_months / 12
            if candidate_years < low:
                failures.append(
                    f"Critère éliminatoire non confirmé : {criterion} "
                    f"(profil : {candidate_years:.1f} ans)"
                )
            continue

        max_months = _match_availability(keyword)
        if max_months is not None:
            if _AVAILABILITY_ORDER[profile.availability] > max_months:
                failures.append(f"Disponibilité insuffisante : {criterion}")
            continue

        country = _match_work_auth_country(keyword)
        if country is not None:
            countries = set(profile.work_authorization_country)
            if country and country not in countries:
                failures.append(f"Droit de travail non confirmé : {criterion}")
            elif not country and not countries:
                failures.append(f"Droit de travail non confirmé : {criterion}")
            continue

        # Critère générique sans champ structuré connu : invérifiable en code,
        # on ne décline plus automatiquement dessus (voir docstring).

    return failures