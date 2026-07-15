"""Schémas A2 — sourcing (§6-A2). Sorties LLM validées Pydantic (même règle que A1/A3/A4)."""
from pydantic import BaseModel, Field


class SourcingQueries(BaseModel):
    """5 à 10 chaînes de recherche, classées par précision attendue décroissante (spec §6-A2)."""
    title_synonyms: list[str] = Field(default_factory=list)     # ex. "Backend Developer", "Software Engineer"
    boolean_queries: list[str] = Field(default_factory=list)    # ex. Python AND FastAPI AND Docker AND Tunisia
    xray_queries: list[str] = Field(default_factory=list)       # ex. site:linkedin.com/in ("Python Developer" OR ...)


class OutreachMessage(BaseModel):
    tone: str        # "professionnel" | "convivial" | "direct"
    message: str


class OutreachSet(BaseModel):
    messages: list[OutreachMessage] = Field(default_factory=list)  # 3 tons (spec §6-A2)