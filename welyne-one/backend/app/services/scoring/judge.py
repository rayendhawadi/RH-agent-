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
familiale).

IMPORTANT — role et limites : tu evalues UNIQUEMENT les 4 sous-scores
(experience_fit, skills_fit, education_fit, sector_context_fit) et tu rediges
une justification qui porte EXCLUSIVEMENT sur l'adequation du candidat aux
exigences du poste. Le respect des criteres eliminatoires (hard_filters,
langues requises) est verifie ailleurs, par du code deterministe, jamais par
toi. En consequence :
- Ne mentionne JAMAIS dans ta justification une notion de refus, de rejet, ou
  d'elimination liee a un critere du champ hard_filters ou languages du
  JobSpec — ce n'est pas ton role et cette phrase serait trompeuse pour le
  recruteur qui lit la ScoreCard.
- Si un critere du JobSpec exprime une fourchette (ex. "3-5 ans
  d'experience"), traite-la comme un minimum a atteindre : un candidat qui la
  depasse est au moins aussi qualifie, jamais moins. Ne penalise pas et
  n'evoque pas de disqualification pour ce motif dans experience_fit ni dans
  la justification.
- Remplis quand meme le champ "verdict" avec une valeur valide (il sera
  recalcule par le systeme) et laisse "hard_filter_failures" vide : []."""

RUN_SEED = 42

# Bandes de verdict par défaut (§6 A4, configurable par offre plus tard).
_SHORTLIST_THRESHOLD = 70
_POOL_THRESHOLD = 45


def _compute_verdict(total: float, hard_filter_failures: list[str]) -> str:
    """Calcule le verdict de façon 100% déterministe (code), à partir du score
    total et des SEULS échecs de filtres durs détectés par apply_hard_filters().

    Correctif bug : auparavant, ScoreCard.verdict était un champ Literal rempli
    librement par le LLM. Le code ne faisait que forcer DECLINE_PENDING quand
    un échec de filtre dur était détecté côté code, mais ne corrigeait jamais
    l'inverse : si le code ne détectait aucun échec, le verdict du LLM était
    conservé tel quel. Or le LLM voit le JobSpec brut (y compris les critères
    hard_filters en texte libre, ex. "3-5 ans") et peut les réinterpréter à sa
    façon — par ex. rejeter un candidat de 7 ans d'expérience en lisant "3-5
    ans" comme une fourchette stricte, alors que apply_hard_filters() ne
    vérifie à raison que le minimum. Résultat : un candidat scoré 86/100
    pouvait être marqué DECLINE_PENDING sur la seule initiative du LLM, en
    contradiction avec le principe §6 A4 "filtres durs (code, sans LLM)".
    """
    if hard_filter_failures:
        return "DECLINE_PENDING"
    if total >= _SHORTLIST_THRESHOLD:
        return "SHORTLIST"
    if total >= _POOL_THRESHOLD:
        return "POOL"
    return "DECLINE_PENDING"


def run_judge(
    profile: CandidateProfile,
    job_spec: JobSpec,
    weights: JobWeights,
    hard_filter_failures: list[str],
    prompt_version: str = "a4@v2",
) -> ScoreCard:
    masked = mask_profile_for_judge(profile)

    user = (
        f"JobSpec:\n{job_spec.model_dump_json(indent=2)}\n\n"
        f"Pondérations par critère (sur 100 au total) :\n{weights.model_dump_json(indent=2)}\n\n"
        f"Note : les champs 'hard_filters' et 'languages' ci-dessus sont fournis "
        f"pour contexte uniquement. Leur respect est déjà vérifié par le système "
        f"en dehors de ce prompt (résultat actuel : "
        f"{'aucun échec' if not hard_filter_failures else hard_filter_failures}). "
        f"N'en tiens pas compte pour noter experience_fit ou toute autre "
        f"sous-note, et ne les mentionne pas dans ta justification.\n\n"
        f"Profil candidat masqué :\n{masked}\n\n"
        f"Évalue uniquement l'adéquation du candidat aux 4 sous-scores."
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

    # hard_filter_failures reflète UNIQUEMENT les échecs détectés par le code
    # (apply_hard_filters, déterministe) — pas ceux que le LLM aurait pu
    # ajouter de sa propre initiative en réinterprétant le JobSpec brut.
    card.hard_filter_failures = list(hard_filter_failures)

    # Verdict 100% déterministe : score total + échecs de filtres durs (code).
    # Le champ verdict renvoyé par le LLM est ignoré (voir _compute_verdict).
    card.verdict = _compute_verdict(card.total, hard_filter_failures)

    return card
