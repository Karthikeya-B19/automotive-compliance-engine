from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from chromadb.config import Settings
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
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 200


class LocalSentenceTransformerEmbeddings(Embeddings):
    """Embedding wrapper for locally stored sentence-transformer model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Never let the review path resolve or download a model over the network.
        # Administrators must pre-stage the approved embedding model locally.
        self.model = SentenceTransformer(model_name, local_files_only=True)

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
    if not path.is_file():
        raise ValueError(f"PDF path is not a regular file: {path}")
    if path.stat().st_size > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"PDF exceeds the maximum allowed size of {MAX_PDF_SIZE_BYTES} bytes: {path}"
        )

    pages: List[str] = []
    with fitz.open(path) as document:
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF exceeds the maximum allowed page count of {MAX_PDF_PAGES}: {path}"
            )
        for page in document:
            text = page.get_text("text")
            if text:
                pages.append(text)
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


def _document_id(source_pdf: str, chunk_index: int) -> str:
    """Return a stable ID for a source file and its chunk position."""
    identity = f"{source_pdf}:{chunk_index}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()


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

    if not all_documents:
        raise ValueError("No text chunks were extracted from the standards PDFs.")

    embeddings = LocalSentenceTransformerEmbeddings(model_name=model_name)
    vector_store = Chroma(
        persist_directory=str(Path(persist_dir) / collection_name),
        embedding_function=embeddings,
        collection_name=collection_name,
        client_settings=Settings(anonymized_telemetry=False),
    )

    existing_ids = vector_store.get()["ids"]
    if existing_ids:
        vector_store.delete(ids=existing_ids)

    document_ids = [
        _document_id(str(document.metadata["source_pdf"]), int(document.metadata["chunk_index"]))
        for document in all_documents
    ]
    vector_store.add_documents(documents=all_documents, ids=document_ids)
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
        client_settings=Settings(anonymized_telemetry=False),
    )


def main() -> None:
    """CLI entry point for the ingestion process."""
    print(f"Looking for PDFs in: {STANDARDS_DIR}")
    vector_store = ingest_standard_documents()
    print(f"Indexed {vector_store._collection.count()} chunks into local Chroma store.")


if __name__ == "__main__":
    main()
