# Jeu de référence (§5.4) — livrable semaine 2

Structure attendue :
- `cvs/` : 30 CV réels anonymisés (PDF/DOCX/scans, mix FR/EN/AR)
- `job_specs/` : 5 fiches de poste
- `ground_truth/*.json` : annotations manuelles par CV, format :
  ```json
  {
    "cv_filename": "cv_012.pdf",
    "mime": "application/pdf",
    "identity": {"full_name": "..."},
    "experiences": [...],
    "skills_raw": ["Python", "..."]
  }
  ```
- `ground_truth/recruiter_ranking.json` : classement recruteur par offre, format :
  ```json
  {
    "job_spec": { ... JobSpec ... },
    "candidates": [
      {"candidate_id": "cv_012", "profile": { ...CandidateProfile... }, "recruiter_rank": 1}
    ]
  }
  ```

Les fichiers ci-dessus sont des **placeholders vides** : les évals qui en
dépendent (`backend/evals/`) sont automatiquement ignorées (`skip`) tant que
ce dossier n'est pas rempli. Anonymisez systématiquement (retirer nom, photo,
contact) avant de committer un CV réel.
