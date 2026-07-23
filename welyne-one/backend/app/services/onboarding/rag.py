import fitz  # PyMuPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.manual_chunk import ManualChunk
from app.models.embedding import Embedding
from app.services.scoring.embeddings import embed_text
from app.services.llm_gateway import complete


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
    """Lit un PDF, le découpe, génère les embeddings et stocke le tout."""
    # Nettoyage de l'ancien manuel
    db.query(ManualChunk).delete()
    db.query(Embedding).filter_by(owner_type="manual_chunk").delete()

    # Lecture PDF
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n\n"

    # Découpage
    chunks = chunk_text(text)

    # Insertion en base avec embeddings
    for c in chunks:
        chunk_obj = ManualChunk(content=c, page=0)
        db.add(chunk_obj)
        db.flush()  # Pour avoir l'ID du chunk

        vec = embed_text(c)
        emb = Embedding(
            owner_type="manual_chunk",
            owner_id=chunk_obj.id,
            section="content",
            vector=vec
        )
        db.add(emb)

    db.commit()


def answer_question(question: str, db: Session) -> str:
    """Répond à une question en utilisant le contexte RAG."""
    # 1. Vectoriser la question
    vec = embed_text(question)

    # 2. Chercher les 3 chunks les plus proches (distance cosinus)
    stmt = (
        select(ManualChunk.content)
        .join(Embedding, Embedding.owner_id == ManualChunk.id)
        .where(Embedding.owner_type == "manual_chunk")
        .order_by(Embedding.vector.cosine_distance(vec))
        .limit(3)
    )
    results = db.execute(stmt).all()

    if not results:
        return "Le manuel de l'entreprise n'a pas encore été importé. Veuillez contacter les RH."

    context = "\n\n---\n\n".join([r[0] for r in results])

    # 3. Construire le prompt
    system = (
        "Tu es l'assistant RH de l'entreprise (Agent A8). Ton rôle est de répondre "
        "aux questions des nouveaux employés pendant leur intégration (onboarding).\n"
        "RÉPONDS UNIQUEMENT EN UTILISANT LE CONTEXTE CI-DESSOUS. Ne cite pas le contexte explicitement, "
        "utilise les informations naturellement. Si la réponse ne se trouve pas dans le contexte, "
        "réponds poliment : 'Je n'ai pas cette information dans le manuel, merci de contacter votre responsable RH.'\n\n"
        "CONTEXTE DU MANUEL D'ENTREPRISE :\n"
        f"{context}"
    )

    # 4. Appeler le LLM (tâche 'judge' pour forcer le gros modèle si configuré ainsi)
    ans = complete("judge", system=system, user=question, temperature=0.0)
    return ans
