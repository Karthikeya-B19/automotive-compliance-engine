from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_community.vectorstores import Chroma
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from sentence_transformers import SentenceTransformer

from src.ingestion.ingest import LocalSentenceTransformerEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"
COLLECTION_NAME = "misra_rules"


class CodeReviewRAGOrchestrator:
    """Evidence-grounded retrieval and review orchestration for secure code checks."""

    def __init__(
        self,
        persist_dir: str | Path = VECTOR_STORE_DIR,
        collection_name: str = COLLECTION_NAME,
        model_name: str = "all-MiniLM-L6-v2",
        llm_model: str = "llama3.1",
        retriever_k: int = 5,
    ):
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.model_name = model_name
        self.llm_model = llm_model
        self.retriever_k = retriever_k

        self.embedding_model = LocalSentenceTransformerEmbeddings(model_name=model_name)
        self.vector_store = Chroma(
            persist_directory=str(self.persist_dir / self.collection_name),
            embedding_function=self.embedding_model,
            collection_name=self.collection_name,
        )

        self.retriever = self.vector_store.as_retriever(
            search_kwargs={"k": self.retriever_k}
        )

        self.llm = ChatOllama(
            model=self.llm_model,
            temperature=0,
            base_url="http://localhost:11434",
        )

    def _build_retrieval_prompt(self, code_snippet: str, compiler_warnings: List[str]) -> str:
        warnings_text = "\n".join(f"- {warning}" for warning in compiler_warnings)
        return (
            "Review the following source code and compiler warnings. "
            "Use only the retrieved coding standard evidence to assess whether the code violates secure coding or MISRA-style rules.\n\n"
            "Source Code:\n"
            f"{code_snippet}\n\n"
            "Compiler Warnings:\n"
            f"{warnings_text}\n\n"
            "If the retrieved context does not contain enough evidence, state that the conclusion is limited by the available text and do not invent rules."
        )

    def retrieve_relevant_context(self, code_snippet: str, compiler_warnings: List[str]) -> List[Dict[str, Any]]:
        """Retrieve the most relevant standard excerpts using the local embedding model."""
        query = self._build_retrieval_prompt(code_snippet, compiler_warnings)
        docs = self.retriever.invoke(query)

        results: List[Dict[str, Any]] = []
        for doc in docs:
            results.append(
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source_pdf", "unknown"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "score": getattr(doc, "score", None),
                }
            )
        return results

    def _build_review_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a secure code reviewer for embedded automotive software. "
                    "Your answer must be grounded only in the retrieved coding standard context. "
                    "Do not use external knowledge or make up rules. "
                    "If the retrieved evidence is insufficient, say so clearly. "
                    "Always provide source evidence, citations, and a confidence score."
                ),
                (
                    "user",
                    "Review the following code and compiler warnings against the retrieved standards.\n\n"
                    "RETRIEVED_CONTEXT:\n{context}\n\n"
                    "SOURCE_CODE:\n{code_snippet}\n\n"
                    "COMPILER_WARNINGS:\n{compiler_warnings}\n\n"
                    "Return valid JSON with exactly these fields: "
                    "review_summary, candidate_root_causes, suggested_remediation, rule_reference, source_evidence, confidence. "
                    "The rule_reference field must include a rule number or standard citation when present in retrieved context. "
                    "The source_evidence field must quote or summarize the exact retrieved standard text that supports the finding. "
                    "Do not answer from memory. Only use the retrieved context."
                ),
            ]
        )
        return prompt

    def review_code(self, code_snippet: str, compiler_warnings: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute retrieval + review and return a structured JSON review payload."""
        warnings = compiler_warnings or []
        context_docs = self.retrieve_relevant_context(code_snippet, warnings)

        if not context_docs:
            return {
                "review_summary": "No relevant coding-standard context was retrieved for this code snippet.",
                "candidate_root_causes": [],
                "suggested_remediation": "Add or index relevant MISRA or coding standard PDFs to the local standards directory before review.",
                "rule_reference": "Not available",
                "source_evidence": [],
                "confidence": "low",
            }

        prompt = self._build_review_prompt()
        context_block = "\n\n---\n\n".join(
            f"Source: {doc['source']}\nChunk: {doc['chunk_index']}\nContent: {doc['content']}"
            for doc in context_docs
        )

        chain = prompt | self.llm
        response = chain.invoke(
            {
                "context": context_block,
                "code_snippet": code_snippet,
                "compiler_warnings": "\n".join(warnings) if warnings else "No compiler warnings provided.",
            }
        )

        raw_text = getattr(response, "content", str(response))
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            parsed = {
                "review_summary": raw_text,
                "candidate_root_causes": [],
                "suggested_remediation": "Review the raw model response for evidence-based remediation.",
                "rule_reference": "Not extracted",
                "source_evidence": [context_block],
                "confidence": "medium",
            }

        result = {
            "review_summary": parsed.get("review_summary", "No summary available."),
            "candidate_root_causes": parsed.get("candidate_root_causes", []),
            "suggested_remediation": parsed.get("suggested_remediation", "No remediation suggested."),
            "rule_reference": parsed.get("rule_reference", "Not available"),
            "source_evidence": parsed.get("source_evidence", [context_block]),
            "confidence": parsed.get("confidence", "medium"),
            "retrieved_context": context_docs,
        }

        return result


def review_code(code_snippet: str, compiler_warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function for direct use from the API or UI."""
    orchestrator = CodeReviewRAGOrchestrator()
    return orchestrator.review_code(code_snippet=code_snippet, compiler_warnings=compiler_warnings)


if __name__ == "__main__":
    sample_code = """
int main(void) {
    int *ptr = NULL;
    *ptr = 5;
    return 0;
}
"""
    sample_warnings = [
        "Dereference of NULL pointer",
        "Possible invalid memory access"
    ]
    print(json.dumps(review_code(sample_code, sample_warnings), indent=2))
