import chromadb
from chromadb.utils import embedding_functions
import logging
from config import CHROMA_DB_PATH, EMBEDDING_MODEL_NAME, SIMILARITY_THRESHOLD, TOP_K_RESULTS
from pdf_loader import split_into_chunks

logger = logging.getLogger(__name__)

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME
)

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(
    name="pdf_notes",
    embedding_function=sentence_transformer_ef
)

def index_pdfs(documents):
    all_chunks = []
    metadatas = []
    ids = []

    for filename, text in documents:
        chunks = split_into_chunks(text)
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadatas.append({"source": filename})
            ids.append(f"{filename}_{j}")

    if all_chunks:
        collection.add(
            documents=all_chunks,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Indexed {len(all_chunks)} chunks.")
    else:
        print("⚠️ No chunks to index.")

def get_relevant_chunks(query):
    results = collection.query(query_texts=[query], n_results=TOP_K_RESULTS)
    logger.info(f"Query distances: {results['distances'][0]}")
    relevant = []
    for i, dist in enumerate(results['distances'][0]):
        if dist < SIMILARITY_THRESHOLD:
            relevant.append(results['documents'][0][i])
    logger.info(f"Relevant chunks after threshold: {len(relevant)}")
    return relevant

def get_relevant_chunks_with_sources(query):
    results = collection.query(query_texts=[query], n_results=TOP_K_RESULTS)
    logger.info(f"Query distances: {results['distances'][0]}")
    relevant_chunks = []
    sources = []
    for i, dist in enumerate(results['distances'][0]):
        if dist < SIMILARITY_THRESHOLD:
            relevant_chunks.append(results['documents'][0][i])
            sources.append(results['metadatas'][0][i]['source'])
    logger.info(f"Relevant chunks after threshold: {len(relevant_chunks)}")
    return relevant_chunks, sources