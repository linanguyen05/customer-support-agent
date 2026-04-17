# config.py
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Bedrock
# REGION = "us-east-1"
# EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
# LLM_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# CHUNK_SIZE = 1500          # Increase chunk size to capture more context, especially for tables, dont work, though
# CHUNK_OVERLAP = 300        # Increase overlap to ensure better context continuity across chunks
# TOP_K = 3
# SIMILARITY_THRESHOLD = os.getenv("SIMILARITY_THRESHOLD")
# if SIMILARITY_THRESHOLD is not None:
#     try:
#         SIMILARITY_THRESHOLD = float(SIMILARITY_THRESHOLD)
#     except ValueError:
#         SIMILARITY_THRESHOLD = None
# LOG_RETRIEVAL_SCORES = os.getenv("LOG_RETRIEVAL_SCORES", "true").lower() in ("1", "true", "yes")

# # Paths
# DEFAULT_PDF_PATH = os.path.join("data", "Company-10k-18pages.pdf")
# PDF_PATH = os.getenv("PDF_PATH", DEFAULT_PDF_PATH)
# FAISS_INDEX_FOLDER = "data"
# FAISS_INDEX_NAME = "faiss"
# FAISS_INDEX_PATH = os.path.join(FAISS_INDEX_FOLDER, f"{FAISS_INDEX_NAME}.faiss")
# DOCSTORE_PATH = os.path.join(FAISS_INDEX_FOLDER, f"{FAISS_INDEX_NAME}.pkl")

# # Load system prompt from file
# with open("prompt.txt", "r", encoding="utf-8") as f:
#     SYSTEM_PROMPT = f.read()

#Local

import os
from dotenv import load_dotenv

load_dotenv()

# Bedrock
REGION = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
LLM_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Chunking
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300
TOP_K = 3
SIMILARITY_THRESHOLD = os.getenv("SIMILARITY_THRESHOLD")
if SIMILARITY_THRESHOLD:
    SIMILARITY_THRESHOLD = float(SIMILARITY_THRESHOLD)
LOG_RETRIEVAL_SCORES = os.getenv("LOG_RETRIEVAL_SCORES", "true").lower() in ("1", "true", "yes")

# S3 & local storage
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_PDF_KEY = os.getenv("S3_PDF_KEY", "data/Company-10k-18pages.pdf")
S3_INDEX_PREFIX = os.getenv("S3_INDEX_PREFIX", "data/")
LOCAL_TMP = os.getenv("LOCAL_TMP", "/tmp/faiss_data")

# Paths trong local tmp
PDF_PATH = os.path.join(LOCAL_TMP, "Company-10k-18pages.pdf")
FAISS_INDEX_PATH = os.path.join(LOCAL_TMP, "faiss.faiss")
DOCSTORE_PATH = os.path.join(LOCAL_TMP, "faiss.pkl")

# System prompt
with open("prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

