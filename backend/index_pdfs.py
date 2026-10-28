from pdf_loader import load_all_pdfs
from vector_store import index_pdfs

if __name__ == "__main__":
    print("Loading PDFs...")
    docs = load_all_pdfs()
    if docs:
        print(f"Found {len(docs)} PDFs. Indexing...")
        index_pdfs(docs)
        print("✅ Indexing complete.")
    else:
        print("No PDFs found to index.")