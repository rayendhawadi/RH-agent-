"""Schéma ScoreCard — Annexe B de la spec. Sortie de l'agent A4 (juge LLM)."""
from pydantic import BaseModel, Field, confloat
from typing import Literal


class SubScores(BaseModel):
    experience_fit: confloat(ge=0, le=30)
    skills_fit: confloat(ge=0, le=30)
    education_fit: confloat(ge=0, le=20)
    sector_context_fit: confloat(ge=0, le=20)


class Evidence(BaseModel):
    subscore: str
    quote: str
    page: int | None = None


class ScoreCard(BaseModel):
    subscores: SubScores
    total: confloat(ge=0, le=100)
    verdict: Literal["SHORTLIST", "POOL", "DECLINE_PENDING"]
    hard_filter_failures: list[str] = Field(default_factory=list)
    justification: str
    evidence: list[Evidence] = Field(default_factory=list)
    model: str = ""
    prompt_version: str = "a4@v1"
    run_seed: int = 0
