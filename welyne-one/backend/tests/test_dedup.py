"""Dédoublonnage candidat (§4, table candidates) — hash email/téléphone normalisés."""
from app.services.parsing.extract_profile import dedup_key


def test_same_email_different_case_and_spacing_gives_same_key():
    k1 = dedup_key("Jean.Dupont@Example.com", "+216 20 000 000")
    k2 = dedup_key("jean.dupont@example.com", "20000000")
    assert k1 == k2


def test_no_contact_info_returns_none():
    assert dedup_key(None, None) is None
