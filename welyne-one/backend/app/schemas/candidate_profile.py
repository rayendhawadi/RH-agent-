"""
Schéma CandidateProfile — Annexe A de la spec.
Toute sortie LLM d'extraction (A3) DOIT valider ce schéma avant écriture en base.
"""
from pydantic import BaseModel, Field
from typing import Literal


class EvidenceSpan(BaseModel):
    page: int | None = None
    text: str = ""


class Experience(BaseModel):
    title: str
    company: str
    start: str | None = None          # "AAAA-MM"
    end: str | None = None            # "AAAA-MM" | "present"
    duration_months: int = 0          # calculé en code, jamais par le LLM
    description: str = ""
    evidence_span: EvidenceSpan = Field(default_factory=EvidenceSpan)


class Education(BaseModel):
    degree: str
    field: str = ""
    institution: str = ""
    year: int | None = None


class Skill(BaseModel):
    raw: str
    normalized: str | None = None
    level: Literal["basic", "good", "expert"] | None = None


class Language(BaseModel):
    lang: str
    level: str = ""


class Identity(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    identity: Identity
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    # Ajout ciblé pour fiabiliser les filtres durs A4 (§6-A4) : ces deux
    # critères reviennent dans presque toute offre mais n'existaient dans
    # aucun champ structuré, ce qui les rendait invérifiables en code (voir
    # hard_filters.py). Extraits par le LLM à l'étage A3, jamais devinés.
    availability: Literal["immediate", "1_month", "3_months", "unspecified"] = "unspecified"
    work_authorization_country: list[str] = Field(default_factory=list)  # codes pays ISO2, ex. ["TN"]
    total_experience_months: int = 0          # calculé en code (post-traitement A3)
    detected_language: Literal["fr", "en", "ar"] = "fr"
    parser_version: str = "a3@v1"