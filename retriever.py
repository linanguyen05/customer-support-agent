# # retriever.py 
# import pdfplumber
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.schema import Document
# from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import BedrockEmbeddings
# import os
# from config import (
#     PDF_PATH,
#     CHUNK_SIZE,
#     CHUNK_OVERLAP,
#     FAISS_INDEX_FOLDER,
#     FAISS_INDEX_NAME,
#     FAISS_INDEX_PATH,
#     DOCSTORE_PATH,
#     TOP_K,
#     SIMILARITY_THRESHOLD,
#     LOG_RETRIEVAL_SCORES,
#     EMBEDDING_MODEL_ID,
# )
# from bedrock_client import BedrockClient

# class PDFRetriever:
#     def __init__(self):
#         self.bedrock_client = BedrockClient()
#         self.embeddings = BedrockEmbeddings(
#             client=self.bedrock_client.bedrock_runtime,
#             model_id=EMBEDDING_MODEL_ID
#         )
#         self.vectorstore = None
#         self._warned_no_index = False
#         self._load_or_build()

#     def _load_pdf(self):
#         docs = []
#         with pdfplumber.open(PDF_PATH) as pdf:
#             for page_num, page in enumerate(pdf.pages, start=1):
#                 text = page.extract_text() or ""
#                 if text.strip():
#                     docs.append(Document(page_content=text, metadata={"page": page_num}))
#         splitter = RecursiveCharacterTextSplitter(
#             chunk_size=CHUNK_SIZE,
#             chunk_overlap=CHUNK_OVERLAP,
#             separators=["\n\n", "\n", " ", ""]
#         )
#         chunks = splitter.split_documents(docs)
#         print(f"Loaded {len(chunks)} chunks from PDF")
#         return chunks

#     def _load_or_build(self):
#         if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCSTORE_PATH):
#             print("Loading existing FAISS index...")
#             self.vectorstore = FAISS.load_local(
#                 folder_path=FAISS_INDEX_FOLDER,
#                 index_name=FAISS_INDEX_NAME,
#                 embeddings=self.embeddings,
#                 allow_dangerous_deserialization=True
#             )
#         else:
#             print(f"Building FAISS index from PDF at {PDF_PATH}...")
#             if not os.path.exists(PDF_PATH):
#                 print(f"[WARN] PDF not found at {PDF_PATH}. Retrieval will be disabled until the PDF/index is available.")
#                 return
#             chunks = self._load_pdf()
#             self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
#             os.makedirs(FAISS_INDEX_FOLDER, exist_ok=True)
#             self.vectorstore.save_local(FAISS_INDEX_FOLDER, FAISS_INDEX_NAME)
#             print("Saved FAISS index.")

#     def get_relevant_documents(self, query: str):
#         if not self.vectorstore:
#             if not self._warned_no_index:
#                 print("[WARN] No FAISS index loaded. Returning empty context.")
#                 self._warned_no_index = True
#             return []
#         docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=TOP_K)
#         if LOG_RETRIEVAL_SCORES:
#             for doc, score in docs_with_scores:
#                 print(f"[DEBUG] score={score:.4f} page={doc.metadata.get('page')}")
#         if SIMILARITY_THRESHOLD is not None:
#             filtered = [(doc, score) for doc, score in docs_with_scores if score < SIMILARITY_THRESHOLD]
#             if not filtered and LOG_RETRIEVAL_SCORES:
#                 print(f"[WARN] All chunks filtered by SIMILARITY_THRESHOLD={SIMILARITY_THRESHOLD}")
#             return [doc for doc, _ in filtered]
#         return [doc for doc, _ in docs_with_scores]
    
import os
import boto3
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
from config import (
    PDF_PATH, CHUNK_SIZE, CHUNK_OVERLAP,
    LOCAL_TMP, FAISS_INDEX_PATH, DOCSTORE_PATH,
    TOP_K, SIMILARITY_THRESHOLD, LOG_RETRIEVAL_SCORES,
    EMBEDDING_MODEL_ID, S3_BUCKET, S3_PDF_KEY, S3_INDEX_PREFIX
)
from bedrock_client import BedrockClient

class PDFRetriever:
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.embeddings = BedrockEmbeddings(
            client=self.bedrock_client.bedrock_runtime,
            model_id=EMBEDDING_MODEL_ID
        )
        self.vectorstore = None
        self._warned_no_index = False
        self._ensure_local_files()
        self._load_or_build()

    def _ensure_local_files(self):
        """Tải PDF và FAISS index từ S3 nếu chưa có trong LOCAL_TMP"""
        os.makedirs(LOCAL_TMP, exist_ok=True)
        s3 = boto3.client("s3")
        # Tải PDF
        if not os.path.exists(PDF_PATH):
            print(f"Downloading PDF from s3://{S3_BUCKET}/{S3_PDF_KEY}")
            s3.download_file(S3_BUCKET, S3_PDF_KEY, PDF_PATH)
        # Tải FAISS index
        if not os.path.exists(FAISS_INDEX_PATH):
            s3_key_index = f"{S3_INDEX_PREFIX}faiss.faiss"
            print(f"Downloading FAISS index from s3://{S3_BUCKET}/{s3_key_index}")
            s3.download_file(S3_BUCKET, s3_key_index, FAISS_INDEX_PATH)
        if not os.path.exists(DOCSTORE_PATH):
            s3_key_docstore = f"{S3_INDEX_PREFIX}faiss.pkl"
            print(f"Downloading docstore from s3://{S3_BUCKET}/{s3_key_docstore}")
            s3.download_file(S3_BUCKET, s3_key_docstore, DOCSTORE_PATH)

    def _load_pdf(self):
        docs = []
        with pdfplumber.open(PDF_PATH) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append(Document(page_content=text, metadata={"page": page_num}))
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)
        print(f"Loaded {len(chunks)} chunks from PDF")
        return chunks

    def _load_or_build(self):
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCSTORE_PATH):
            print("Loading existing FAISS index from local tmp...")
            self.vectorstore = FAISS.load_local(
                folder_path=LOCAL_TMP,
                index_name="faiss",
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("Building FAISS index from PDF...")
            chunks = self._load_pdf()
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            self.vectorstore.save_local(LOCAL_TMP, "faiss")
            print("Saved FAISS index locally. Please upload to S3 for future use.")

    def get_relevant_documents(self, query: str):
        if not self.vectorstore:
            if not self._warned_no_index:
                print("[WARN] No FAISS index loaded. Returning empty context.")
                self._warned_no_index = True
            return []
        docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=TOP_K)
        if LOG_RETRIEVAL_SCORES:
            for doc, score in docs_with_scores:
                print(f"[DEBUG] score={score:.4f} page={doc.metadata.get('page')}")
        if SIMILARITY_THRESHOLD is not None:
            filtered = [(doc, score) for doc, score in docs_with_scores if score < SIMILARITY_THRESHOLD]
            if not filtered and LOG_RETRIEVAL_SCORES:
                print(f"[WARN] All chunks filtered by SIMILARITY_THRESHOLD={SIMILARITY_THRESHOLD}")
            return [doc for doc, _ in filtered]
        return [doc for doc, _ in docs_with_scores]