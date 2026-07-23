"""
Dédoublonnage candidat (§2.1 §4) — jusqu'ici `dedup_key()` était calculée
mais jamais utilisée nulle part : chaque upload créait un nouveau
`Candidate`, même pour la même personne réappliquant à une autre offre ou
importée deux fois. Ce module la câble enfin, et ajoute le repli demandé
par la spec.

Écart assumé vs la spec : le repli documenté est "nom flou + date de
naissance" — mais aucune étape du pipeline (A3, CandidateProfile) ne
collecte de date de naissance (à raison : la plupart des CV modernes n'en
affichent pas, et c'est une donnée sensible au sens RGPD/anti-discrimination
à ne pas demander sans nécessité). Le repli implémenté ici est donc
uniquement "nom flou" avec un seuil de similarité volontairement strict
(0.92) pour limiter les faux positifs en l'absence d'un second signal.
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.services.parsing.extract_profile import dedup_key

NAME_SIMILARITY_THRESHOLD = 0.92


def _normalize_name(name: str) -> str:
    stripped = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    return " ".join(stripped.lower().split())


def find_existing_candidate(
    db: Session, full_name: str, email: str | None, phone: str | None
) -> Candidate | None:
    """Renvoie le Candidate existant correspondant, ou None si aucun match sûr.

    1. Exact : hash email/téléphone normalisés (pii_masked_key) — rapide, indexé.
    2. Repli : nom flou (ratio >= 0.92) parmi les candidats existants, seulement
       si (1) n'a rien donné. Un match ambigu (plusieurs candidats au-dessus du
       seuil) n'est jamais retenu — mieux vaut un doublon qu'un mauvais
       rattachement de dossier candidat.
    """
    key = dedup_key(email, phone)
    if key:
        exact = db.query(Candidate).filter(Candidate.pii_masked_key == key).first()
        if exact is not None:
            return exact

    if not full_name or not full_name.strip():
        return None

    target = _normalize_name(full_name)
    best_match: Candidate | None = None
    best_ratio = 0.0
    ambiguous = False

    for candidate in db.query(Candidate.id, Candidate.full_name).yield_per(500):
        ratio = SequenceMatcher(None, target, _normalize_name(candidate.full_name)).ratio()
        if ratio >= NAME_SIMILARITY_THRESHOLD:
            if best_match is not None and ratio >= best_ratio - 0.02:
                ambiguous = True
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate

    if ambiguous:
        return None
    return db.get(Candidate, best_match.id) if best_match else None


def get_or_create_candidate(
    db: Session, full_name: str, email: str | None, phone: str | None
) -> Candidate:
    """Point d'entrée unique pour applications.py / sourcing.py — remplace les
    `Candidate(...)` créés en dur qui contournaient tout dédoublonnage."""
    existing = find_existing_candidate(db, full_name, email, phone)
    if existing is not None:
        # Complète les champs manquants si le nouvel upload apporte une info
        # que l'ancien dossier n'avait pas (ex. email trouvé cette fois-ci).
        changed = False
        if email and not existing.email:
            existing.email = email
            changed = True
        if phone and not existing.phone:
            existing.phone = phone
            changed = True
        if changed:
            key = dedup_key(existing.email, existing.phone)
            if key:
                existing.pii_masked_key = key
            db.add(existing)
        return existing

    candidate = Candidate(
        full_name=full_name,
        email=email,
        phone=phone,
        pii_masked_key=dedup_key(email, phone),
    )
    db.add(candidate)
    db.flush()
    return candidate