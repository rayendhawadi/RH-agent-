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


def test_eligible_candidate_not_declined_on_availability_and_work_auth():
    """Régression : candidate disponible immédiatement + droit de travail TN
    déclarés (champs structurés) ne doit plus échouer sur ces critères, même
    si les phrases du recruteur n'apparaissent jamais mot pour mot dans le CV."""
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Sarra"},
            "languages": [{"lang": "fr"}],
            "availability": "immediate",
            "work_authorization_country": ["TN"],
        }
    )
    job_spec = JobSpec(
        title="Dev",
        languages=["fr"],
        hard_filters=[
            "Disponibilité pour démarrer dans le mois qui vient",
            "Droit de travail en Tunisie (pas de sponsoring visa)",
        ],
    )
    assert apply_hard_filters(profile, job_spec) == []
