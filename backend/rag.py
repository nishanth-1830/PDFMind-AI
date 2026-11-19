import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
import chromadb

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
EMBED_MODEL = "gemini-embedding-001"

chroma = chromadb.PersistentClient(path="chroma_db")


def _collection(session_id: str):
    """One collection per visitor, so PDFs never mix between users."""
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)[:50]
    return chroma.get_or_create_collection(
        name=f"s_{safe_id}",
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT"):
    """Convert a list of texts into embeddings (in batches of 50)."""
    vectors = []
    for i in range(0, len(texts), 50):
        batch = texts[i:i + 50]
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        vectors.extend([e.values for e in result.embeddings])
    return vectors


def add_document(session_id, doc_id, filename, chunks):
    """Save all chunks of one PDF into the vector database."""
    col = _collection(session_id)
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts, "RETRIEVAL_DOCUMENT")

    col.add(
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        documents=texts,
        embeddings=vectors,
        metadatas=[
            {"doc_id": doc_id, "filename": filename, "page": c["page"]}
            for c in chunks
        ],
    )


def search(session_id, question, doc_ids=None, top_k=5):
    """Find the chunks most related to the question."""
    col = _collection(session_id)
    if col.count() == 0:
        return []

    q_vector = embed_texts([question], "RETRIEVAL_QUERY")[0]

    where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
    result = col.query(
        query_embeddings=[q_vector],
        n_results=top_k,
        where=where,
    )

    hits = []
    for text, meta in zip(result["documents"][0], result["metadatas"][0]):
        hits.append({
            "text": text,
            "page": meta["page"],
            "filename": meta["filename"],
            "doc_id": meta["doc_id"],
        })
    return hits


def list_documents(session_id):
    """Return the unique PDFs uploaded in this session."""
    col = _collection(session_id)
    if col.count() == 0:
        return []
    metas = col.get(include=["metadatas"])["metadatas"]
    docs = {}
    for m in metas:
        docs[m["doc_id"]] = m["filename"]
    return [{"doc_id": d, "filename": f} for d, f in docs.items()]


def delete_document(session_id, doc_id):
    """Remove one PDF from the database."""
    _collection(session_id).delete(where={"doc_id": doc_id})