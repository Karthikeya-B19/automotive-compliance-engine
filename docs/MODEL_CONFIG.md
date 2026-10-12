# Model and Retrieval Configuration

Version 2.0.

| Component | Active implementation |
| --- | --- |
| Advisory corpus | 20 versioned synthetic cards in `data/standards/automotive_rule_cards.json` |
| Lexical ranking | Local BM25 with length normalization |
| Dense ranking | Locally cached `all-MiniLM-L6-v2`, normalized vectors and cosine/dot product |
| Fusion | Reciprocal rank fusion with constant 60 |
| Retrieval depth | Top 5 candidates per finding |
| Applicability | Exact typed detector rule ID must occur in retrieved candidates |
| Generator | Local Ollama `llama3.1`, temperature 0, JSON format, bounded output |
| Citation validation | Applicable rule ID plus nonempty extractive supporting evidence |
| Evidence | Corpus/card hashes, query, scores, applicability and citation decisions |

Set `REVIEW_DENSE_RETRIEVAL=false` for lexical-only operation. `OLLAMA_BASE_URL` defaults to `http://localhost:11434`. Normal review never downloads the embedding model. Pre-stage approved model assets before an offline demonstration.

If embeddings are unavailable, traces say `bm25` rather than hybrid. If Ollama is unavailable but retrieval succeeds, the response says `retrieval-grounded-template`. No model generation is claimed for that mode.

The legacy PDF ingestion utilities can still create a Chroma index for experiments. That index is not used by the active v2 rule-card review path. Licensed standards ingestion and edition-specific clause validation remain separate future integration work.

The local launcher authorizes user-supplied ZIPs under `uploaded-repository`; administrator-provided `REVIEW_REPOSITORY_PERMISSIONS` overrides that pilot profile. The review service is not an enterprise IAM or multi-tenant deployment.

Target assumptions include a 32-bit int platform for shift checks and classical CAN for `can_dlc`. Cards are advisory project rules and never official MISRA/ISO clauses. Corpus changes require review and regeneration of retrieval evidence.
