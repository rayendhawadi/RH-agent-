"""
Tâches Celery de l'orchestrateur A0 : parsing (A3) puis scoring (A4), enchaînées
par événements. Idempotentes via (application_id, step, attempt) pour que les
retries (backoff exponentiel, 3 tentatives) ne dupliquent jamais un score.

Lancement local sans Docker :
    celery -A app.celery_app worker --loglevel=info
"""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.candidate import Candidate
from app.models.candidate_profile import CandidateProfileRow
from app.models.document import Document
from app.models.job import Job
from app.models.score import Score
from app.orchestrator.state_machine import transition, route_to_needs_attention
from app.schemas.candidate_profile import CandidateProfile
from app.schemas.job_spec import JobSpec, JobWeights
from app.services.parsing.extract_profile import extract_candidate_profile
from app.services.parsing.extractors import extract_text, detect_language
from app.services.scoring.pipeline import score_application

logger = logging.getLogger("welyne.orchestrator.tasks")

MAX_ATTEMPTS = 3

# ScoreCard.verdict (Annexe B, "SHORTLIST"/"POOL"/"DECLINE_PENDING") utilise un
# vocabulaire différent de la machine à états (§2.1, "SHORTLISTED"/"POOL"/
# "DECLINE_PENDING"). Passer card.verdict tel quel comme to_status faisait
# échouer silencieusement la transition SCORED -> SHORTLISTED (illégale, car
# "SHORTLIST" ≠ "SHORTLISTED"), routant la candidature en NEEDS_ATTENTION au
# lieu de SHORTLISTED — le bouton "Inviter à la pré-qualification" du
# dashboard (conditionné sur status === "SHORTLISTED") n'apparaissait donc
# jamais. Ce mapping explicite évite de supposer que les deux vocabulaires
# coïncident.
_VERDICT_TO_STATUS = {
    "SHORTLIST": "SHORTLISTED",
    "POOL": "POOL",
    "DECLINE_PENDING": "DECLINE_PENDING",
}


@celery_app.task(bind=True, max_retries=MAX_ATTEMPTS, default_retry_delay=5)
def parse_application(self, application_id: str):
    """Étape RECEIVED -> PARSED. Déclenchée après upload d'un document (A3)."""
    db = SessionLocal()
    try:
        application = db.get(Application, application_id)
        if application is None or application.status != "RECEIVED":
            return  # idempotence : déjà traité ou introuvable

        document = (
            db.query(Document).filter(Document.application_id == application.id).first()
        )
        if document is None:
            route_to_needs_attention(db, application, "aucun document attaché")
            return

        raw_text, ocr_used = extract_text(document.storage_path, document.mime)
        document.raw_text = raw_text
        document.ocr_used = ocr_used
        db.add(document)
        db.commit()

        language = detect_language(raw_text)
        profile = extract_candidate_profile(raw_text, language)

        row = CandidateProfileRow(
            application_id=application.id,
            profile=profile.model_dump(mode="json"),
            language=language,
            parser_version=profile.parser_version,
        )
        db.add(row)

        # Backfill Candidate.email / Candidate.phone depuis le profil extrait
        # par A3 quand ils n'ont pas été saisis au formulaire d'upload (§4,
        # table candidates). Sans ce sync, l'accusé de réception A7 et le
        # dédoublonnage (dedup_key) ne voient jamais ces valeurs.
        candidate = db.get(Candidate, application.candidate_id)
        if candidate is not None:
            if not candidate.email and profile.identity.email:
                candidate.email = profile.identity.email
            if not candidate.phone and profile.identity.phone:
                candidate.phone = profile.identity.phone
            db.add(candidate)

        db.commit()

        transition(db, application, "PARSED", actor="agent:a3")
        score_application_task.delay(str(application.id))

    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec parsing application %s", application_id)
        if self.request.retries >= MAX_ATTEMPTS - 1:
            db2 = SessionLocal()
            app2 = db2.get(Application, application_id)
            if app2:
                route_to_needs_attention(db2, app2, f"parsing: {exc}")
            db2.close()
        else:
            raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=MAX_ATTEMPTS, default_retry_delay=5, name="score_application_task")
def score_application_task(self, application_id: str):
    """Étape PARSED -> SCORED -> {SHORTLISTED|POOL|DECLINE_PENDING} (A4)."""
    db = SessionLocal()
    try:
        application = db.get(Application, application_id)
        if application is None or application.status != "PARSED":
            return

        profile_row = (
            db.query(CandidateProfileRow)
            .filter(CandidateProfileRow.application_id == application.id)
            .first()
        )
        job = db.get(Job, application.job_id)
        if profile_row is None or job is None:
            route_to_needs_attention(db, application, "profil ou offre introuvable")
            return

        profile = CandidateProfile.model_validate(profile_row.profile)
        job_spec = JobSpec.model_validate(job.job_spec or {"title": job.title})
        weights = JobWeights.model_validate(job.weights or {})

        card = score_application(profile, job_spec, weights)

        db.add(
            Score(
                application_id=application.id,
                total=card.total,
                subscores=card.subscores.model_dump(),
                verdict=card.verdict,
                justification=card.justification,
                evidence=[e.model_dump() for e in card.evidence],
                model=card.model,
                prompt_version=card.prompt_version,
                run_seed=card.run_seed,
            )
        )
        db.commit()

        transition(db, application, "SCORED", actor="agent:a4")
        target_status = _VERDICT_TO_STATUS.get(card.verdict)
        if target_status is None:
            route_to_needs_attention(db, application, f"verdict inconnu : {card.verdict}")
            return
        transition(db, application, target_status, actor="agent:a4", payload={"total": card.total})

    except Exception as exc:  # noqa: BLE001
        logger.exception("Échec scoring application %s", application_id)
        if self.request.retries >= MAX_ATTEMPTS - 1:
            db2 = SessionLocal()
            app2 = db2.get(Application, application_id)
            if app2:
                route_to_needs_attention(db2, app2, f"scoring: {exc}")
            db2.close()
        else:
            raise self.retry(exc=exc)
    finally:
        db.close()
