# PDFMind AI

An Intelligent Multi-Document Understanding, Question Answering and Personalized Learning Platform.

## Problem
Students and professionals spend hours reading long PDFs such as textbooks, research papers and manuals. Normal PDF readers only support keyword search, with no understanding or learning support.

## Solution
PDFMind AI is a website where users upload PDFs and ask questions in natural language. It answers with page citations and also creates summaries, quizzes and flashcards.

## Features
- No login: open the website and start immediately
- Upload up to 5 PDFs (max 20 MB each)
- Chat with one or several PDFs
- Answers with file name and page citations (RAG)
- Automatic summary and key points
- AI quiz with score history
- Flashcards (click to flip)

## Tech Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI
- AI: Google Gemini API (embeddings and answers)
- Vector database: ChromaDB
- PDF processing: PyMuPDF

## Working Flow
Upload PDF -> Extract text -> Split into chunks -> Create embeddings -> Store in ChromaDB -> Ask question -> Retrieve relevant chunks -> Gemini answers with page citations

## How to Run
1. Install Python 3.10 or higher
2. Open a terminal in the `backend` folder
3. Create and activate a virtual environment: