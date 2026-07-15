"""
Agent A2 — générateur de requêtes (§6-A2). JobSpec -> synonymes de titre +
chaînes booléennes + X-ray (site:linkedin.com/in ...), classées par précision
attendue décroissante. Le recruteur lance lui-même ces recherches (mode
assistance, pas de scraping — voir décision de conformité §6-A2).
"""
from __future__ import annotations

from app.schemas.job_spec import JobSpec
from app.schemas.sourcing import SourcingQueries
from app.services.llm_gateway import complete_structured

_SYSTEM = (
    "Tu es un expert sourcing recrutement. À partir du JobSpec fourni, génère : "
    "(1) 3 à 6 synonymes du titre de poste (variantes réalistes utilisées sur "
    "LinkedIn/CV, y compris anglais si le poste est technique) ; "
    "(2) 5 à 8 requêtes booléennes combinant titre/synonymes, compétences "
    "indispensables et localisation (opérateurs AND/OR/quotes) ; "
    "(3) 3 à 5 requêtes X-ray Google au format "
    "'site:linkedin.com/in (\"titre1\" OR \"titre2\") compétence localisation'. "
    "Classe chaque liste de la requête la plus précise à la plus large. "
    "Sortie JSON uniquement, conforme au schéma."
)


def generate_sourcing_queries(job_spec: JobSpec) -> SourcingQueries:
    user = job_spec.model_dump_json()
    return complete_structured(
        "chat", _SYSTEM, user, SourcingQueries, temperature=0.3, trace_name="a2/queries@v1"
    )