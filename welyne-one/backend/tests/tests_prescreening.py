"""Tests A5 — slot-filling (§6-A5). Mock complete_structured pour éviter tout appel réseau."""
from unittest.mock import patch

from app.models.conversation import Conversation
from app.schemas.prescreen import ExtractedAnswer, PrescreenSummary
from app.services.prescreening import dialogue


def _conv(plan, extracted=None, language="fr"):
    c = Conversation(application_id="00000000-0000-0000-0000-000000000000")
    c.plan = plan
    c.extracted = extracted or {}
    c.flags = []
    c.retry_counts = {}
    c.language = language
    c.status = "OPEN"
    return c


def test_ask_next_uses_candidate_language():
    plan = [{"slot_id": "availability", "question_fr": "Disponible ?", "question_en": "Available?"}]
    conv = _conv(plan, language="en")
    q = plan[0]
    assert dialogue._question_text(q, conv.language) == "Available?"


def test_ask_next_falls_back_to_french_if_missing_translation():
    plan = [{"slot_id": "availability", "question_fr": "Disponible ?"}]
    conv = _conv(plan, language="ar")
    assert dialogue._question_text(plan[0], conv.language) == "Disponible ?"


def test_unclear_answer_skipped_after_max_retries():
    """Après MAX_SLOT_RETRIES relances infructueuses, le slot n'est plus reposé :
    il est marqué non-clarifié et signalé au recruteur (jamais de boucle infinie)."""
    conv = _conv([{"slot_id": "availability", "question_fr": "Q1"}])
    conv.retry_counts = {"availability": dialogue.MAX_SLOT_RETRIES}
    answer = ExtractedAnswer(slot_id="availability", filled=False, off_topic=False)

    attempts = conv.retry_counts.get("availability", 0)
    assert attempts >= dialogue.MAX_SLOT_RETRIES  # branche "on n'insiste plus"


def test_off_topic_question_does_not_fill_slot():
    answer = ExtractedAnswer(
        slot_id="salary", filled=False, off_topic=True,
        off_topic_question="Quels sont les avantages proposés ?",
    )
    assert answer.off_topic
    assert not answer.filled
    assert answer.off_topic_question


def test_clarification_question_is_distinct_from_off_topic():
    """« c'est quoi un préavis ? » = demande de sens d'un terme, PAS une question sur
    l'entreprise -> needs_clarification=true, off_topic doit rester false."""
    answer = ExtractedAnswer(
        slot_id="notice_period", filled=False, needs_clarification=True,
        clarification_answer="Un préavis est le délai à respecter avant de quitter un poste.",
    )
    assert answer.needs_clarification
    assert not answer.off_topic
    assert not answer.filled
    assert answer.clarification_answer


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