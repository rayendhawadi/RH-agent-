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
    total_experience_months: int = 0          # calculé en code (post-traitement A3)
    detected_language: Literal["fr", "en", "ar"] = "fr"
    parser_version: str = "a3@v1"
