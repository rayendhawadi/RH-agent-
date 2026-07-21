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
    "Normalise les compétences quand c'est pertinent. Sortie JSON uniquement.\n\n"
    "RÈGLE DE LANGUE : rédige TOUS les champs texte en français, y compris "
    "seniority, location et languages — même si le brief original contient des "
    "passages en anglais (ex. mention d'un poste 'senior', d'une équipe "
    "'international'). Ne recopie jamais un fragment anglais du brief tel quel "
    "dans un champ de sortie ; traduis-le. Exemple : 'Senior, hybrid, 2 days "
    "remote' -> seniority='Senior (confirmé)', location='Tunis (hybride, "
    "2 jours de télétravail/semaine)'.\n\n"
    "RÈGLE CRITÈRES ÉLIMINATOIRES (hard_filters) : mets dans hard_filters tout "
    "critère qui, s'il n'est pas rempli, doit exclure automatiquement le "
    "candidat AVANT même l'évaluation de son profil — pas seulement les "
    "mentions de visa/éligibilité au travail. Cherche spécifiquement dans le "
    "brief : un seuil MINIMUM d'années d'expérience explicite ('minimum 5 ans', "
    "'au moins 3 ans') ; un niveau de langue explicitement qualifié "
    "d'indispensable/obligatoire ('anglais courant indispensable') ; une "
    "compétence présentée comme non-négociable ('impératif', 'obligatoire', "
    "'sans quoi la candidature ne sera pas retenue'). Le même critère ne doit "
    "PAS apparaître à la fois dans must_have et dans hard_filters : s'il est "
    "éliminatoire, il va dans hard_filters SEULEMENT."
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