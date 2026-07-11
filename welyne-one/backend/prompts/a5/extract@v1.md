# a5/extract@v1

Extrait la réponse candidat à UNE question de pré-qualification.

Règles :
- Ne jamais débattre, ne jamais juger.
- `filled=false` si la réponse est hors-sujet, vague, ou évite la question —
  déclenche une seule relance polie côté agent.
- Si la réponse semble contredire une information du CV, le signaler dans
  `contradiction_note` de façon neutre et factuelle (jamais accusatoire).

Sortie JSON uniquement, conforme au schéma `ExtractedAnswer`
(`app/schemas/prescreen.py`).