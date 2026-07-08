"""
Étage 3 du scoring A4 : juge LLM (grille de scoring, Annexe C de la spec).
Profil masqué + JobSpec + pondérations -> ScoreCard avec preuves citées.
Température 0, seed fixe -> cohérence exigée par le KPI écart-type < 5 pts (§1.1, §5.4).
"""
from __future__ import annotations

from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec, JobWeights
from app.schemas.score_card import ScoreCard
from app.services.llm_gateway import complete_structured, TASK_MODELS
from app.services.scoring.pii_mask import mask_profile_for_judge

SYSTEM_PROMPT = """Tu es un evaluateur de recrutement strict et equitable. Score
UNIQUEMENT a partir du profil masque et de la fiche de poste. Cite une preuve
verbatim (courte, < 25 mots) pour chaque sous-score, en indiquant la page si
disponible. Si une information manque, score prudemment et dis-le dans la
justification. Sortie JSON uniquement, conforme au schema ScoreCard. Pas de
noms, pas de suppositions sur l'identite (genre, age, origine, situation
familiale)."""

RUN_SEED = 42


def run_judge(
    profile: CandidateProfile,
    job_spec: JobSpec,
    weights: JobWeights,
    hard_filter_failures: list[str],
    prompt_version: str = "a4@v1",
) -> ScoreCard:
    masked = mask_profile_for_judge(profile)

    user = (
        f"JobSpec:\n{job_spec.model_dump_json(indent=2)}\n\n"
        f"Pondérations par critère (sur 100 au total) :\n{weights.model_dump_json(indent=2)}\n\n"
        f"Échecs de filtres durs déjà détectés (à refléter dans hard_filter_failures) : "
        f"{hard_filter_failures}\n\n"
        f"Profil candidat masqué :\n{masked}\n\n"
        f"Bandes de verdict : total >= 70 -> SHORTLIST ; 45-69 -> POOL ; "
        f"< 45 ou filtre dur échoué -> DECLINE_PENDING."
    )

    card = complete_structured(
        task="judge",
        system=SYSTEM_PROMPT,
        user=user,
        schema=ScoreCard,
        temperature=0.0,
        seed=RUN_SEED,
        trace_name="a4_judge_scorecard",
    )

    card.model = TASK_MODELS["judge"]
    card.prompt_version = prompt_version
    card.run_seed = RUN_SEED
    if hard_filter_failures:
        card.hard_filter_failures = list(set(card.hard_filter_failures + hard_filter_failures))
        card.verdict = "DECLINE_PENDING"

    return card
