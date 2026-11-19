import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pdf_utils import process_pdf
import rag
import llm

app = FastAPI(title="PDFMind AI")

MAX_MB = 20
MAX_DOCS = 5
FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


class ChatRequest(BaseModel):
    session_id: str
    question: str
    doc_ids: Optional[List[str]] = None


class ToolRequest(BaseModel):
    session_id: str
    doc_ids: Optional[List[str]] = None


def get_text(session_id, doc_ids=None, limit=8000):
    """Collect the document text in order, sampled evenly if too long."""
    col = rag._collection(session_id)
    if col.count() == 0:
        return ""
    where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
    data = col.get(where=where, include=["documents"])
    pairs = list(zip(data["ids"], data["documents"]))

    def key(p):
        doc, _, idx = p[0].rpartition("_")
        return (doc, int(idx))

    pairs.sort(key=key)
    texts = [t for _, t in pairs]
    total = sum(len(t) for t in texts)
    if total > limit:
        texts = texts[:: total // limit + 1]
    return "\n".join(texts)


@app.post("/api/upload")
def upload(session_id: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed.")
    if len(rag.list_documents(session_id)) >= MAX_DOCS:
        raise HTTPException(400, f"You can upload up to {MAX_DOCS} PDFs.")

    data = file.file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large. Maximum is {MAX_MB} MB.")

    try:
        chunks = process_pdf(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(400, "Could not read this PDF file.")

    doc_id = uuid.uuid4().hex[:8]
    try:
        rag.add_document(session_id, doc_id, file.filename, chunks)
    except Exception as e:
        raise HTTPException(500, f"AI processing failed: {e}")
    return {"doc_id": doc_id, "filename": file.filename, "chunks": len(chunks)}


@app.get("/api/documents")
def documents(session_id: str):
    return rag.list_documents(session_id)


@app.delete("/api/documents/{doc_id}")
def remove_document(doc_id: str, session_id: str):
    rag.delete_document(session_id, doc_id)
    return {"ok": True}


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(400, "Please type a question.")
    try:
        hits = rag.search(req.session_id, req.question, req.doc_ids)
        answer = llm.answer_question(req.question, hits)
    except Exception as e:
        raise HTTPException(500, f"Could not get an answer: {e}")
    sources = []
    for h in hits:
        s = {"filename": h["filename"], "page": h["page"]}
        if s not in sources:
            sources.append(s)
    return {"answer": answer, "sources": sources}


def _need_text(req):
    text = get_text(req.session_id, req.doc_ids)
    if not text:
        raise HTTPException(400, "Please upload a PDF first.")
    return text


@app.post("/api/summary")
def summary(req: ToolRequest):
    text = _need_text(req)
    try:
        return {"summary": llm.make_summary(text)}
    except Exception as e:
        raise HTTPException(500, f"Could not create summary: {e}")


@app.post("/api/quiz")
def quiz(req: ToolRequest):
    text = _need_text(req)
    try:
        return {"questions": llm.make_quiz(text)}
    except Exception:
        raise HTTPException(500, "Could not create the quiz. Please try again.")


@app.post("/api/flashcards")
def flashcards(req: ToolRequest):
    text = _need_text(req)
    try:
        return {"cards": llm.make_flashcards(text)}
    except Exception:
        raise HTTPException(500, "Could not create flashcards. Please try again.")


# Must stay LAST: serves the website
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")