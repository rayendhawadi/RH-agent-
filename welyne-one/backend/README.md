# Welyne One — Backend (Phase 0 + Phase 1)

Backend FastAPI + Celery + Postgres/pgvector pour l'Agent IA RH. Ce README
couvre l'exécution **sans Docker** (le Docker Compose officiel sera ajouté en
phase 4 — voir `DECISIONS.md` à la racine du repo).

## 1. Prérequis locaux

- Python 3.11+
- PostgreSQL 16 avec l'extension `pgvector` installée
- Redis (pour Celery)
- Tesseract OCR avec les paquets de langue `fra`, `eng`, `ara`
  (`sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara`)
- Un compte Groq gratuit (console.groq.com) pour la clé API

## 2. Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# éditez .env : GROQ_API_KEY, DATABASE_URL_SYNC, REDIS_URL, JWT_SECRET, PII_MASK_SALT
```

## 3. Base de données

Créez la base localement (exemple avec `psql`) :

```sql
CREATE USER welyne WITH PASSWORD 'welyne';
CREATE DATABASE welyne_one OWNER welyne;
```

Puis appliquez la migration initiale (crée toutes les tables du §4 + extension
`vector`) :

```bash
alembic upgrade head
# ou : make migrate
```

## 4. Démarrer les services (3 terminaux, sans Docker)

```bash
# Terminal 1 — Redis (si pas déjà lancé en service système)
redis-server

# Terminal 2 — API FastAPI
uvicorn app.main:app --reload --port 8000
# ou : make run

# Terminal 3 — Worker Celery (A0 : parsing + scoring en tâche de fond)
celery -A app.celery_app worker --loglevel=info
# ou : make worker
```

## 5. Porte de démo Phase 0

> « `docker compose up` → login → un appel LLM tracé visible dans Langfuse »
> — adapté ici en mode sans Docker :

```bash
# 1. Créer le premier admin
python scripts/seed_admin.py admin@welyne.com changeme123

# 2. Synchroniser le registre de prompts (§5.3)
python scripts/sync_prompt_registry.py

# 3. Login (récupère un token JWT)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@welyne.com","password":"changeme123"}'

# 4. Hello-world passerelle LLM sur Groq
python scripts/hello_llm_gateway.py
```

Si `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` sont renseignés dans `.env`
(instance Langfuse auto-hébergée, à lancer séparément — voir leur doc), la
trace `hello_world_phase0` apparaît dans le dashboard Langfuse.

## 6. Porte de démo Phase 1

> « 50 CV réels + 1 fiche de poste → shortlist classée avec scores appuyés
> sur preuves, export CSV/PDF ; parseur ≥ 95 %, Spearman ≥ 0,75 »

```bash
# Créer une offre
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"title": "Développeur Backend Python"}'

# Téléverser un CV (déclenche A3 -> A4 automatiquement via Celery)
curl -X POST http://localhost:8000/applications/upload \
  -H "Authorization: Bearer <token>" \
  -F "job_id=<uuid>" -F "candidate_full_name=Jane Doe" \
  -F "file=@/chemin/vers/cv.pdf"

# Suivre la shortlist
curl "http://localhost:8000/applications?job=<uuid>&min_score=70" \
  -H "Authorization: Bearer <token>"
```

L'export CSV/PDF de la shortlist n'est pas encore implémenté (prévu avec le
dashboard complet en phase 2, `/reports`) ; `/reports/funnel` donne déjà une
vue agrégée par statut.

## 7. Tests et évaluations

```bash
make test    # tests unitaires (state machine, dédoublonnage, filtres durs, schémas)
make evals   # harnais §5.4 : précision parseur, Spearman, écart-type, sonde de biais
```

Les évals de précision parseur / scoring sont **automatiquement ignorées**
(`skip`) tant que `/reference_dataset` n'est pas rempli avec les 30 CV réels +
annotations (livrable semaine 2, voir `reference_dataset/README.md`). Les
tests de logique pure (state machine, filtres, masquage PII, schémas) tournent
dès maintenant.

## 8. Structure du code

```
app/
  core/           config, connexion DB
  models/         SQLAlchemy — tables du §4
  schemas/        Pydantic — CandidateProfile (Annexe A), ScoreCard (Annexe B), JobSpec
  services/
    llm_gateway.py        passerelle LLM §5.1 (routage, repli, retry, validation)
    parsing/               agent A3 : extraction + OCR + extraction LLM -> CandidateProfile
    scoring/                agent A4 : filtres durs, embeddings, juge LLM -> ScoreCard
  orchestrator/    agent A0 : machine à états, portes humaines, tâches Celery
  auth/            JWT + bcrypt, rôles
  api/             routeurs FastAPI (Annexe D)
prompts/           registre de prompts versionnés §5.3
evals/             harnais d'évaluation §5.4
tests/             tests unitaires
alembic/           migrations
scripts/           hello-world LLM, seed admin, sync des prompts
```
