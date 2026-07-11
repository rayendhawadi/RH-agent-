"""
A5 — Agent de pré-qualification conversationnelle (§6-A5).

Sous-graphe de dialogue à état de slot-filling : ouvre avec consentement,
pose les slots un par un, ne débat jamais, redemande une fois en cas
d'ambiguïté, signale (sans juger) le hors-script et les contradictions,
timeout 48h -> une relance -> PRESCREEN_INCOMPLETE.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.models.application import Application
from app.schemas.prescreen import PrescreenPlan, ExtractedAnswer, PrescreenSummary
from app.services.llm_gateway import complete_structured
from app.orchestrator.state_machine import transition, route_to_needs_attention

logger = logging.getLogger("welyne.a5")

CONSENT_FR = (
    "Bonjour, je suis l'assistant IA de Welyne. Vos réponses sont enregistrées "
    "pour votre candidature et un humain valide chaque décision. Puis-je vous "
    "poser quelques questions rapides ?"
)
TIMEOUT_HOURS = 48


def start_conversation(db: Session, application: Application, channel: str = "web") -> Conversation:
    """Ouvre le dialogue : plan de questions (LLM) + message de consentement journalisé."""
    plan = _generate_plan(application)

    conv = Conversation(
        application_id=application.id,
        channel=channel,
        status="OPEN",
        plan=[q.model_dump() for q in plan.questions],
        consent_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.flush()

    db.add(Message(conversation_id=conv.id, role="agent", body=CONSENT_FR))
    _ask_next(db, conv)

    db.commit()
    db.refresh(conv)
    return conv


def _generate_plan(application: Application) -> PrescreenPlan:
    job_spec = application.job.job_spec if application.job else {}
    profile = application.profile.profile if application.profile else {}

    system = (
        "Tu generes un plan de pre-qualification RH : 5 a 8 questions maximum "
        "(disponibilite, preavis, pretentions salariales, mobilite, confirmation "
        "de 2-3 competences cles, verifications eliminatoires). Slot_id court en "
        "snake_case. Sortie JSON uniquement conforme au schema PrescreenPlan."
    )
    user = f"JobSpec: {job_spec}\nProfilCandidat (extrait): {profile}"
    try:
        return complete_structured("chat", system, user, PrescreenPlan, trace_name="a5/questions@v1")
    except Exception as exc:  # noqa: BLE001 — jamais bloquant, fallback minimal
        logger.warning("Plan A5 indisponible, fallback générique : %s", exc)
        from app.schemas.prescreen import PrescreenQuestion
        return PrescreenPlan(questions=[
            PrescreenQuestion(slot_id="availability", question_fr="Quelle est votre disponibilité ?",
                               question_en="What is your availability?"),
            PrescreenQuestion(slot_id="salary_expectation", question_fr="Quelles sont vos prétentions salariales ?",
                               question_en="What are your salary expectations?"),
        ])


def _pending_slots(conv: Conversation) -> list[dict]:
    filled = set(conv.extracted.keys())
    return [q for q in conv.plan if q["slot_id"] not in filled]


def _ask_next(db: Session, conv: Conversation) -> dict | None:
    pending = _pending_slots(conv)
    if not pending:
        return None
    q = pending[0]
    db.add(Message(conversation_id=conv.id, role="agent", body=q["question_fr"], slot_id=q["slot_id"]))
    return q


def process_incoming(db: Session, conv: Conversation, text: str) -> Conversation:
    """Traite un message candidat : extraction du slot en cours, re-ask si ambigu, flag si hors-script."""
    if conv.status != "OPEN":
        return conv

    db.add(Message(conversation_id=conv.id, role="candidate", body=text))

    pending = _pending_slots(conv)
    current_slot = pending[0]["slot_id"] if pending else None

    if current_slot:
        answer = _extract_answer(current_slot, pending[0]["question_fr"], text)
        if answer.filled:
            conv.extracted = {**conv.extracted, answer.slot_id: answer.value}
        else:
            # ambiguïté : une seule relance polie, pas de débat
            db.add(Message(
                conversation_id=conv.id, role="agent",
                body="Pourriez-vous préciser votre réponse s'il vous plaît ?", slot_id=current_slot,
            ))
        if answer.contradiction_note:
            conv.flags = [*conv.flags, {"slot_id": current_slot, "note": answer.contradiction_note}]

    if _pending_slots(conv):
        _ask_next(db, conv)
    else:
        _finalize(db, conv)

    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _extract_answer(slot_id: str, question: str, text: str) -> ExtractedAnswer:
    system = (
        "Tu extrais la reponse a UNE question de pre-qualification RH. Ne juge "
        "jamais, ne debats jamais. Si la reponse est hors-sujet ou trop vague, "
        "filled=false. Si elle contredit un CV mentionne implicitement, note-le "
        "sans jugement dans contradiction_note. JSON uniquement conforme a ExtractedAnswer."
    )
    user = f"slot_id: {slot_id}\nQuestion posée : {question}\nRéponse candidat : {text}"
    try:
        return complete_structured("chat", system, user, ExtractedAnswer, trace_name="a5/extract@v1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Extraction A5 indisponible pour %s : %s", slot_id, exc)
        return ExtractedAnswer(slot_id=slot_id, value=text, filled=True)


def _finalize(db: Session, conv: Conversation) -> None:
    """Toutes les slots remplies : résumé, fusion profil, transition PRESCREENED."""
    summary = _summarize(conv)
    conv.status = "COMPLETED"
    conv.flags = [*conv.flags, *summary.flags]
    db.add(Message(
        conversation_id=conv.id, role="system",
        body="\n".join(summary.summary_lines) or "Pré-qualification terminée.",
    ))

    application = db.get(Application, conv.application_id)
    if application and application.profile:
        application.profile.profile = {**application.profile.profile, "prescreen": conv.extracted}
        db.add(application.profile)

    if application:
        if summary.verdict_hint == "review" or conv.flags:
            route_to_needs_attention(db, application, reason="A5: signaux à revoir avant PRESCREENED")
        else:
            transition(db, application, "PRESCREENED", actor="agent:a5")


def _summarize(conv: Conversation) -> PrescreenSummary:
    system = (
        "Resume ce dialogue de pre-qualification en 5 lignes maximum, professionnel, "
        "factuel. Liste les signaux (contradictions, points forts) sans jugement. "
        "JSON uniquement conforme a PrescreenSummary."
    )
    user = f"Réponses extraites : {conv.extracted}\nDrapeaux existants : {conv.flags}"
    try:
        return complete_structured("chat", system, user, PrescreenSummary, trace_name="a5/summary@v1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Résumé A5 indisponible : %s", exc)
        return PrescreenSummary(summary_lines=["Pré-qualification terminée (résumé indisponible)."])


def check_timeouts(db: Session) -> int:
    """
    A appeler périodiquement (Celery beat). Conversations OPEN sans activité
    depuis TIMEOUT_HOURS : une relance, puis PRESCREEN_INCOMPLETE au 2e dépassement.
    Retourne le nombre de conversations traitées.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=TIMEOUT_HOURS)
    stale = (
        db.query(Conversation)
        .filter(Conversation.status == "OPEN", Conversation.updated_at < cutoff)
        .all()
    )
    treated = 0
    for conv in stale:
        if conv.reminder_sent_at is None:
            conv.reminder_sent_at = datetime.now(timezone.utc)
            db.add(Message(conversation_id=conv.id, role="agent",
                            body="Petit rappel : pourriez-vous compléter vos réponses ?"))
        else:
            conv.status = "PRESCREEN_INCOMPLETE"
            application = db.get(Application, conv.application_id)
            if application:
                route_to_needs_attention(db, application, reason="A5: PRESCREEN_INCOMPLETE (timeout)")
        db.add(conv)
        treated += 1
    db.commit()
    return treated