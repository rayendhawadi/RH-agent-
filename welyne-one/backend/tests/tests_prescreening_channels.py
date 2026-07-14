"""
Tests unitaires — canaux email (IMAP) et WhatsApp (webhook Meta) de l'agent
A5. Pas de vraie connexion IMAP ni de vrai appel réseau : tout est mocké,
même convention que test_messaging.py / test_state_machine.py.

Couvre :
- normalize_phone() : formats variés -> chiffres seuls (§3, format Meta) ;
- email_poller._find_open_conversation() : matching par external_ref puis
  par email candidat en repli ;
- email_poller.poll_prescreen_emails() : route bien vers process_incoming,
  ignore proprement si IMAP non configuré ;
- api.prescreen._find_open_whatsapp_conversation() : matching par numéro ;
- verify_whatsapp_webhook() : handshake Meta (challenge renvoyé / 403).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.messaging.service import normalize_phone
from app.services.prescreening.email_poller import (
    ImapNotConfigured,
    _find_open_conversation,
    poll_prescreen_emails,
)


# ---------------------------------------------------------------------------
# normalize_phone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+216 20 000 000", "21620000000"),
        ("216-20-000-000", "21620000000"),
        ("21620000000", "21620000000"),
        ("+216 20 00 00 00", "21620000000"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


# ---------------------------------------------------------------------------
# email_poller._find_open_conversation
# ---------------------------------------------------------------------------

class _FakeConv:
    def __init__(self, id_, channel="email", status="OPEN", external_ref=None):
        self.id = id_
        self.channel = channel
        self.status = status
        self.external_ref = external_ref


class _FakeConvQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def join(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self._result


class _FakeCandidateQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._result


class FakeDB:
    """DB factice : renvoie une conversation directe, ou None puis un
    candidat + une conversation via le repli, selon le scénario testé."""

    def __init__(self, direct_conv=None, candidate=None, fallback_conv=None):
        self.direct_conv = direct_conv
        self.candidate = candidate
        self.fallback_conv = fallback_conv
        self._call = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Conversation":
            self._call += 1
            # 1er appel : recherche directe par external_ref
            if self._call == 1:
                return _FakeConvQuery(self.direct_conv)
            # 2e appel (repli) : recherche via le candidat trouvé
            return _FakeConvQuery(self.fallback_conv)
        if name == "Candidate":
            return _FakeCandidateQuery(self.candidate)
        raise AssertionError(f"Modèle inattendu : {name}")


def test_find_open_conversation_matches_by_external_ref():
    conv = _FakeConv("c1", external_ref="jane@example.com")
    db = FakeDB(direct_conv=conv)
    assert _find_open_conversation(db, "jane@example.com") is conv


def test_find_open_conversation_falls_back_to_candidate_email():
    fallback = _FakeConv("c2", external_ref=None)
    candidate = MagicMock(id="cand-1")
    db = FakeDB(direct_conv=None, candidate=candidate, fallback_conv=fallback)
    assert _find_open_conversation(db, "jane@example.com") is fallback


def test_find_open_conversation_returns_none_without_match():
    db = FakeDB(direct_conv=None, candidate=None, fallback_conv=None)
    assert _find_open_conversation(db, "unknown@example.com") is None


# ---------------------------------------------------------------------------
# poll_prescreen_emails
# ---------------------------------------------------------------------------

def test_poll_returns_zero_when_imap_not_configured():
    db = MagicMock()
    with patch(
        "app.services.prescreening.email_poller.fetch_unseen_replies",
        side_effect=ImapNotConfigured("no config"),
    ):
        assert poll_prescreen_emails(db) == 0


def test_poll_routes_matched_replies_to_process_incoming():
    db = FakeDB(direct_conv=_FakeConv("c1", external_ref="jane@example.com"))
    with patch(
        "app.services.prescreening.email_poller.fetch_unseen_replies",
        return_value=[("jane@example.com", "Disponible dès lundi.")],
    ), patch("app.services.prescreening.email_poller.process_incoming") as mocked:
        treated = poll_prescreen_emails(db)
        assert treated == 1
        mocked.assert_called_once()


def test_poll_skips_unmatched_replies_without_crashing():
    db = FakeDB(direct_conv=None, candidate=None, fallback_conv=None)
    with patch(
        "app.services.prescreening.email_poller.fetch_unseen_replies",
        return_value=[("stranger@example.com", "Bonjour")],
    ), patch("app.services.prescreening.email_poller.process_incoming") as mocked:
        treated = poll_prescreen_emails(db)
        assert treated == 0
        mocked.assert_not_called()


class _FakeApplication:
    def __init__(self, id_, status="SHORTLISTED"):
        self.id = id_
        self.status = status


class _FakeAppQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self._result


class AutoStartFakeDB:
    """
    Simule le cas : candidat connu (email matché), candidature SHORTLISTED,
    mais AUCUNE conversation n'existe encore nulle part (candidat a répondu
    par email sans jamais cliquer sur le lien de l'invitation A7).
    """

    def __init__(self, candidate, application, existing_conv_for_app=None):
        self.candidate = candidate
        self.application = application
        self.existing_conv_for_app = existing_conv_for_app
        self._conv_calls = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Conversation":
            self._conv_calls += 1
            # appels 1 et 2 (direct + repli de _find_open_conversation) -> rien trouvé
            if self._conv_calls <= 2:
                return _FakeConvQuery(None)
            # 3e appel : vérif "déjà screené ?" dans _find_or_start_conversation
            return _FakeConvQuery(self.existing_conv_for_app)
        if name == "Candidate":
            return _FakeCandidateQuery(self.candidate)
        if name == "Application":
            return _FakeAppQuery(self.application)
        raise AssertionError(f"Modèle inattendu : {name}")


def test_poll_auto_starts_screening_when_candidate_never_clicked_the_link():
    candidate = MagicMock(id="cand-1")
    application = _FakeApplication("app-1")
    db = AutoStartFakeDB(candidate=candidate, application=application, existing_conv_for_app=None)

    new_conv = _FakeConv("c-new", external_ref="jane@example.com")
    with patch(
        "app.services.prescreening.email_poller.fetch_unseen_replies",
        return_value=[("jane@example.com", "ok oui ça m'intéresse bien")],
    ), patch(
        "app.services.prescreening.email_poller.start_conversation", return_value=new_conv
    ) as mocked_start, patch(
        "app.services.prescreening.email_poller.process_incoming"
    ) as mocked_process:
        treated = poll_prescreen_emails(db)
        assert treated == 1
        mocked_start.assert_called_once_with(db, application, channel="email")
        mocked_process.assert_called_once_with(db, new_conv, "ok oui ça m'intéresse bien")


def test_poll_does_not_restart_screening_that_already_has_a_conversation():
    """Un screening existe déjà (autre canal, ou déjà COMPLETED) -> pas de double-démarrage."""
    candidate = MagicMock(id="cand-1")
    application = _FakeApplication("app-1")
    already = _FakeConv("c-old", channel="whatsapp", status="COMPLETED")
    db = AutoStartFakeDB(candidate=candidate, application=application, existing_conv_for_app=already)

    with patch(
        "app.services.prescreening.email_poller.fetch_unseen_replies",
        return_value=[("jane@example.com", "Bonjour")],
    ), patch("app.services.prescreening.email_poller.start_conversation") as mocked_start, patch(
        "app.services.prescreening.email_poller.process_incoming"
    ) as mocked_process:
        treated = poll_prescreen_emails(db)
        assert treated == 0
        mocked_start.assert_not_called()
        mocked_process.assert_not_called()


# ---------------------------------------------------------------------------
# webhook WhatsApp — résolution par numéro + handshake de vérification
# ---------------------------------------------------------------------------

def test_find_open_whatsapp_conversation_matches_by_external_ref():
    from app.api.prescreen import _find_open_whatsapp_conversation

    conv = _FakeConv("c1", channel="whatsapp", external_ref="21620000000")
    db = FakeDB(direct_conv=conv)
    assert _find_open_whatsapp_conversation(db, "21620000000") is conv


def test_whatsapp_webhook_verification_returns_challenge_on_valid_token():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from app.api.prescreen import router, settings as prescreen_settings

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    prescreen_settings.WHATSAPP_VERIFY_TOKEN = "test-token"
    res = client.get(
        "/chat/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "test-token", "hub.challenge": "12345"},
    )
    assert res.status_code == 200
    assert res.text == "12345"


def test_whatsapp_webhook_verification_rejects_bad_token():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from app.api.prescreen import router, settings as prescreen_settings

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    prescreen_settings.WHATSAPP_VERIFY_TOKEN = "test-token"
    res = client.get(
        "/chat/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert res.status_code == 403