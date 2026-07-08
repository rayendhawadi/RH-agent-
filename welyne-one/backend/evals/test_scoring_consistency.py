"""
Évals scoring (§5.4) :
  - corrélation de rang de Spearman vs classement recruteur >= 0.75
  - écart-type par CV sur 3 passages < 5 points
Nécessite le jeu de référence + classement recruteur (livrable semaine 2).
"""
import json
import statistics
from pathlib import Path

import pytest

REF_DIR = Path(__file__).resolve().parents[2] / "reference_dataset"
RANKING_FILE = REF_DIR / "ground_truth" / "recruiter_ranking.json"


@pytest.mark.skipif(not RANKING_FILE.exists(), reason="Classement recruteur non encore fourni (livrable semaine 2)")
def test_spearman_correlation():
    from scipy.stats import spearmanr
    from app.services.scoring.pipeline import score_application
    from app.schemas.candidate_profile import CandidateProfile
    from app.schemas.job_spec import JobSpec, JobWeights

    ranking = json.loads(RANKING_FILE.read_text(encoding="utf-8"))
    job_spec = JobSpec.model_validate(ranking["job_spec"])
    weights = JobWeights()

    model_scores, recruiter_ranks = [], []
    for entry in ranking["candidates"]:
        profile = CandidateProfile.model_validate(entry["profile"])
        card = score_application(profile, job_spec, weights)
        model_scores.append(card.total)
        recruiter_ranks.append(entry["recruiter_rank"])

    corr, _ = spearmanr(model_scores, recruiter_ranks)
    assert abs(corr) >= 0.75, f"Spearman {corr:.2f} sous la cible 0.75"


@pytest.mark.skipif(not RANKING_FILE.exists(), reason="Jeu de référence non encore fourni")
def test_scoring_stddev_under_5_points():
    from app.services.scoring.pipeline import score_application
    from app.schemas.candidate_profile import CandidateProfile
    from app.schemas.job_spec import JobSpec, JobWeights

    ranking = json.loads(RANKING_FILE.read_text(encoding="utf-8"))
    job_spec = JobSpec.model_validate(ranking["job_spec"])
    weights = JobWeights()

    for entry in ranking["candidates"][:3]:  # échantillon pour ne pas exploser le quota gratuit
        profile = CandidateProfile.model_validate(entry["profile"])
        totals = [score_application(profile, job_spec, weights).total for _ in range(3)]
        stddev = statistics.pstdev(totals)
        assert stddev < 5, f"Écart-type {stddev:.1f} pts >= 5 pour {entry.get('candidate_id')}"
