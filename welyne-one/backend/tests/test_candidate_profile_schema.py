"""Validation basique du schéma CandidateProfile (Annexe A)."""
from app.schemas.candidate_profile import CandidateProfile


def test_minimal_valid_profile():
    profile = CandidateProfile.model_validate({"identity": {"full_name": "Jane Doe"}})
    assert profile.detected_language == "fr"
    assert profile.experiences == []


def test_experience_duration_defaults_to_zero_before_postprocessing():
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Jane Doe"},
            "experiences": [{"title": "Dev", "company": "Acme", "start": "2020-01", "end": "2022-01"}],
        }
    )
    assert profile.experiences[0].duration_months == 0  # calculé plus tard, en code
