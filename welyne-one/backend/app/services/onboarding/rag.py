"""
RAG sur le manuel d'entreprise (Agent A8, §6-A8) — Q&R avec citations
vérifiables : chaque réponse peut être tracée jusqu'à une page réelle du
manuel, jamais une simple affirmation en l'air.

Design des citations : plutôt que de demander au LLM de générer des
numéros de page (il pourrait en inventer), on numérote nous-mêmes les
chunks récupérés côté retrieval, on demande au LLM d'indiquer LESQUELS il a
réellement utilisés (sources_used, sortie JSON validée par Pydantic via
complete_structured), puis on reconstruit les citations (page + court
extrait) à partir de nos propres métadonnées de chunk — jamais depuis ce
que le LLM prétend.
"""
from __future__ import annotations

import fitz  # PyMuPDF
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.manual_chunk import ManualChunk
from app.models.embedding import Embedding
from app.services.scoring.embeddings import embed_text
from app.services.llm_gateway import complete_structured

_EXCERPT_MAX_LEN = 180


class OnboardingAnswer(BaseModel):
    answer: str = Field(
        description="Réponse à la question, en langage naturel et en français, "
        "reformulée dans tes propres mots (pas de copie mot pour mot des sources)."
    )
    sources_used: list[int] = Field(
        default_factory=list,
        description="Numéros (1, 2, 3...) des sources numérotées ci-dessus réellement "
        "utilisées pour construire la réponse. Liste VIDE si aucune source ne répond à "
        "la question — dans ce cas 'answer' doit être le repli poli standard, rien d'autre.",
    )


def chunk_text(text: str, max_length: int = 800) -> list[str]:
    """Découpe basique par paragraphes avec une limite de longueur."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current_chunk) + len(p) > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = p
        else:
            current_chunk += ("\n\n" + p) if current_chunk else p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def process_manual(file_path: str, db: Session):
    """Lit un PDF, le découpe PAGE PAR PAGE, génère les embeddings et stocke
    le tout. Découper page par page (plutôt que sur le texte concaténé du
    document entier) est ce qui rend le numéro de page de chaque chunk
    exact — condition nécessaire pour des citations qui pointent au bon
    endroit plutôt qu'un `page=0` arbitraire."""
    db.query(ManualChunk).delete()
    db.query(Embedding).filter_by(owner_type="manual_chunk").delete()

    doc = fitz.open(file_path)
    for page_index, page in enumerate(doc, start=1):
        page_text = page.get_text()
        for c in chunk_text(page_text):
            chunk_obj = ManualChunk(content=c, page=page_index)
            db.add(chunk_obj)
            db.flush()  # pour avoir l'ID du chunk

            vec = embed_text(c)
            emb = Embedding(
                owner_type="manual_chunk",
                owner_id=chunk_obj.id,
                section="content",
                vector=vec,
            )
            db.add(emb)

    db.commit()


def _short_excerpt(content: str) -> str:
    content = " ".join(content.split())  # aplati les retours à la ligne internes
    if len(content) <= _EXCERPT_MAX_LEN:
        return content
    return content[:_EXCERPT_MAX_LEN].rsplit(" ", 1)[0] + "…"


def answer_question(question: str, db: Session) -> dict:
    """Retourne {"answer": str, "citations": [{"page": int, "excerpt": str}]}.
    `citations` est vide quand la question ne trouve pas de réponse dans le
    manuel — c'est le signal que le frontend peut utiliser pour distinguer
    une réponse sourcée d'un simple repli poli."""
    vec = embed_text(question)

    stmt = (
        select(ManualChunk.content, ManualChunk.page)
        .join(Embedding, Embedding.owner_id == ManualChunk.id)
        .where(Embedding.owner_type == "manual_chunk")
        .order_by(Embedding.vector.cosine_distance(vec))
        .limit(3)
    )
    results = db.execute(stmt).all()

    if not results:
        return {
            "answer": "Le manuel de l'entreprise n'a pas encore été importé. Veuillez contacter les RH.",
            "citations": [],
        }

    sources = [{"n": i, "page": page, "content": content} for i, (content, page) in enumerate(results, start=1)]
    context = "\n\n".join(f"[SOURCE {s['n']} — page {s['page']}]\n{s['content']}" for s in sources)

    system = (
        "Tu es l'assistant RH de l'entreprise (Agent A8). Ton rôle est de répondre "
        "aux questions des nouveaux employés pendant leur intégration (onboarding).\n"
        "Réponds UNIQUEMENT à partir des sources numérotées ci-dessous, jamais de tes "
        "connaissances générales. Indique dans sources_used les numéros des sources "
        "réellement utilisées. Si aucune source ne répond à la question, laisse "
        "sources_used vide et réponds exactement : 'Je n'ai pas cette information dans "
        "le manuel, merci de contacter votre responsable RH.'\n\n"
        f"{context}"
    )

    result = complete_structured(
        "chat", system, question, OnboardingAnswer,
        temperature=0.0, trace_name="a8_onboarding_rag",
    )

    citations = [
        {"page": s["page"], "excerpt": _short_excerpt(s["content"])}
        for s in sources
        if s["n"] in result.sources_used
    ]

    return {"answer": result.answer, "citations": citations}