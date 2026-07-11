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


def test_language_requirement_in_free_text_hard_filter_uses_profile_languages():
    """Régression : un critère éliminatoire en texte libre (job_spec.hard_filters,
    ex. "Maîtrise du français") ne doit PAS être comparé par sous-chaîne
    littérale contre skills/experiences/location (qui n'incluent jamais la
    langue déclarée) — sinon un candidat avec languages=[{"lang":"fr"}] est
    refusé à tort alors qu'il maîtrise bien le français."""
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Test", "location": "Tunis"},
            "skills": [{"raw": "Python"}, {"raw": "SQL"}],
            "languages": [{"lang": "fr", "level": "courant"}],
        }
    )
    job_spec = JobSpec(title="Dev", hard_filters=["Maîtrise du français"])
    failures = apply_hard_filters(profile, job_spec)
    assert failures == []


def test_language_requirement_in_free_text_hard_filter_still_fails_when_absent():
    """Symétrique du test précédent : le correctif ne doit pas introduire de
    faux négatif — un candidat sans français doit toujours échouer le
    critère éliminatoire, qu'il soit formulé en texte libre ou structuré."""
    profile = CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Test"},
            "languages": [{"lang": "en", "level": "fluent"}],
        }
    )
    job_spec = JobSpec(title="Dev", hard_filters=["Maîtrise du français"])
    failures = apply_hard_filters(profile, job_spec)
    assert len(failures) == 1
    assert "français" in failures[0].lower() or "francais" in failures[0].lower()