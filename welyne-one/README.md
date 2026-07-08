# Welyne One — Agent IA RH

Implémentation **Phase 0 + Phase 1** de la spécification technique v1.0
(voir le PDF fourni). Sans Docker pour l'instant, comme demandé — le
`docker-compose.yml` sera ajouté en fin de projet (phase 4) sans changer le
code applicatif (voir `DECISIONS.md`).

## Ce qui est livré

**Phase 0** (repo, infra locale, hello-world LLM) :
- Repo structuré (backend FastAPI/Celery + frontend Next.js)
- Connexion Postgres 16 + pgvector, migration initiale (toutes les tables §4)
- Auth JWT + bcrypt, rôles admin/recruteur/lecteur
- Passerelle LLM (§5.1) : Groq → Gemini → Mistral → Ollama, retry/backoff,
  validation Pydantic obligatoire
- Registre de prompts (§5.3) versionnés sur disque + sync vers la DB
- Script `hello_llm_gateway.py` (porte de démo phase 0)
- Squelette du jeu de référence (`reference_dataset/`)

**Phase 1** (valeur cœur) :
- **A0** — Orchestrateur : machine à états complète (§2.1), portes humaines
  (HITL) qui bloquent toute transition sensible, audit log, retries Celery
  avec idempotence, routage vers `NEEDS_ATTENTION`
- **A3** — Parsing CV : PyMuPDF/python-docx + repli OCR Tesseract (fra/eng/ara),
  détection de langue, extraction LLM → `CandidateProfile` (Annexe A) validé
  Pydantic, durées calculées en code, dédoublonnage par hash email/téléphone
- **A4** — Scoring : filtres durs (code), embeddings bge-m3 (pré-classement),
  juge LLM masqué (aucune identité visible) → `ScoreCard` (Annexe B), sortie
  citant des preuves
- Dashboard minimal : login, liste/création d'offres, liste/upload de
  candidatures avec statut
- API complète : `/auth`, `/jobs`, `/applications` (upload, liste, détail,
  validation de rejet), `/reports/funnel`, `/candidates/{id}/erase` (RGPD)
- Harnais d'évaluation (§5.4) : précision parseur, corrélation Spearman,
  écart-type de cohérence, sonde de biais — tests exécutables dès maintenant
  pour la logique pure ; les évals sur données réelles s'activent dès que
  `reference_dataset/` est rempli (livrable semaine 2)
- Tests unitaires : machine à états, dédoublonnage, filtres durs, schémas

## Démarrage rapide

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # renseigner GROQ_API_KEY + DATABASE_URL_SYNC + JWT_SECRET + PII_MASK_SALT
alembic upgrade head
python scripts/seed_admin.py admin@welyne.com changeme123
uvicorn app.main:app --reload            # terminal 1
celery -A app.celery_app worker --loglevel=info   # terminal 2 (nécessite redis-server lancé)
```

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Détails complets : `backend/README.md` (installation pas à pas, portes de
démo phase 0 et phase 1, structure du code) et `frontend/README.md`.

## Ce qui n'est PAS encore fait (volontairement, hors phases 0-1)

- A1 (création/publication d'offre par IA), A2 (sourcing), A5 (pré-qualification
  chat), A6 (planification), A7 (communications automatiques), A8 (onboarding),
  A9 (reporting complet) — prévus phases 2 à 4 (§8)
- Le jeu de référence réel (30 CV + annotations) — livrable semaine 2, à
  déposer dans `reference_dataset/`
- Docker / docker-compose — phase 4
- Langfuse auto-hébergé, Cal.com, WhatsApp Cloud API — à installer séparément
  quand les agents correspondants seront implémentés

## Arborescence

```
welyne-one/
  backend/            API FastAPI, Celery, agents A0/A3/A4, evals, prompts, migrations
  frontend/            Dashboard Next.js minimal
  reference_dataset/   Jeu de référence §5.4 (structure + placeholders)
  DECISIONS.md         Registre des écarts de stack et décisions (§3, §8.2)
```
