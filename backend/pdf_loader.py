import os
from pypdf import PdfReader
from config import PDF_FOLDER, CHUNK_SIZE

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def split_into_chunks(text, chunk_size=CHUNK_SIZE):
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n\n"
    if current:
        chunks.append(current.strip())
    return chunks

def load_all_pdfs():
    if not os.path.exists(PDF_FOLDER):
        print(f"Warning: {PDF_FOLDER} folder not found.")
        return []
    
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    documents = []
    for filename in pdf_files:
        path = os.path.join(PDF_FOLDER, filename)
        print(f"  Reading {filename}...")
        text = extract_text_from_pdf(path)
        if text.strip():
            documents.append((filename, text))
        else:
            print(f"    Warning: No text found in {filename}")
    return documents