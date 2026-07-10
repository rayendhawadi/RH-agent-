"""
Envoi WhatsApp via l'API Meta WhatsApp Business Cloud (§3, tier dev gratuit).
Miroir de `_send_smtp` dans service.py, mais pour le canal WhatsApp.

Nécessite WHATSAPP_TOKEN et WHATSAPP_PHONE_ID dans .env (Annexe E, déjà
présents dans app.core.config.Settings — rien à ajouter côté config).
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("welyne.messaging.whatsapp")
settings = get_settings()

GRAPH_API_VERSION = "v21.0"


class WhatsAppSendError(Exception):
    pass


def send_whatsapp_text(to: str, body: str) -> dict:
    """
    Envoie un message texte simple via l'API Graph de Meta.
    `to` doit être au format international sans '+' (ex: '21612345678').
    """
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_ID:
        raise WhatsAppSendError("WHATSAPP_TOKEN / WHATSAPP_PHONE_ID absents de la config (.env).")

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Échec envoi WhatsApp (%s) : %s", exc.response.status_code, exc.response.text)
        raise WhatsAppSendError(f"WhatsApp API a renvoyé {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        logger.warning("Échec envoi WhatsApp (réseau) : %s", exc)
        raise WhatsAppSendError(str(exc)) from exc