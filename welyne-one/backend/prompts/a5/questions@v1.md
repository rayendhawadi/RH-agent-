# a5/questions@v1

Génère un plan de pré-qualification de 5 à 8 questions maximum, spécifiques au
poste : disponibilité, préavis, prétentions salariales, mobilité, confirmation
de 2-3 compétences clés, vérifications éliminatoires (issues des critères
éliminatoires du JobSpec).

- `slot_id` : identifiant court en snake_case, stable, utilisé pour le
  slot-filling.
- Chaque question doit exister en FR/EN (AR optionnel en v1).
- Ne jamais inclure de question déjà répondue dans le profil candidat.

Sortie JSON uniquement, conforme au schéma `PrescreenPlan`
(`app/schemas/prescreen.py`).