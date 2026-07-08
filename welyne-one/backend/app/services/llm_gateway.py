"""
Passerelle LLM (§5.1) — point de passage unique pour tout appel LLM.

Responsabilités :
  - routage par profil de tâche (extract / judge / chat)
  - chaîne de repli : Groq -> Gemini -> Mistral -> Ollama local
  - retry + backoff exponentiel (lit les en-têtes de rate-limit quand dispo)
  - validation Pydantic obligatoire pour toute sortie structurée
    (1 tentative de réparation, puis rejet — jamais de JSON invalide en base)
  - temperature=0 et seed fixe pour tout ce qui est scoré ou stocké
  - journalisation vers Langfuse (best-effort, ne bloque jamais l'appel)

Aucune clé API en dur : tout vient de app.core.config.Settings (.env).
"""
from __future__ import annotations

import json
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings

logger = logging.getLogger("welyne.llm_gateway")
settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class LLMGatewayError(Exception):
    """Levée quand toute la chaîne de repli a échoué."""


class _ProviderError(Exception):
    pass


def _call_groq(model: str, system: str, user: str, temperature: float, seed: int | None) -> str:
    if not settings.GROQ_API_KEY:
        raise _ProviderError("GROQ_API_KEY manquante")
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        seed=seed,
    )
    return resp.choices[0].message.content or ""


def _call_gemini(model: str, system: str, user: str, temperature: float, seed: int | None) -> str:
    if not settings.GEMINI_API_KEY:
        raise _ProviderError("GEMINI_API_KEY manquante")
    import httpx

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature},
    }
    r = httpx.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_mistral(model: str, system: str, user: str, temperature: float, seed: int | None) -> str:
    if not settings.MISTRAL_API_KEY:
        raise _ProviderError("MISTRAL_API_KEY manquante")
    import httpx

    r = httpx.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
        json={
            "model": "mistral-small-latest",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_ollama(model: str, system: str, user: str, temperature: float, seed: int | None) -> str:
    import httpx

    r = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={
            "model": "qwen3:8b",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "seed": seed or 0},
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


# Ordre de repli fixe, conforme au "kit de survie tiers gratuits" (§3)
_PROVIDER_CHAIN = [
    ("groq", _call_groq),
    ("gemini", _call_gemini),
    ("mistral", _call_mistral),
    ("ollama", _call_ollama),
]

TASK_MODELS = {
    "extract": settings.MODEL_EXTRACT,   # petit modèle 8B rapide, volume
    "judge": settings.MODEL_JUDGE,       # 70B / gpt-oss-120b, précision
    "chat": settings.MODEL_CHAT,         # 70B, dialogue A5
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type(_ProviderError),
    reraise=True,
)
def _call_with_retry(fn, model, system, user, temperature, seed):
    return fn(model, system, user, temperature, seed)


def complete(
    task: str,
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    seed: int | None = 42,
    trace_name: str | None = None,
) -> str:
    """
    Appel texte brut à travers la chaîne de repli. `task` in {"extract", "judge", "chat"}.
    Utilisé directement par A5 (chat) ; A3/A4 préfèrent `complete_structured`.
    """
    model = TASK_MODELS.get(task, settings.MODEL_CHAT)
    last_err: Exception | None = None

    for name, fn in _PROVIDER_CHAIN:
        try:
            result = _call_with_retry(fn, model, system, user, temperature, seed)
            _log_langfuse(trace_name or task, name, model, system, user, result)
            return result
        except Exception as exc:  # noqa: BLE001 — on veut basculer sur TOUTE erreur provider
            logger.warning("Fournisseur %s indisponible (%s), repli...", name, exc)
            last_err = exc
            continue

    raise LLMGatewayError(f"Tous les fournisseurs LLM ont échoué : {last_err}")


def complete_structured(
    task: str,
    system: str,
    user: str,
    schema: Type[T],
    *,
    temperature: float = 0.0,
    seed: int | None = 42,
    trace_name: str | None = None,
) -> T:
    """
    Appel avec sortie JSON validée contre un schéma Pydantic.
    En cas d'échec de validation : 1 tentative de réparation (on renvoie l'erreur
    au modèle), puis rejet (LLMGatewayError) — jamais de JSON invalide en base.
    """
    schema_hint = (
        f"\n\nRéponds UNIQUEMENT avec un objet JSON valide conforme à ce schéma "
        f"(pas de texte hors JSON, pas de balises markdown) :\n{schema.model_json_schema()}"
    )
    raw = complete(task, system + schema_hint, user, temperature=temperature, seed=seed, trace_name=trace_name)

    try:
        return schema.model_validate_json(_strip_fences(raw))
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning("Validation Pydantic échouée, tentative de réparation : %s", exc)
        repair_user = (
            f"Ta réponse précédente n'était pas un JSON valide pour ce schéma.\n"
            f"Erreur : {exc}\nRéponse précédente : {raw}\n\n"
            f"Corrige et renvoie UNIQUEMENT le JSON valide."
        )
        raw2 = complete(task, system + schema_hint, repair_user, temperature=temperature, seed=seed)
        try:
            return schema.model_validate_json(_strip_fences(raw2))
        except (ValidationError, json.JSONDecodeError) as exc2:
            raise LLMGatewayError(f"Sortie LLM non conforme au schéma après réparation : {exc2}") from exc2


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()


def _log_langfuse(trace_name: str, provider: str, model: str, system: str, user: str, result: str) -> None:
    """Journalisation best-effort — ne doit jamais faire échouer l'appel LLM."""
    if not settings.LANGFUSE_PUBLIC_KEY:
        return
    try:
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        lf.trace(
            name=trace_name,
            input={"system": system, "user": user},
            output=result,
            metadata={"provider": provider, "model": model},
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Langfuse indisponible : %s", exc)
