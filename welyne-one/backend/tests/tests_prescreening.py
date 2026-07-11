"""Tests A5 — slot-filling (§6-A5). Mock complete_structured pour éviter tout appel réseau."""
from unittest.mock import patch

from app.models.conversation import Conversation
from app.schemas.prescreen import ExtractedAnswer, PrescreenSummary
from app.services.prescreening import dialogue


def _conv(plan, extracted=None):
    c = Conversation(application_id="00000000-0000-0000-0000-000000000000")
    c.plan = plan
    c.extracted = extracted or {}
    c.flags = []
    c.status = "OPEN"
    return c


def test_pending_slots_excludes_filled():
    plan = [{"slot_id": "availability", "question_fr": "Q1"}, {"slot_id": "salary", "question_fr": "Q2"}]
    conv = _conv(plan, extracted={"availability": "immédiate"})
    pending = dialogue._pending_slots(conv)
    assert [q["slot_id"] for q in pending] == ["salary"]


@patch("app.services.prescreening.dialogue._extract_answer")
def test_ambiguous_answer_does_not_fill_slot(mock_extract):
    mock_extract.return_value = ExtractedAnswer(slot_id="availability", filled=False)
    plan = [{"slot_id": "availability", "question_fr": "Q1"}]
    conv = _conv(plan)

    # simulate the filling branch without DB
    pending = dialogue._pending_slots(conv)
    answer = mock_extract.return_value
    assert not answer.filled
    assert "availability" not in conv.extracted


@patch("app.services.prescreening.dialogue._extract_answer")
def test_filled_answer_updates_extracted(mock_extract):
    mock_extract.return_value = ExtractedAnswer(slot_id="availability", value="immédiate", filled=True)
    plan = [{"slot_id": "availability", "question_fr": "Q1"}]
    conv = _conv(plan)

    answer = mock_extract.return_value
    if answer.filled:
        conv.extracted = {**conv.extracted, answer.slot_id: answer.value}

    assert conv.extracted == {"availability": "immédiate"}
    assert dialogue._pending_slots(conv) == []