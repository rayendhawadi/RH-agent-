"""
Agent A1 — Création & publication d'offres (§6). Transforme un brief brut en
JobSpec structuré (schéma Annexe/§3) + variantes de contenu par canal.
"""
from __future__ import annotations

from app.schemas.job_content import ChannelContent
from app.schemas.job_spec import JobSpec
from app.services.llm_gateway import complete_structured

_SYSTEM_JOBSPEC = (
    "Tu es un assistant RH expert en rédaction de fiches de poste. Transforme "
    "le brief brut fourni en JobSpec structuré : intitulé, missions, critères "
    "indispensables, atouts, séniorité, langues, localisation, fourchette "
    "salariale, et critères éliminatoires (hard_filters) séparés des indispensables. "
    "Normalise les compétences quand c'est pertinent. Sortie JSON uniquement."
)

_SYSTEM_CHANNELS = (
    "Tu es un rédacteur RH. À partir du JobSpec fourni, génère 4 variantes de "
    "contenu de publication : un post LinkedIn engageant, un texte pour job board "
    "classique, un texte pour page carrières, et un message court WhatsApp. "
    "Sortie JSON uniquement, conforme au schéma."
)


def generate_jobspec_from_brief(raw_brief: str) -> JobSpec:
    return complete_structured(
        "extract", _SYSTEM_JOBSPEC, raw_brief, JobSpec, trace_name="a1/jobspec_extract@v1"
    )


def generate_channel_content(job_spec: JobSpec) -> ChannelContent:
    user = job_spec.model_dump_json()
    return complete_structured(
        "chat", _SYSTEM_CHANNELS, user, ChannelContent, trace_name="a1/channel_content@v1"
    )