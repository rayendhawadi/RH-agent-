"""Schéma JobSpec — sortie de l'agent A1 (fiche de poste structurée)."""
from pydantic import BaseModel, Field


class SalaryRange(BaseModel):
    min: int | None = None
    max: int | None = None
    currency: str = "TND"


class JobSpec(BaseModel):
    title: str
    missions: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)     # indispensables
    nice_to_have: list[str] = Field(default_factory=list)  # atouts
    seniority: str = ""
    languages: list[str] = Field(default_factory=list)
    location: str = ""
    salary_range: SalaryRange = Field(default_factory=SalaryRange)
    hard_filters: list[str] = Field(default_factory=list)  # critères éliminatoires -> A4 étage 1


class JobWeights(BaseModel):
    """Pondérations éditables par le recruteur (curseurs UI)."""
    experience_fit: int = 30
    skills_fit: int = 30
    education_fit: int = 20
    sector_context_fit: int = 20
