"""Étage 1 du scoring A4 — filtres durs, sans appel LLM."""
from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec
from app.services.scoring.hard_filters import apply_hard_filters


def test_missing_required_language_fails_filter():
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Test"},
            "languages": [{"lang": "fr", "level": "courant"}],
        }
    )
    job_spec = JobSpec(title="Dev", languages=["fr", "en"])
    failures = apply_hard_filters(profile, job_spec)
    assert any("en" in f.lower() or "anglais" in f.lower() for f in failures) or len(failures) > 0


def test_all_languages_present_passes():
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Test"},
            "languages": [{"lang": "fr"}, {"lang": "en"}],
        }
    )
    job_spec = JobSpec(title="Dev", languages=["fr", "en"])
    failures = apply_hard_filters(profile, job_spec)
    assert failures == []
