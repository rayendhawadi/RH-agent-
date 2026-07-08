# DECISIONS.md

Registre des écarts par rapport à la politique « gratuit & OSS d'abord » (§3
de la spec) et des décisions d'architecture notables. Chaque écart doit être
justifié ici avant merge (§8.2, méthodes de travail non négociables).

Format :

## AAAA-MM-JJ — Titre court
**Contexte :** ...
**Décision :** ...
**Alternative gratuite écartée :** ...
**Justification :** ...
**Responsable :** ...

---

## 2026-07-08 — Docker repoussé à la phase 4

**Contexte :** La spec prévoit `docker compose up` dès la phase 0. La demande
initiale du projet est de livrer les phases 0 et 1 sans Docker.

**Décision :** Phase 0 et 1 livrées avec un mode d'exécution local (venv
Python + Postgres/Redis installés localement). Le `docker-compose.yml` et les
Dockerfiles seront ajoutés en fin de projet (phase 4), sans changement de
code applicatif — uniquement l'emballage.

**Alternative gratuite écartée :** aucune — ce n'est pas un écart de stack
payante, seulement un séquencement d'implémentation demandé explicitement.

**Justification :** aucun impact sur le choix des technologies (toujours
Postgres 16, Redis, FastAPI, Celery) ; seul le mode de déploiement change.

**Responsable :** équipe stagiaires — à valider avec Welyne avant la démo
finale.

---

## 2026-07-08 — Frontend minimal en Phase 1

**Contexte :** §8, phase 1 exige une « liste minimale dashboard ».

**Décision :** livrer un dashboard Next.js 15 réellement fonctionnel mais
volontairement minimal (liste des offres, liste des candidatures avec score),
sans authentification UI complète (le token JWT est saisi une fois et stocké
en mémoire côté client pour la démo). L'auth UI complète (login persistant,
gestion de session) arrive en phase 2 avec le reste du dashboard (§8, phase 2
« vue pipeline »).

**Justification :** respecte le périmètre exact du CA de démo 1 (§8) sans
sur-livrer du travail de phase 2.

**Responsable :** équipe stagiaires.
