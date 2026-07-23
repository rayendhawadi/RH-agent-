"""
A0 — Orchestrateur, coeur LangGraph (§2.1, §3 : "A0 est un graphe superviseur
LangGraph persisté avec le checkpointer Postgres").

Périmètre de cette migration : le chemin RECEIVED -> PARSED -> SCORED ->
{SHORTLISTED|POOL|DECLINE_PENDING} — c'est exactement ce que couvre le CA
officiel ("tuer le worker au milieu d'un lot de 50 CV -> redémarrer -> le
lot se termine sans aucun doublon"). A5/A6/A8/A9 restent en tâches Celery
classiques : la spec elle-même les décrit comme des sous-graphes/nœuds
invoqués par A0, pas comme le graphe racine, et ils n'ont pas de CA de
résilience équivalent qui justifierait le coût de migration.

Porte humaine (DECLINE_PENDING -> DECLINED) : reste gérée par
state_machine.validate_decline(), pas par interrupt() LangGraph. Un
interrupt() est fait pour une reprise proche dans le temps (le process
attend, ou redémarre vite) ; ici la validation recruteur peut arriver des
heures ou des jours plus tard via un appel REST complètement déconnecté de
ce graphe. Le mécanisme HUMAN_GATES existant (déjà testé) fait exactement
ce qu'il faut sans complexifier inutilement l'exécution du graphe.

Bug latent corrigé au passage par cette migration : avant, parse_application
et score_application_task étaient deux tâches Celery séparées, enchaînées
par un appel `.delay()` fait *après* le commit de PARSED. Si le worker
mourait entre ce commit et cet appel, la candidature restait bloquée en
PARSED pour toujours — rien ne redéclenchait jamais le scoring. Ici, les
deux étapes vivent dans UN seul graphe checkpointé : si l'exécution
s'interrompt après le noeud "parse", le retry Celery rejoue le graphe
depuis l'état sauvegardé, et le noeud "score" s'exécute bien.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfileRow
from app.models.document import Document
from app.models.job import Job
from app.models.score import Score
from app.orchestrator.state_machine import route_to_needs_attention, transition
from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec, JobWeights
from app.services.parsing.extract_profile import extract_candidate_profile
from app.services.parsing.extractors import detect_language, extract_text
from app.services.scoring.pipeline import score_application

logger = logging.getLogger("welyne.a0.graph")

# ScoreCard.verdict (Annexe B) vs machine à états (§2.1) : vocabulaires
# différents, cf. commentaire historique dans l'ancien orchestrator/tasks.py.
_VERDICT_TO_STATUS = {
    "SHORTLIST": "SHORTLISTED",
    "POOL": "POOL",
    "DECLINE_PENDING": "DECLINE_PENDING",
}


class PipelineState(TypedDict):
    application_id: str
    stopped: bool  # True si un noeud a déjà traité l'issue (no-op idempotent
                    # ou routage NEEDS_ATTENTION) -> le graphe s'arrête là.


def _plain_psycopg_dsn(sqlalchemy_url: str) -> str:
    """PostgresSaver attend un DSN psycopg brut (postgresql://...), pas
    l'URL SQLAlchemy (postgresql+psycopg://...) utilisée ailleurs."""
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def get_checkpointer():
    settings = get_settings()
    with PostgresSaver.from_conn_string(_plain_psycopg_dsn(settings.DATABASE_URL_SYNC)) as saver:
        yield saver


def setup_checkpointer() -> None:
    """Crée les tables de checkpoint LangGraph si elles n'existent pas —
    idempotent, à lancer une fois au déploiement (pas à chaque tâche) :

        python -c "from app.orchestrator.graph import setup_checkpointer; setup_checkpointer()"
    """
    with get_checkpointer() as saver:
        saver.setup()


def node_parse(state: PipelineState) -> PipelineState:
    """RECEIVED -> PARSED (A3). Reprend telle quelle la logique métier de
    l'ancien orchestrator/tasks.py::parse_application — seule la façon dont
    l'étape suivante est déclenchée change (edge de graphe, plus `.delay()`)."""
    db = SessionLocal()
    try:
        application = db.get(Application, state["application_id"])
        if application is None or application.status != "RECEIVED":
            return {**state, "stopped": True}  # idempotence

        document = db.query(Document).filter(Document.application_id == application.id).first()
        if document is None:
            route_to_needs_attention(db, application, "aucun document attaché")
            return {**state, "stopped": True}

        raw_text, ocr_used = extract_text(document.storage_path, document.mime)
        document.raw_text = raw_text
        document.ocr_used = ocr_used
        db.add(document)
        db.commit()

        language = detect_language(raw_text)
        profile = extract_candidate_profile(raw_text, language)

        db.add(CandidateProfileRow(
            application_id=application.id,
            profile=profile.model_dump(mode="json"),
            language=language,
            parser_version=profile.parser_version,
        ))

        candidate = db.get(Candidate, application.candidate_id)
        if candidate is not None:
            if not candidate.email and profile.identity.email:
                candidate.email = profile.identity.email
            if not candidate.phone and profile.identity.phone:
                candidate.phone = profile.identity.phone
            db.add(candidate)

        db.commit()
        transition(db, application, "PARSED", actor="agent:a3")
        return {**state, "stopped": False}
    finally:
        db.close()


def node_score(state: PipelineState) -> PipelineState:
    """PARSED -> SCORED -> {SHORTLISTED|POOL|DECLINE_PENDING} (A4). Reprend
    telle quelle la logique de l'ancien score_application_task."""
    db = SessionLocal()
    try:
        application = db.get(Application, state["application_id"])
        if application is None or application.status != "PARSED":
            return {**state, "stopped": True}

        profile_row = (
            db.query(CandidateProfileRow)
            .filter(CandidateProfileRow.application_id == application.id)
            .first()
        )
        job = db.get(Job, application.job_id)
        if profile_row is None or job is None:
            route_to_needs_attention(db, application, "profil ou offre introuvable")
            return {**state, "stopped": True}

        profile = CandidateProfile.model_validate(profile_row.profile)
        job_spec = JobSpec.model_validate(job.job_spec or {"title": job.title})
        weights = JobWeights.model_validate(job.weights or {})

        card = score_application(profile, job_spec, weights)

        db.add(Score(
            application_id=application.id,
            total=card.total,
            subscores=card.subscores.model_dump(),
            verdict=card.verdict,
            justification=card.justification,
            evidence=[e.model_dump() for e in card.evidence],
            hard_filter_failures=card.hard_filter_failures,
            model=card.model,
            prompt_version=card.prompt_version,
            run_seed=card.run_seed,
        ))
        db.commit()

        transition(db, application, "SCORED", actor="agent:a4")
        target_status = _VERDICT_TO_STATUS.get(card.verdict)
        if target_status is None:
            route_to_needs_attention(db, application, f"verdict inconnu : {card.verdict}")
            return {**state, "stopped": True}

        transition(db, application, target_status, actor="agent:a4", payload={"total": card.total})
        return {**state, "stopped": True}  # fin du graphe, rien après SCORED ici
    finally:
        db.close()


def _route_after_parse(state: PipelineState) -> str:
    return END if state["stopped"] else "score"


def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)
    graph.add_node("parse", node_parse)
    graph.add_node("score", node_score)
    graph.set_entry_point("parse")
    graph.add_conditional_edges("parse", _route_after_parse, {"score": "score", END: END})
    graph.add_edge("score", END)
    return graph


def run_pipeline(application_id: str) -> None:
    """Point d'entrée appelé par la tâche Celery (voir orchestrator/tasks.py).
    Un thread_id = un application_id : chaque candidature a son propre fil
    de checkpoint, une reprise ne peut jamais rejouer l'état d'une autre."""
    with get_checkpointer() as checkpointer:
        compiled = build_graph().compile(checkpointer=checkpointer)
        compiled.invoke(
            {"application_id": application_id, "stopped": False},
            config={"configurable": {"thread_id": application_id}},
        )