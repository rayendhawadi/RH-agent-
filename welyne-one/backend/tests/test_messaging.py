"""
Tests unitaires de l'agent A7 — service de messagerie (§5.2).
Pas de DB requise (mocks légers), même convention que test_state_machine.py.

Couvre les critères d'acceptation §6-A7 :
- aucun chemin d'envoi n'existe sans écriture dans message_log ;
- rate-limit 1 message / 4h / candidat, accusés exemptés ;
- la langue du template suit la langue détectée du candidat (§5.2) ;
- le canal de repli WhatsApp est choisi quand aucun email n'est disponible.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.messaging.service import (
    resolve_language,
    resolve_recipient,
    send_message,
)


# ---------------------------------------------------------------------------
# Fakes légers (pas de vraie base de données, cf. tests/test_state_machine.py)
# ---------------------------------------------------------------------------

class _FakeMessageLogQuery:
    """Émule `db.query(MessageLog).filter(...).count()`."""

    def __init__(self, count_value: int):
        self._count_value = count_value

    def filter(self, *args, **kwargs):
        return self

    def count(self):
        return self._count_value


class _FakeProfileRow:
    def __init__(self, language: str):
        self.language = language


class _FakeProfileQuery:
    """Émule `db.query(CandidateProfileRow).filter(...).first()`."""

    def __init__(self, profile_row):
        self._profile_row = profile_row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._profile_row


class FakeDB:
    """
    Session factice : garde trace de tout ce qui est écrit (add/commit) pour
    vérifier qu'aucun envoi ne saute la journalisation, et simule les deux
    requêtes utilisées par le service (rate-limit, langue du profil).
    """

    def __init__(self, *, recent_message_count: int = 0, profile_language: str | None = None):
        self.added = []
        self.commits = 0
        self._recent_message_count = recent_message_count
        self._profile_row = _FakeProfileRow(profile_language) if profile_language else None

    def query(self, model):
        model_name = getattr(model, "__name__", "")
        if model_name == "MessageLog":
            return _FakeMessageLogQuery(self._recent_message_count)
        if model_name == "CandidateProfileRow":
            return _FakeProfileQuery(self._profile_row)
        raise AssertionError(f"Modèle inattendu interrogé dans le test : {model_name}")

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1


# ---------------------------------------------------------------------------
# CA : aucun chemin d'envoi non journalisé n'existe
# ---------------------------------------------------------------------------

def test_successful_send_is_logged():
    db = FakeDB(recent_message_count=0)
    entry = send_message(
        db, "app-1", "candidate@example.com", "ack",
        {"candidate_name": "Jane", "job_title": "Dev"},
    )
    assert db.commits == 1
    assert db.added == [entry]
    assert entry.status == "sent"
    assert entry.rendered_body  # le corps a bien été rendu et stocké


def test_smtp_failure_is_still_logged_with_failed_status(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("SMTP indisponible")

    monkeypatch.setattr("app.services.messaging.service._send_smtp", _boom)
    monkeypatch.setattr("app.services.messaging.service.settings.SMTP_HOST", "smtp.example.com")

    db = FakeDB(recent_message_count=0)
    entry = send_message(
        db, "app-1", "candidate@example.com", "ack",
        {"candidate_name": "Jane", "job_title": "Dev"},
        channel="email",
    )
    assert db.commits == 1  # journalisé même en échec d'envoi
    assert entry.status == "failed"


def test_rate_limited_send_is_still_logged_as_skipped():
    db = FakeDB(recent_message_count=1)  # un message déjà envoyé < 4h
    entry = send_message(
        db, "app-1", "candidate@example.com", "invite_prescreen",
        {"candidate_name": "Jane", "job_title": "Dev"},
    )
    assert db.commits == 1
    assert entry.status == "skipped_rate_limit"
    assert entry.rendered_body == ""  # pas de rendu de template si on n'envoie pas


# ---------------------------------------------------------------------------
# Rate-limit : 1 message / 4h / candidat, accusés exemptés
# ---------------------------------------------------------------------------

def test_non_ack_message_is_blocked_within_rate_limit_window():
    db = FakeDB(recent_message_count=1)
    entry = send_message(
        db, "app-1", "candidate@example.com", "invite_interview",
        {"candidate_name": "Jane", "job_title": "Dev"},
    )
    assert entry.status == "skipped_rate_limit"


def test_ack_is_exempt_from_rate_limit():
    db = FakeDB(recent_message_count=5)  # très au-dessus de la limite
    entry = send_message(
        db, "app-1", "candidate@example.com", "ack",
        {"candidate_name": "Jane", "job_title": "Dev"},
    )
    assert entry.status == "sent"  # jamais bloqué, même si des messages récents existent


# ---------------------------------------------------------------------------
# Langue automatique (§5.2) — resolve_language
# ---------------------------------------------------------------------------

def test_resolve_language_uses_detected_profile_language():
    db = FakeDB(profile_language="en")
    assert resolve_language(db, "app-1") == "en"


def test_resolve_language_defaults_to_french_when_profile_missing():
    db = FakeDB(profile_language=None)
    assert resolve_language(db, "app-1") == "fr"


def test_resolve_language_falls_back_to_french_for_unsupported_language():
    # ex : détection "ar" côté A3, mais seuls fr/en sont couverts par les
    # templates A7 (§5.2, bibliothèque de templates).
    db = FakeDB(profile_language="ar")
    assert resolve_language(db, "app-1") == "fr"


def test_send_message_renders_template_in_resolved_language():
    db = FakeDB(recent_message_count=0)
    entry = send_message(
        db, "app-1", "candidate@example.com", "ack",
        {"candidate_name": "Jane", "job_title": "Dev"},
        language="en",
    )
    assert "Hello Jane" in entry.rendered_body
    assert "Bonjour" not in entry.rendered_body


# ---------------------------------------------------------------------------
# Choix du canal (email prioritaire, repli WhatsApp) — resolve_recipient
# ---------------------------------------------------------------------------

class _FakeCandidate:
    def __init__(self, email=None, phone=None):
        self.email = email
        self.phone = phone


def test_resolve_recipient_prefers_email():
    candidate = _FakeCandidate(email="jane@example.com", phone="+21620000000")
    assert resolve_recipient(candidate) == ("email", "jane@example.com")


def test_resolve_recipient_falls_back_to_whatsapp_without_email():
    candidate = _FakeCandidate(email=None, phone="+21620000000")
    assert resolve_recipient(candidate) == ("whatsapp", "+21620000000")


def test_resolve_recipient_returns_none_without_contact_info():
    candidate = _FakeCandidate(email=None, phone=None)
    assert resolve_recipient(candidate) is None


# ---------------------------------------------------------------------------
# Templates inconnus : échec explicite plutôt qu'un envoi silencieux erroné
# ---------------------------------------------------------------------------

def test_unknown_template_raises_instead_of_sending_garbage():
    db = FakeDB(recent_message_count=0)
    with pytest.raises(ValueError):
        send_message(db, "app-1", "candidate@example.com", "does_not_exist", {})
    assert db.commits == 0  # rien n'est journalisé pour un template invalide