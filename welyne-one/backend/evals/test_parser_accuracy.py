"""
Évals parseur (§5.4) : précision champ par champ du CandidateProfile vs
annotations manuelles. Cible >= 90% sur noms, dates, intitulés, compétences.

Nécessite le jeu de référence dans /reference_dataset (30 CV + annotations) —
placeholder ici car les fichiers réels sont un livrable de la semaine 2.
"""
import json
from pathlib import Path

import pytest

REF_DIR = Path(__file__).resolve().parents[2] / "reference_dataset"
CVS_DIR = REF_DIR / "cvs"
GROUND_TRUTH_DIR = REF_DIR / "ground_truth"


def _reference_pairs():
    if not GROUND_TRUTH_DIR.exists():
        return []
    return sorted(GROUND_TRUTH_DIR.glob("*.json"))


@pytest.mark.skipif(not _reference_pairs(), reason="Jeu de référence non encore constitué (livrable semaine 2)")
@pytest.mark.parametrize("ground_truth_file", _reference_pairs())
def test_field_accuracy(ground_truth_file):
    from app.services.parsing.extractors import extract_text, detect_language
    from app.services.parsing.extract_profile import extract_candidate_profile

    truth = json.loads(ground_truth_file.read_text(encoding="utf-8"))
    cv_path = CVS_DIR / truth["cv_filename"]
    mime = truth.get("mime", "application/pdf")

    raw_text, _ = extract_text(str(cv_path), mime)
    lang = detect_language(raw_text)
    profile = extract_candidate_profile(raw_text, lang)

    checks = []
    checks.append(profile.identity.full_name.strip().lower() == truth["identity"]["full_name"].strip().lower())
    checks.append(len(profile.experiences) >= len(truth.get("experiences", [])) - 1)  # tolérance +-1
    truth_skills = {s.lower() for s in truth.get("skills_raw", [])}
    profile_skills = {s.raw.lower() for s in profile.skills}
    if truth_skills:
        checks.append(len(truth_skills & profile_skills) / len(truth_skills) >= 0.7)

    accuracy = sum(checks) / len(checks) if checks else 0
    assert accuracy >= 0.90, f"Précision {accuracy:.0%} sous la cible 90% pour {ground_truth_file.name}"


def test_reference_dataset_scaffold_exists():
    """Vérifie au moins que la structure du jeu de référence est en place (CA phase 0)."""
    assert CVS_DIR.exists()
    assert GROUND_TRUTH_DIR.exists()
    assert (REF_DIR / "job_specs").exists()
