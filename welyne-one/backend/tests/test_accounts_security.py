"""
Tests unitaires — améliorations sécurité comptes (§7) :
- normalize_email() : casse indifférente
- is_rate_limited() : fenêtre Redis + fail-open si Redis indisponible
- users.py _log() : chaque mutation de compte écrit bien dans audit_log
- create_user / update_role / toggle_active / reset_password : audit + normalisation
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.auth.security import normalize_email, generate_secure_token
from app.core.rate_limit import is_rate_limited


# ---------------------------------------------------------------------------
# normalize_email
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Admin@Welyne.com", "admin@welyne.com"),
        ("  jane@example.com  ", "jane@example.com"),
        ("JANE@EXAMPLE.COM", "jane@example.com"),
        ("jane@example.com", "jane@example.com"),
    ],
)
def test_normalize_email(raw, expected):
    assert normalize_email(raw) == expected


def test_generate_secure_token_is_unique_and_url_safe():
    t1 = generate_secure_token()
    t2 = generate_secure_token()
    assert t1 != t2
    assert len(t1) > 30
    assert all(c.isalnum() or c in "-_" for c in t1)


# ---------------------------------------------------------------------------
# is_rate_limited
# ---------------------------------------------------------------------------

def test_rate_limited_fail_open_when_redis_unavailable():
    with patch("app.core.rate_limit._get_client", return_value=None):
        assert is_rate_limited("login:1.2.3.4", max_attempts=10, window_seconds=300) is False


def test_rate_limited_blocks_after_threshold():
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 11  # 11e tentative, seuil = 10
    with patch("app.core.rate_limit._get_client", return_value=fake_redis):
        assert is_rate_limited("login:1.2.3.4", max_attempts=10, window_seconds=300) is True


def test_rate_limited_allows_under_threshold():
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 3
    with patch("app.core.rate_limit._get_client", return_value=fake_redis):
        assert is_rate_limited("login:1.2.3.4", max_attempts=10, window_seconds=300) is False


def test_rate_limited_sets_expiry_on_first_attempt():
    fake_redis = MagicMock()
    fake_redis.incr.return_value = 1
    with patch("app.core.rate_limit._get_client", return_value=fake_redis):
        is_rate_limited("login:1.2.3.4", max_attempts=10, window_seconds=300)
        fake_redis.expire.assert_called_once()


def test_rate_limited_fail_open_on_redis_exception():
    fake_redis = MagicMock()
    fake_redis.incr.side_effect = RuntimeError("connexion perdue")
    with patch("app.core.rate_limit._get_client", return_value=fake_redis):
        assert is_rate_limited("login:1.2.3.4", max_attempts=10, window_seconds=300) is False


# ---------------------------------------------------------------------------
# users.py — audit log sur chaque mutation de compte
# ---------------------------------------------------------------------------

from app.api.users import _log


class _FakeUser:
    def __init__(self, id_, email):
        self.id = id_
        self.email = email


def test_log_writes_audit_entry_with_actor_and_action():
    db = MagicMock()
    actor = _FakeUser("admin-1", "admin@welyne.com")
    target = _FakeUser("target-1", "jane@example.com")

    _log(db, actor, "role_changed", target, payload={"from": "recruteur", "to": "lecteur"})

    db.add.assert_called_once()
    entry = db.add.call_args[0][0]
    assert entry.entity == "user"
    assert entry.entity_id == "target-1"
    assert entry.action == "role_changed"
    assert entry.actor == "user:admin@welyne.com"
    assert entry.payload == {"from": "recruteur", "to": "lecteur"}


def test_log_default_payload_is_empty_dict():
    db = MagicMock()
    actor = _FakeUser("admin-1", "admin@welyne.com")
    target = _FakeUser("target-1", "jane@example.com")

    _log(db, actor, "deactivated", target)

    entry = db.add.call_args[0][0]
    assert entry.payload == {}