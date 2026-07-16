"""
Rate-limit générique par IP, basé sur Redis (déjà utilisé par Celery — même
instance, pas de nouvelle dépendance). Fenêtre fixe simple : suffisant pour
protéger /auth/login contre le brute-force sans complexité inutile pour un
MVP (§3 politique stack : gratuit/simple d'abord).

Si Redis est injoignable, on n'échoue JAMAIS une requête à cause du
rate-limiter lui-même (fail-open) : mieux vaut un login sans limite
temporaire qu'un backend qui tombe parce que Redis a un hoquet.
"""
from __future__ import annotations

import logging

import redis

from app.core.config import get_settings

logger = logging.getLogger("welyne.rate_limit")
settings = get_settings()

_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rate-limiter : connexion Redis impossible (%s) — fail-open.", exc)
            return None
    return _client


def is_rate_limited(key: str, max_attempts: int, window_seconds: int) -> bool:
    """
    True si `key` (ex. "login:1.2.3.4") a dépassé `max_attempts` dans la
    fenêtre glissante de `window_seconds`. Compteur simple avec expiration :
    la première requête pose le TTL, les suivantes incrémentent.
    """
    client = _get_client()
    if client is None:
        return False  # fail-open : Redis indisponible ne doit jamais bloquer un login légitime

    try:
        redis_key = f"ratelimit:{key}"
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_seconds)
        return count > max_attempts
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate-limiter : erreur Redis (%s) — fail-open.", exc)
        return False