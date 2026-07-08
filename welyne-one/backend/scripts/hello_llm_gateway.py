#!/usr/bin/env python
"""
Porte de démo Phase 0 : "un appel LLM tracé visible dans Langfuse".

Usage :
    python scripts/hello_llm_gateway.py

Nécessite GROQ_API_KEY dans .env (tier gratuit, sans carte — voir §3 de la spec).
Si LANGFUSE_PUBLIC_KEY est renseigné, l'appel est aussi tracé dans Langfuse.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_gateway import complete  # noqa: E402


def main():
    result = complete(
        task="chat",
        system="Tu es l'assistant de démarrage de Welyne One.",
        user="En une phrase, confirme que la passerelle LLM fonctionne.",
        trace_name="hello_world_phase0",
    )
    print("── Réponse du modèle ──────────────────────────────")
    print(result)
    print("────────────────────────────────────────────────────")
    print("Si LANGFUSE_PUBLIC_KEY est configuré, vérifiez la trace 'hello_world_phase0'.")


if __name__ == "__main__":
    main()
