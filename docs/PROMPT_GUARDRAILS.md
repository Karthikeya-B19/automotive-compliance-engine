# Prompt and Evidence Guardrails

Version 2.0.

Retrieval queries use deterministic candidate titles, categories and recommendations. Arbitrary source comments do not enter ranking as instructions. Model input is bounded and escaped into data delimiters.

The system prompt instructs the local model to use supplied advisory cards, return structured JSON, cite an exact AUTO rule ID and quote applicable context. Synthetic cards must not be represented as official MISRA or ISO clauses.

Programmatic controls supplement the prompt:

1. Similarity alone cannot authorize a citation. The retrieved card must match the detector's typed rule ID.
2. Missing applicable evidence produces explicit abstention.
3. A model citation must identify an applicable context card.
4. Evidence quotes must be nonempty extracts from matching context.
5. Rejected model evidence clears citation, source evidence and model remediation and lowers confidence.
6. Deterministic findings remain separate from the rejected model answer.

Tests include forged IDs, unrelated citations, invented quotes, empty evidence, corpus deletion, unrelated corpus replacement, model outage and cached-result mutation. Live evidence includes actual local Ollama calls.

These controls validate specified contracts. They do not establish universal prompt-injection resistance, true code-defect status or semantic correctness of every generated sentence. Local corpus administration is trusted, and human review remains mandatory.
