"""
Agent A2 — générateur de messages d'approche (§6-A2). Une fois qu'un profil
intéressant est trouvé manuellement par le recruteur, génère 3 brouillons
(tons différents). L'envoi reste manuel (copier-coller par le recruteur,
spec §6-A2 : "l'envoi reste manuel").
"""
from __future__ import annotations

from app.schemas.job_spec import JobSpec
from app.schemas.sourcing import OutreachSet
from app.services.llm_gateway import complete_structured

_SYSTEM = (
    "Tu es un recruteur qui rédige un premier message d'approche court (3-5 "
    "phrases) pour un profil trouvé sur LinkedIn. Utilise le prénom du "
    "candidat et mentionne un point concret de son profil en lien avec le "
    "poste. Ne promets rien (pas de salaire, pas de garantie d'entretien). "
    "Génère EXACTEMENT 3 variantes : tons 'professionnel', 'convivial', "
    "'direct'. Sortie JSON uniquement, conforme au schéma."
)


def generate_outreach_messages(job_spec: JobSpec, candidate_name: str, candidate_highlight: str = "") -> OutreachSet:
    user = (
        f"JobSpec : {job_spec.model_dump_json()}\n"
        f"Prénom du candidat : {candidate_name}\n"
        f"Point marquant du profil (compétence/expérience visible) : {candidate_highlight or 'non précisé'}"
    )
    return complete_structured(
        "chat", _SYSTEM, user, OutreachSet, temperature=0.4, trace_name="a2/outreach@v1"
    )