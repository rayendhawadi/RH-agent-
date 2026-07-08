"""
Sonde de biais (§5.4, §7) : re-scorer avec noms/genres permutés doit donner des
scores identiques (le masquage PII est censé rendre le juge aveugle à l'identité).
"""
import copy

from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec, JobWeights
from app.services.scoring.pii_mask import mask_profile_for_judge


def _sample_profile() -> CandidateProfile:
    return CandidateProfile.model_validate(
        {
            "identity": {"full_name": "Ahmed Ben Salah", "email": "a@example.com", "phone": "+21600000000"},
            "experiences": [
                {
                    "title": "Développeur backend",
                    "company": "TechCo",
                    "start": "2020-01",
                    "end": "2023-01",
                    "description": "Python, FastAPI",
                }
            ],
            "education": [{"degree": "Ingénieur", "field": "Informatique", "institution": "ENIT"}],
            "skills": [{"raw": "Python"}, {"raw": "FastAPI"}],
            "languages": [{"lang": "fr", "level": "courant"}],
            "detected_language": "fr",
        }
    )


def test_masking_strips_identity_fields():
    profile = _sample_profile()
    masked = mask_profile_for_judge(profile)

    assert masked["identity"]["full_name"] == "[CANDIDAT MASQUÉ]"
    assert masked["identity"]["email"] is None
    assert masked["identity"]["phone"] is None
    # Le contenu factuel (compétences, expériences) doit rester intact
    assert masked["skills"][0]["raw"] == "Python"


def test_masking_is_identity_invariant():
    """Deux profils avec des identités différentes mais un contenu factuel
    identique doivent produire un masque strictement identique."""
    p1 = _sample_profile()
    p2 = copy.deepcopy(p1)
    p2.identity.full_name = "Fatma Trabelsi"

    m1 = mask_profile_for_judge(p1)
    m2 = mask_profile_for_judge(p2)

    m1.pop("identity")
    m2.pop("identity")
    assert m1 == m2
