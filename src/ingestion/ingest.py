from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
STANDARDS_DIR = DATA_DIR / "standards"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
CHROMA_COLLECTION_NAME = "misra_rules"


class LocalSentenceTransformerEmbeddings(Embeddings):
    """Embedding wrapper for locally stored sentence-transformer model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        return embedding[0].tolist()


def _ensure_directories() -> None:
    STANDARDS_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Read a PDF and extract all text content using PyMuPDF."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    document = fitz.open(path)
    pages: List[str] = []
    for page in document:
        text = page.get_text("text")
        if text:
            pages.append(text)
    document.close()
    return "\n\n".join(pages)


def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 200) -> List[str]:
    """Split extracted PDF text into overlapping chunks for indexing."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def build_documents_from_pdf(pdf_path: str | Path) -> List[Document]:
    """Build LangChain documents from extracted PDF text."""
    extracted = extract_pdf_text(pdf_path)
    chunks = chunk_text(extracted)

    docs: List[Document] = []
    for idx, chunk in enumerate(chunks):
        metadata = {
            "source_pdf": str(Path(pdf_path).name),
            "chunk_index": idx,
            "document_type": "automotive_coding_standard",
        }
        docs.append(Document(page_content=chunk, metadata=metadata))
    return docs


def _list_pdf_files(directory: str | Path) -> List[Path]:
    path = Path(directory)
    if not path.exists():
        return []
    return sorted(path.glob("*.pdf"))


def ingest_standard_documents(
    standards_dir: str | Path = STANDARDS_DIR,
    persist_dir: str | Path = VECTOR_STORE_DIR,
    collection_name: str = CHROMA_COLLECTION_NAME,
    model_name: str = "all-MiniLM-L6-v2",
) -> Chroma:
    """Parse standard PDFs, chunk the text, and store embeddings in ChromaDB."""
    _ensure_directories()

    pdf_files = _list_pdf_files(standards_dir)
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in directory: {standards_dir}")

    all_documents: List[Document] = []
    for pdf_file in pdf_files:
        all_documents.extend(build_documents_from_pdf(pdf_file))

    embeddings = LocalSentenceTransformerEmbeddings(model_name=model_name)

    vector_store = Chroma.from_documents(
        documents=all_documents,
        embedding=embeddings,
        persist_directory=str(Path(persist_dir) / collection_name),
        collection_name=collection_name,
    )
    vector_store.persist()
    return vector_store


def load_vector_store(
    persist_dir: str | Path = VECTOR_STORE_DIR,
    collection_name: str = CHROMA_COLLECTION_NAME,
    model_name: str = "all-MiniLM-L6-v2",
) -> Chroma:
    """Load an existing local ChromaDB collection."""
    embeddings = LocalSentenceTransformerEmbeddings(model_name=model_name)
    return Chroma(
        persist_directory=str(Path(persist_dir) / collection_name),
        embedding_function=embeddings,
        collection_name=collection_name,
    )


def main() -> None:
    """CLI entry point for the ingestion process."""
    print(f"Looking for PDFs in: {STANDARDS_DIR}")
    vector_store = ingest_standard_documents()
    print(f"Indexed {vector_store._collection.count()} chunks into local Chroma store.")


if __name__ == "__main__":
    main()
