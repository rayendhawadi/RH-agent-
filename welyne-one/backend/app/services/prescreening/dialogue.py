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
from app.services.messaging.service import resolve_recipient, normalize_phone
from app.orchestrator.state_machine import transition, route_to_needs_attention

logger = logging.getLogger("welyne.a5")

CONSENT = {
    "fr": (
        "Bonjour, je suis l'assistant IA de Welyne. Vos réponses sont enregistrées "
        "pour votre candidature et un humain valide chaque décision. Puis-je vous "
        "poser quelques questions rapides ?"
    ),
    "en": (
        "Hello, I'm Welyne's AI assistant. Your answers are recorded for your "
        "application and a human validates every decision. May I ask you a few "
        "quick questions?"
    ),
    "ar": (
        "مرحباً، أنا المساعد الذكي لشركة Welyne. يتم تسجيل إجاباتك من أجل ترشحك، "
        "ويتحقق شخص من كل قرار. هل يمكنني طرح بعض الأسئلة السريعة؟"
    ),
}
HANDOFF_MESSAGE = {
    "fr": "Bonne question — je transmets cela à notre recruteur, qui reviendra vers vous. Revenons à la question précédente :",
    "en": "Good question — I'm passing that along to our recruiter, who will get back to you. Back to the previous question:",
    "ar": "سؤال جيد — سأحيل هذا إلى المسؤول عن التوظيف وسيتواصل معك. لنعد إلى السؤال السابق:",
}
TIMEOUT_HOURS = 48
MAX_SLOT_RETRIES = 1  # une seule relance en cas d'ambiguïté, puis on n'insiste plus (spec §6-A5)


def _dispatch_external(db: Session, conv: Conversation, body: str) -> None:
    """
    Envoie réellement `body` au candidat si le canal est externe
    (email/whatsapp), via le service A7 (§5.2 — point de passage unique,
    journalisation dans message_log). Le widget web n'en a pas besoin : il
    relit directement /chat/{conv_id}. Jamais bloquant : un échec d'envoi
    ne doit pas casser le dialogue (le message reste au moins visible dans
    /chat/applications/{id}/latest côté dashboard).
    """
    if conv.channel not in ("email", "whatsapp") or not conv.external_ref:
        return
    from app.services.messaging.service import send_message

    try:
        send_message(
            db, conv.application_id, conv.external_ref, "prescreen_message",
            {"body": body}, language=conv.language, channel=conv.channel,
            validated_by="agent:a5", thread_key=str(conv.id),
        )
    except Exception as exc:  # noqa: BLE001 — jamais bloquant pour le dialogue
        logger.warning("Envoi %s A5 échoué (conversation %s) : %s", conv.channel, conv.id, exc)


def start_conversation(db: Session, application: Application, channel: str | None = None) -> Conversation:
    """
    Ouvre le dialogue : plan de questions (LLM) + message de consentement journalisé.

    Choix du canal (spec §5.2/§6-A5) : si `channel` n'est pas imposé explicitement par
    l'appelant (ex. webhook WhatsApp entrant, test dashboard), on applique la même règle
    de priorité que A7 : email renseigné -> "email", sinon téléphone -> "whatsapp",
    sinon repli sur le portail "web".
    """
    plan = _generate_plan(application)
    profile = application.profile.profile if application.profile else {}
    language = profile.get("detected_language") or "fr"
    if language not in CONSENT:
        language = "fr"

    if channel is None:
        recipient = resolve_recipient(application.candidate) if application.candidate else None
        channel = recipient[0] if recipient else "web"

    # external_ref = identifiant du canal externe (adresse email ou numéro
    # WhatsApp normalisé) utilisé pour retrouver CETTE conversation quand une
    # réponse arrive de l'extérieur (webhook WhatsApp, relevé IMAP). Le
    # widget web n'en a pas besoin : le candidat poste directement sur
    # /chat/{conv_id}/message avec l'id de la conversation.
    external_ref = None
    if channel == "email" and application.candidate and application.candidate.email:
        external_ref = application.candidate.email.strip().lower()
    elif channel == "whatsapp" and application.candidate and application.candidate.phone:
        external_ref = normalize_phone(application.candidate.phone)

    conv = Conversation(
        application_id=application.id,
        channel=channel,
        status="OPEN",
        language=language,
        plan=[q.model_dump() for q in plan.questions],
        consent_at=datetime.now(timezone.utc),
        external_ref=external_ref,
    )
    db.add(conv)
    db.flush()

    db.add(Message(conversation_id=conv.id, role="agent", body=CONSENT[language]))
    _dispatch_external(db, conv, CONSENT[language])
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


def _question_text(q: dict, language: str) -> str:
    key = f"question_{language}"
    return q.get(key) or q.get("question_fr") or q.get("question_en", "")


def _ask_next(db: Session, conv: Conversation) -> dict | None:
    pending = _pending_slots(conv)
    if not pending:
        return None
    q = pending[0]
    body = _question_text(q, conv.language)
    db.add(Message(conversation_id=conv.id, role="agent", body=body, slot_id=q["slot_id"]))
    _dispatch_external(db, conv, body)
    return q


def process_incoming(db: Session, conv: Conversation, text: str) -> Conversation:
    """Traite un message candidat : extraction du slot en cours, re-ask si ambigu, flag si hors-script."""
    if conv.status != "OPEN":
        return conv

    db.add(Message(conversation_id=conv.id, role="candidate", body=text))

    pending = _pending_slots(conv)
    current_q = pending[0] if pending else None
    current_slot = current_q["slot_id"] if current_q else None

    if current_slot:
        question_text = _question_text(current_q, conv.language)
        answer = _extract_answer(current_slot, question_text, text)

        if answer.off_topic:
            # sujet hors-script / question sur l'ENTREPRISE -> jamais d'invention de réponse,
            # transfert poli au recruteur ; _ask_next() reposera la question juste après
            # (spec §6-A5)
            conv.flags = [*conv.flags, {
                "slot_id": current_slot, "type": "off_topic_handoff",
                "note": answer.off_topic_question or text,
            }]
            db.add(Message(
                conversation_id=conv.id, role="agent",
                body=HANDOFF_MESSAGE.get(conv.language, HANDOFF_MESSAGE["fr"]),
                slot_id=current_slot,
            ))
            _dispatch_external(db, conv, HANDOFF_MESSAGE.get(conv.language, HANDOFF_MESSAGE["fr"]))
        elif answer.needs_clarification:
            # candidat demande le SENS d'un terme (ex. "c'est quoi un préavis ?") -> connaissance
            # RH générique, sans rapport avec l'entreprise : safe à expliquer. _ask_next()
            # reposera la question juste après. Ne consomme pas de relance (pas une réponse
            # ambiguë : le candidat a juste besoin d'un éclaircissement).
            clarification = answer.clarification_answer or "Je vais reformuler la question."
            db.add(Message(
                conversation_id=conv.id, role="agent", body=clarification, slot_id=current_slot,
            ))
            _dispatch_external(db, conv, clarification)
        elif answer.filled:
            conv.extracted = {**conv.extracted, answer.slot_id: answer.value}
        else:
            retries = dict(conv.retry_counts)
            attempts = retries.get(current_slot, 0)
            if attempts < MAX_SLOT_RETRIES:
                retries[current_slot] = attempts + 1
                conv.retry_counts = retries
                # ambiguïté : une seule relance polie, pas de débat
                retry_body = "Pourriez-vous préciser votre réponse s'il vous plaît ?"
                db.add(Message(
                    conversation_id=conv.id, role="agent",
                    body=retry_body, slot_id=current_slot,
                ))
                _dispatch_external(db, conv, retry_body)
            else:
                # toujours pas clair après relance -> on n'insiste plus, on transmet au recruteur
                conv.extracted = {**conv.extracted, current_slot: "NON_CLARIFIÉ"}
                conv.flags = [*conv.flags, {
                    "slot_id": current_slot, "type": "unclear_after_retry",
                    "note": f"Réponse non clarifiée : « {text} »",
                }]

        if answer.contradiction_note:
            conv.flags = [*conv.flags, {"slot_id": current_slot, "type": "contradiction", "note": answer.contradiction_note}]

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
        "Tu extrais la reponse a UNE question de pre-qualification RH. Ne juge jamais, "
        "ne debats jamais. Distingue TROIS cas, un seul a la fois :\n"
        "1) REPONSE EXPLOITABLE : le candidat repond au fond, meme partiellement ou de "
        "facon quantifiee/qualitative (ex. '50%', 'un peu', '1 an', 'oui', 'non'). "
        "-> filled=true, value=sa reponse reformulee brievement. Ne PAS marquer ambigu "
        "seulement parce que la reponse est partielle, nuancee ou modeste : une reponse "
        "quantifiee ou qualifiee est exploitable, pas ambigue.\n"
        "2) DEMANDE DE CLARIFICATION D'UN TERME : le candidat ne comprend pas un mot ou "
        "le sens de LA QUESTION elle-meme (ex. 'c'est quoi un preavis ?', 'que veut dire "
        "mobilite ?'). -> needs_clarification=true, clarification_answer = une definition "
        "courte et generique du terme RH (connaissance generale, PAS une politique de "
        "l'entreprise), filled=false, off_topic=false.\n"
        "3) QUESTION SUR L'ENTREPRISE : le candidat demande une info specifique a "
        "l'entreprise que tu ne connais pas (avantages, ambiance, salaire propose, "
        "politique interne). -> off_topic=true, off_topic_question=sa question, "
        "filled=false, needs_clarification=false. N'invente JAMAIS une reponse ici.\n"
        "Si la reponse est vraiment incomprehensible/hors-sujet sans etre une question : "
        "filled=false, off_topic=false, needs_clarification=false. "
        "Si elle contredit un CV mentionne implicitement, note-le sans jugement dans "
        "contradiction_note. JSON uniquement conforme a ExtractedAnswer."
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
    conv.flags = [
        *conv.flags,
        *({"type": "positive_signal", "note": s} for s in summary.positive_signals),
        *({"type": "warning_signal", "note": s} for s in summary.warning_signals),
    ]
    db.add(Message(
        conversation_id=conv.id, role="system",
        body="\n".join(summary.summary_lines) or "Pré-qualification terminée.",
    ))

    application = db.get(Application, conv.application_id)
    if application and application.profile:
        application.profile.profile = {**application.profile.profile, "prescreen": conv.extracted}
        db.add(application.profile)

    has_warning_flags = any(
        isinstance(f, dict) and f.get("type") != "positive_signal" for f in conv.flags
    )
    if application:
        if summary.verdict_hint == "review" or has_warning_flags:
            route_to_needs_attention(db, application, reason="A5: signaux à revoir avant PRESCREENED")
        else:
            transition(db, application, "PRESCREENED", actor="agent:a5")


def _summarize(conv: Conversation) -> PrescreenSummary:
    system = (
        "Resume ce dialogue de pre-qualification en 5 lignes maximum, professionnel, "
        "factuel. Separe les signaux en positive_signals (points forts, coherence) et "
        "warning_signals (contradictions, reponses non clarifiees, questions hors-script "
        "transmises au recruteur) — sans jugement, juste des constats factuels. "
        "JSON uniquement conforme a PrescreenSummary."
    )
    user = f"Réponses extraites : {conv.extracted}\nDrapeaux existants : {conv.flags}"
    try:
        return complete_structured("chat", system, user, PrescreenSummary, trace_name="a5/summary@v1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Résumé A5 indisponible : %s", exc)
        warnings = [f["note"] for f in conv.flags if isinstance(f, dict) and f.get("type") != "positive_signal"]
        return PrescreenSummary(
            summary_lines=["Pré-qualification terminée (résumé indisponible)."],
            warning_signals=warnings,
        )


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
            reminder_body = "Petit rappel : pourriez-vous compléter vos réponses ?"
            db.add(Message(conversation_id=conv.id, role="agent", body=reminder_body))
            _dispatch_external(db, conv, reminder_body)
        else:
            conv.status = "PRESCREEN_INCOMPLETE"
            application = db.get(Application, conv.application_id)
            if application:
                route_to_needs_attention(db, application, reason="A5: PRESCREEN_INCOMPLETE (timeout)")
        db.add(conv)
        treated += 1
    db.commit()
    return treated