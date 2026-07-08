# Welyne One — Dashboard (Phase 1, minimal)

Dashboard Next.js 15 minimal : login, liste/création d'offres, liste/upload de
candidatures avec statut. Volontairement simple — le dashboard complet
(pipeline, preuves de score dépliables, éditeur de pondérations) arrive en
phase 2 (§8).

## Lancer en local (sans Docker)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # pointe vers http://localhost:8000 par défaut
npm run dev
```

Ouvrez http://localhost:3000. Connectez-vous avec le compte créé via
`python scripts/seed_admin.py` côté backend.
