import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
CHAT_MODEL = "gemini-3.1-flash-lite"


def _ask(prompt: str) -> str:
    """Send a prompt to Gemini. Fast mode, retry once on failure."""
    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    max_output_tokens=800,
                ),
            )
            text = (response.text or "").strip()
            if text:
                return text
            last_error = Exception("Gemini returned an empty reply.")
        except Exception as e:
            last_error = e
        time.sleep(1)
    raise last_error

def answer_question(question: str, hits: list) -> str:
    """Use the context below to answer clearly and briefly.
- Give the key facts in 3 to 5 lines, or short bullet points for specifications.
- Mention the page number like (page 2).
- Only say "I could not find this in the document" if the context has nothing related."""
    if not hits:
        return "I could not find anything in your documents. Please upload a PDF first."

    context = ""
    for h in hits:
        context += f"[{h['filename']}, page {h['page']}]\n{h['text']}\n\n"

    prompt = f"""You are an expert assistant that explains PDF documents.
    Use the context below to give a COMPLETE and DETAILED answer.
   - Include every relevant fact, number and detail from the context.
   - Write at least 5 to 8 lines, or a bullet list when there are specifications.
   - Mention the page number in brackets, like (page 2), after facts.
   - Never reply with only one short sentence if more details exist.
   - Only say "I could not find this in the document" if the context has nothing related.

   CONTEXT:
   {context}

   QUESTION: {question}

    DETAILED ANSWER:"""
    return _ask(prompt)


def make_summary(text: str) -> str:
    """Create a short summary with key points."""
    prompt = f"""Summarize the document text below.
Give a short summary of 4 to 5 lines, then 5 key points as bullet points.

TEXT:
{text[:8000]}"""
    return _ask(prompt)


def _clean_json(raw: str):
    """Remove code fences and convert the reply to Python data."""
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def make_quiz(text: str, count: int = 4):
    """Create multiple choice questions as a list."""
    prompt = f"""Create {count} multiple choice questions from the text below.
Return ONLY a JSON list, with no extra words. Use this exact format:
[
  {{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "..."}}
]
"answer" is the index (0 to 3) of the correct option.

TEXT:
{text[:8000]}"""
    return _clean_json(_ask(prompt))


def make_flashcards(text: str, count: int = 6):
    """Create question and answer flashcards."""
    prompt = f"""Create {count} flashcards from the text below.
Return ONLY a JSON list, with no extra words. Use this exact format:
[
  {{"front": "question or term", "back": "short answer or meaning"}}
]

TEXT:
{text[:80000]}"""
    return _clean_json(_ask(prompt))