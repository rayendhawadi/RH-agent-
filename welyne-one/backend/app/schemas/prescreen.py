"""
Schémas A5 — pré-qualification conversationnelle (§6-A5).
Toute sortie LLM (plan de questions, extraction de réponse) DOIT valider ces
schémas avant écriture en base (même règle que A3/A4).
"""
from pydantic import BaseModel, Field
from typing import Literal


class PrescreenQuestion(BaseModel):
    slot_id: str                       # ex: "availability", "notice_period", "salary_expectation"
    question_fr: str
    question_en: str
    question_ar: str = ""
    required: bool = True


class PrescreenPlan(BaseModel):
    """Sortie LLM du générateur de questions — 5 à 8 slots max (spec §6-A5)."""
    questions: list[PrescreenQuestion] = Field(default_factory=list)


class ExtractedAnswer(BaseModel):
    """Sortie LLM de l'extracteur de réponse — un tour de dialogue."""
    slot_id: str
    value: str = ""
    filled: bool = False               # False si la réponse est ambiguë -> reposer une fois
    contradiction_note: str = ""       # signalé, jamais jugé (spec: "pas jugées")
    off_topic: bool = False            # candidat pose une question sur l'ENTREPRISE (avantages, ambiance...)
    off_topic_question: str = ""       # la question du candidat, pour transfert au recruteur
    needs_clarification: bool = False  # candidat demande le SENS d'un terme de la question (ex. "préavis ?")
    clarification_answer: str = ""     # courte définition générique du terme, PAS d'info sur l'entreprise


class PrescreenSummary(BaseModel):
    """Résumé de 5 lignes produit en fin de dialogue (spec §6-A5)."""
    summary_lines: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    warning_signals: list[str] = Field(default_factory=list)
    verdict_hint: Literal["proceed", "review"] = "proceed"