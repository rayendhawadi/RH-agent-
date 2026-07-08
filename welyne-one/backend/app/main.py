"""
Point d'entrée FastAPI — Welyne One, Agent IA RH.
Lancement local sans Docker : `uvicorn app.main:app --reload` (voir README).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, jobs, applications, reports, candidates_erase

app = FastAPI(
    title="Welyne One — Agent IA RH",
    version="1.0.0",
    description="Plateforme de recrutement multi-agents (spécification v1.0, juillet 2026).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # dashboard Next.js en dev local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(reports.router)
app.include_router(candidates_erase.router)


@app.get("/health")
def health():
    return {"status": "ok"}
