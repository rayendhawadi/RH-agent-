"""Assemble les 3 étages du scoring A4 en une seule fonction appelable par l'orchestrateur."""
from __future__ import annotations

from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec, JobWeights
from app.schemas.score_card import ScoreCard
from app.services.scoring.hard_filters import apply_hard_filters
from app.services.scoring.judge import run_judge


def score_application(profile: CandidateProfile, job_spec: JobSpec, weights: JobWeights) -> ScoreCard:
    # Étage 1 : filtres durs (rapide, sans LLM)
    failures = apply_hard_filters(profile, job_spec)

    # Étage 2 (rapprochement sémantique) : branché au niveau du lot dans le worker
    # Celery pour trier les CV avant le juge — voir app/services/scoring/embeddings.py.
    # Ici on scoreune candidature isolée, donc on saute directement à l'étage 3.

    # Étage 3 : juge LLM (toujours appelé, même en cas d'échec de filtre dur,
    # pour produire une justification lisible par le recruteur)
    card = run_judge(profile, job_spec, weights, failures)
    return card
