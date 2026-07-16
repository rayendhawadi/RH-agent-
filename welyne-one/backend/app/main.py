"""
Point d'entrée FastAPI — Welyne One, Agent IA RH.
Lancement local sans Docker : `uvicorn app.main:app --reload` (voir README).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import auth, jobs, applications, reports, candidates_erase, interviews, offers, onboarding, prescreen, sourcing, users, audit

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
app.include_router(reports.router)
app.include_router(candidates_erase.router)
app.include_router(prescreen.router)
app.include_router(sourcing.router)
app.include_router(users.router)
app.include_router(audit.router)

@app.get("/health")
def health():
    return {"status": "ok"}
