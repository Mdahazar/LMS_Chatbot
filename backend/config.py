import os

# ========== PATHS ==========
PDF_FOLDER = "notes"               # folder containing PDFs
CHROMA_DB_PATH = "./chroma_db"     # where vector DB is stored

# ========== TEXT SPLITTING ==========
CHUNK_SIZE = 500                   # characters per chunk

# ========== RETRIEVAL ==========
SIMILARITY_THRESHOLD = 0.5         # adjust based on testing
TOP_K_RESULTS = 3                   # number of chunks to retrieve

# ========== LLM ==========
LLM_MODEL = "phi3:mini"             # or "mistral", "llama3", etc.

# ========== EMBEDDING MODEL ==========
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"