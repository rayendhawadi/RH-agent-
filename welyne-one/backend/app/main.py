"""
Point d'entrée FastAPI — Welyne One, Agent IA RH.
Lancement local sans Docker : `uvicorn app.main:app --reload` (voir README).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import auth, jobs, applications, reports, candidates_erase, interviews, offers, onboarding, prescreen, sourcing, users, audit, role_templates

logging.basicConfig(
    level=getattr(logging, get_settings().LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Welyne One — Agent IA RH",
    version="1.0.0",
    description="Plateforme de recrutement multi-agents (spécification v1.0, juillet 2026).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(interviews.router)
app.include_router(interviews.public_router)
app.include_router(offers.router)
app.include_router(onboarding.router)
app.include_router(onboarding.public_router)
app.include_router(role_templates.router)
app.include_router(reports.router)
app.include_router(candidates_erase.router)
app.include_router(prescreen.router)
app.include_router(sourcing.router)
app.include_router(users.router)
app.include_router(audit.router)

@app.on_event("startup")
def preload_embedding_model():
    """Le modèle bge-m3 (RAG A8 §6-A8, prescore sémantique A4) est volumineux
    et lent à charger — sans ce préchargement, la PREMIÈRE requête qui en a
    besoin (une question candidat sur le manuel, ou un scoring) paie ce coût
    en plein milieu de la conversation, ce qui ressemble à un blocage. En le
    chargeant ici, ce coût est payé une fois au démarrage du conteneur, visible
    dans les logs de boot plutôt que masqué dans une requête utilisateur."""
    try:
        from app.services.scoring.embeddings import _get_model

        _get_model()
        logging.getLogger("welyne.startup").info("Modèle d'embeddings (bge-m3) préchargé.")
    except Exception:  # noqa: BLE001
        # Ne bloque jamais le démarrage du serveur pour ça — au pire, le
        # chargement paresseux à la première requête reste le filet de
        # sécurité (comportement inchangé par rapport à avant ce fix).
        logging.getLogger("welyne.startup").exception("Échec du préchargement du modèle d'embeddings.")


@app.get("/health")
def health():
    return {"status": "ok"}