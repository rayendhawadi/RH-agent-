.PHONY: install migrate run worker hello evals test seed-admin sync-prompts

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload --port 8000

worker:
	celery -A app.celery_app worker --loglevel=info --pool=solo

hello:
	python scripts/hello_llm_gateway.py

seed-admin:
	python scripts/seed_admin.py admin@welyne.com changeme123

sync-prompts:
	python scripts/sync_prompt_registry.py

test:
	pytest tests/ -v

evals:
	pytest evals/ -v
	@echo "Rapport à copier manuellement vers evals/reports/ pour la démo hebdo (§8.2)"
