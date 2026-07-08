"""Tests unitaires de la machine à états A0 (§2.1) — pas de DB requise (mock léger)."""
from unittest.mock import MagicMock

import pytest

from app.orchestrator.state_machine import (
    transition,
    IllegalTransitionError,
    HumanGateRequiredError,
    validate_decline,
)


class FakeApplication:
    def __init__(self, status):
        self.id = "app-1"
        self.status = status
        self.stage_history = []


def _fake_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


def test_legal_transition_updates_status_and_history():
    app_ = FakeApplication("RECEIVED")
    db = _fake_db()
    transition(db, app_, "PARSED", actor="agent:a3")
    assert app_.status == "PARSED"
    assert len(app_.stage_history) == 1
    assert app_.stage_history[0]["from"] == "RECEIVED"


def test_illegal_transition_routes_to_needs_attention():
    app_ = FakeApplication("RECEIVED")
    db = _fake_db()
    with pytest.raises(IllegalTransitionError):
        transition(db, app_, "HIRED", actor="agent:a3")
    assert app_.status == "NEEDS_ATTENTION"


def test_decline_requires_human_gate():
    """Un agent ne peut pas franchir DECLINE_PENDING -> DECLINED sans passer par validate_decline()."""
    app_ = FakeApplication("DECLINE_PENDING")
    db = _fake_db()
    with pytest.raises(HumanGateRequiredError):
        transition(db, app_, "DECLINED", actor="agent:a4")


def test_validate_decline_is_the_only_legal_path():
    app_ = FakeApplication("DECLINE_PENDING")
    db = _fake_db()
    result = validate_decline(db, app_, recruiter_email="recruteur@welyne.com")
    assert result.status == "DECLINED"
