# Model, Retrieval and Runtime Configuration

Artifact: `CB.AI.U4AID23109_ModelConfig_v1.3`

Student: Karthikeya Bellapukonda  
Register number: CB.AI.U4AID23109  
University: Amrita Vishwa Vidyapeetham  
Case study: CS4 — Automotive Secure Code Debugging and Review Assistant

## Runtime components

| Component | Provider / version choice | Configuration | Purpose |
|---|---|---|---|
| Local LLM | Ollama, default model `llama3.1` | `temperature=0`, default endpoint `http://localhost:11434` | Contextual explanation over retrieved evidence |
| Embeddings | SentenceTransformers `all-MiniLM-L6-v2` | `local_files_only=True`; model must be pre-staged | Semantic retrieval over approved local documents |
| Vector store | ChromaDB | Local persistent collection `misra_rules`; anonymized telemetry disabled | Stores and retrieves approved evidence chunks |
| Orchestration | LangChain | Retriever `k=5`; Pydantic JSON parser | Builds bounded prompts and validates structured output |
| Deterministic analysis | Project Python module | Conservative regex/control-pattern preflight | Reproducible candidate detection and offline fallback |
| Repository analysis | Project Python module | In-memory ZIP validation; max 8 MB compressed, 300 source files, 256 KB/file, 2 MB total source, ratio 200 | All-file scan, module summaries, repository tree, include dependencies and path-specific findings |
| Access control | API middleware and JSON permission policy | Random per-run key, authenticated user, repository ID and path prefixes | Reject unauthenticated or unauthorized repository access |
| Interface theme | Streamlit theme configuration and scoped UI CSS | Explicit foreground/background pairs for text, widgets, tabs, metrics, alerts, tables and buttons | Prevent unreadable text when browser or Streamlit theme defaults differ |
| Static-analysis evidence | SARIF 2.1 parser | Up to 100 bounded results | Normalize tool, rule, severity, message, file and line |
| CI integration | `tools/ci_review.py` | JSON/SARIF output and configurable severity gate | Pull-request evidence and machine-readable results |
| Workflow store | SQLite | Review metadata, input hashes, output, status and audit events | Human-review traceability; source body is not stored |

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama endpoint |
| `REVIEW_API_URL` | `http://localhost:8000/api/v1/review` | Streamlit-to-API address |
| `REVIEW_API_KEY` | empty | Optional pilot API key |
| `REVIEW_DB_PATH` | `data/reviews.db` | SQLite database path |

## Grounding and citation policy

1. Repository source, warnings, logs and related modules are delimited as untrusted data and are never executed.
2. The LLM may use only retrieved local standard excerpts for a rule reference.
3. A cited rule must be present in retrieved context. Otherwise the system outputs exactly `No applicable rule found` and assigns Low confidence.
4. The model provides a concise verification summary, not hidden chain-of-thought.
5. Output is advisory and cannot approve a merge, release or compliance state.

## Offline behavior

The review path does not download embedding files. If the local embedding model, Chroma index or Ollama endpoint is unavailable, the system returns a labeled `deterministic-fallback` result. This preserves useful local evidence without pretending that RAG or LLM review occurred.

## Submitted knowledge-base limitation

The included standard PDF is synthetic and demonstrates ingestion/citation mechanics only. It is not a licensed MISRA publication and must not be used to claim MISRA compliance. Production deployment requires organization-approved, properly licensed standards.
