import fitz  # PyMuPDF


def extract_pages(pdf_bytes: bytes):
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for index, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append((index + 1, text))
    return pages


def split_into_chunks(pages, chunk_size=800, overlap=150):
    chunks = []
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append({"text": piece, "page": page_number})
            start += chunk_size - overlap
    return chunks


def process_pdf(pdf_bytes: bytes):
    pages = extract_pages(pdf_bytes)
    if not pages:
        raise ValueError("No readable text found. This may be a scanned PDF.")
    return split_into_chunks(pages)