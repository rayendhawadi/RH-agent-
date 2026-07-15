"""Schémas A6 — planification d'entretiens (§6-A6)."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class SlotOut(BaseModel):
    start: datetime  # UTC
    end: datetime     # UTC


class ProposeSlotsRequest(BaseModel):
    candidate_tz: str | None = None  # IANA, ex "Africa/Tunis" ; défaut settings si absent


class BookInterviewRequest(BaseModel):
    interview_id: str
    slot_index: int | None = None          # choisir parmi proposed_slots
    start: datetime | None = None          # ou un créneau libre (hors des 3 proposés)
    end: datetime | None = None
    candidate_tz: str | None = None


class RescheduleRequest(BaseModel):
    interview_id: str
    start: datetime
    end: datetime
    reason: str = ""


class CancelRequest(BaseModel):
    interview_id: str
    reason: str = ""


class InterviewOut(BaseModel):
    id: str
    application_id: str
    status: str
    proposed_slots: list[dict] = Field(default_factory=list)
    slot_start: datetime | None = None
    slot_end: datetime | None = None
    candidate_tz: str
    calendar_ref: str | None = None
    reschedule_count: int = 0

    class Config:
        from_attributes = True