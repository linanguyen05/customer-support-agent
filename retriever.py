# retriever.py 
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
import os
from config import (
    PDF_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    FAISS_INDEX_FOLDER,
    FAISS_INDEX_NAME,
    FAISS_INDEX_PATH,
    DOCSTORE_PATH,
    TOP_K,
    SIMILARITY_THRESHOLD,
    LOG_RETRIEVAL_SCORES,
    EMBEDDING_MODEL_ID,
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
        self._load_or_build()

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
            print("Loading existing FAISS index...")
            self.vectorstore = FAISS.load_local(
                folder_path=FAISS_INDEX_FOLDER,
                index_name=FAISS_INDEX_NAME,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print(f"Building FAISS index from PDF at {PDF_PATH}...")
            if not os.path.exists(PDF_PATH):
                print(f"[WARN] PDF not found at {PDF_PATH}. Retrieval will be disabled until the PDF/index is available.")
                return
            chunks = self._load_pdf()
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            os.makedirs(FAISS_INDEX_FOLDER, exist_ok=True)
            self.vectorstore.save_local(FAISS_INDEX_FOLDER, FAISS_INDEX_NAME)
            print("Saved FAISS index.")

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
    
