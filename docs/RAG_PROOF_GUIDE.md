# RAG evaluation and demonstration guide

Karthikeya Bellapukonda · CB.AI.U4AID23109 · Individual TechPulse Case Study 4

Companion to `deliverables/CB.AI.U4AID23109_RAGProof_v2.1.pptx`. Open the PowerPoint Notes pane for explanations and evidence locations on every slide. Slides 1–18 form the presentation. Slides 19–20 retain all 20 query ranks for questions.

## The claim you can defend

The project retrieves applicable advisory guidance for deterministic review candidates, improves ranking on the measured query set with hybrid search, abstains when applicable guidance is absent, runs an actual local language model, and rejects the demonstrated unsupported citations. Each statement has a separate retained evidence record. This evidence does not prove universal bug detection or safety certification.

## What RAG means here

Retrieval augmented generation supplies selected external knowledge to a language model at review time. It does not retrain or fine-tune the model. The analyser first detects supported C/C++ patterns. Retrieval then searches 20 versioned automotive advisory cards. The local `llama3.1` model explains candidates with that context, and a programmatic validator checks its claimed rule ID and evidence.

BM25 preserves exact embedded terms such as `can_dlc`, `strcpy` and ISR. It accounts for term rarity, repetition and document length. Local `all-MiniLM-L6-v2` embeddings handle paraphrases. Normalized-vector dot products measure cosine similarity. Reciprocal rank fusion combines the ranked lists as `sum(1 / (60 + rank))`, starting at rank one. It avoids directly adding incomparable BM25 and cosine scores.

Similarity alone cannot establish rule applicability. The gate requires the detector's typed rule ID in the retrieved top-five candidates. A missing match produces abstention. The citation validator separately requires an exact applicable ID, nonempty evidence and an extractive quote from the matching retrieved context.

The active review corpus is `data/standards/automotive_rule_cards.json`. Its cards are synthetic project guidance, not official MISRA or ISO clauses. The legacy PDF/Chroma utilities do not supply the active v2 review path. Hashes identify exact corpus/card versions, not the correctness or authority of their content.

## All measured evaluation metrics

| Measurement | Lexical BM25 | Hybrid BM25 + dense | Meaning |
| --- | --- | --- | --- |
| Recall@5 | 90% = 18/20 | 95% = 19/20 | Relevant labelled rule occurs among first five results |
| Top-1 accuracy | 70% = 14/20 | 85% = 17/20 | Relevant labelled rule ranks first |
| MRR@5 | 0.791667 | 0.891667 | Mean reciprocal rank, with zero for a top-five miss |

The experiment searches the same 20-card corpus with 20 author-labelled natural-language queries. There is one labelled relevant rule per query, so recall@5 acts as a per-query hit rate. Hybrid improves recall by five percentage points, top-one accuracy by 15 points and MRR by 0.100. `actual_strategy` confirms real dense retrieval rather than a fallback. Source: `Evaluation_Results/rag_evidence/retrieval_results.json` and `evaluation/prove_rag.py`.

The ISR-blocking query improves from a top-five miss to rank three. Array bounds, assignment conditions and `sprintf` improve from rank two to rank one. The fixed-width shift query remains a top-five miss in both strategies. All ranks, full queries, score traces and misses remain in the JSON and presentation appendix. The small author-labelled set has no independent adjudication and cannot establish general accuracy.

| System measurement | Recorded result | Interpretation |
| --- | --- | --- |
| Automated component suite | 93 passed, zero failures/skips | Specified component/API/UI contracts hold on these tests |
| Public corpus | 100 distinct repos, 6,721 eligible files | Bounded-batch robustness across actual source trees |
| Source volume | 2,650,420 lines | Eligible C/C++ source scanned |
| Repository-level failures | 0 of 100 | No repository-level scan failure in this run |
| Candidate findings | 2,017 | Unlabelled candidates, not verified vulnerabilities |
| Median total time | 0.679 seconds/repo | Includes cache/download and scan; not isolated analyser latency |
| ECU mutations | 40/40 detected at injected lines | Four supported synthetic defect families in ten real files |
| ECU upstream coverage | Two projects: Speeduino and rusEFI | Real source provenance, not firmware validation |
| Faulty CLI sample | Exit 1, four SARIF findings | Severity gate rejects the selected faulty sample |
| Clean CLI comparison | Exit 0, zero SARIF findings | Gate passes this clean comparison |
| Independent host compiler | GCC zero-division warning | Isolated synthetic snippet, not an ECU firmware build |

Sources: `Evaluation_Results/component_evidence.json`, `public_benchmark/summary.json` and `ecu_mutations/results.json`. The public sample contains tutorials and prototypes as well as automotive/embedded projects. No upstream code was executed. Cross-partition dependencies remain incomplete. No hardware run, flash or full ECU compilation occurred.

## Proof that retrieval actually contributes

Run `python evaluation/export_rag_controls.py`. It writes `Evaluation_Results/rag_evidence/control_interventions.json` with complete input findings, ranked results, scores, corpus hashes and decisions.

All corpus variants retain the source `int rpm_rate(int rpm) { return rpm / 0; }`, the deterministic finding and its query. They all use BM25 to isolate the corpus intervention.

| Corpus | Observed outcome |
| --- | --- |
| Relevant AUTO-DIV-ZERO card present | Supports the candidate |
| Same card deleted | Abstains from rule support |
| Only unrelated AUTO-NULL card supplied | Abstains despite a retrieved card |

The deterministic candidate remains present in all cases. Retrieval is therefore contributing guidance rather than claiming to detect the zero division itself. Inspect `corpus_cases[*].trace.per_finding[0]` for the query, expected ID, ranked candidates and decision.

The same file preserves four validator proposals: a correct quote passes; a forged ID, invented quote and empty evidence each fail. Two additional checks verify identical query and input findings across corpus variants. All nine checks pass. These proposals are programmatic controls and are not represented as actual LLM generation.

## Proof that a real language model ran

Source: `Evaluation_Results/rag_evidence/live_generation.json`. The file retains source snippets, local model metadata/digest, elapsed calls, actual-generation flags, retrieved context, proposed evidence and final validation decisions. The installed model was `llama3.1:latest`, 8B, Q4_K_M.

| Actual case | Model ran? | Recorded call | Outcome |
| --- | --- | --- | --- |
| Unbounded copy into `char name[8]` | Yes | 4.991 s | AUTO-STRCPY and exact advisory quote pass |
| Literal zero division | Yes | 8.282 s | Correct ID but source-code quote fails citation validation |
| Clean comparison `rpm / 2` | No | 0.001 s | Deterministic-only, no applicable candidate context |

These elapsed values are individual observations, not representative latency percentiles. The rejected zero-division response quoted `int rpm_rate(int rpm) { return rpm / 0; }` rather than retrieved advisory text. The validator clears its model citation and evidence while retaining the separately grounded deterministic finding. Its rejection is useful evidence of the gate, not proof that every model explanation is correct. Only one of the two generated answers passed citation validation in this saved run; avoid reporting a general answer-accuracy percentage from two examples.

## Fresh-install CI proof

[GitHub Actions run 38255018583](https://github.com/Karthikeya-B19/automotive-compliance-engine/actions/runs/38255018583) passed on fresh Ubuntu/Python 3.12. Its logs report 93 passing tests, no broken requirements, NumPy 1.26.4/PyArrow 25.0.1 compatibility, successful SARIF generation and successful upload. A nonfatal Starlette deprecation warning remains. The earlier failed run exposed dependency drift, which the compatibility patch fixed. CI verifies surrounding software contracts; it does not execute the installed local Ollama model.

## Reproduction commands

From the project root with its environment active:

```powershell
python -m pytest -q
python evaluation/prove_rag.py
python evaluation/export_rag_controls.py
python evaluation/prove_live_rag.py
```

Actual dense retrieval requires the local embedding model. Actual generation requires Ollama running with `llama3.1` installed. Check the recorded actual strategy and mode. A fallback is not a live-generation result. Rerunning a model may change its proposal, so read that run's citation decision rather than assuming it matches the saved example.

## A concise professor demonstration

1. Present the measured comparison and show `actual_strategy: bm25+dense-rrf` in the saved retrieval JSON.
2. Show the complete appendix so the remaining shift-rule miss is visible.
3. Run the control exporter. Show the same query and finding across present/deleted/unrelated corpus variants, then compare support with abstention.
4. Open the actual-generation file. Show the accepted AUTO-STRCPY quote and the rejected zero-division proposal with `actual_llm_generation: true`.
5. Start `python run.py`, select `uploaded-repository`, and compare a baseline/mutant ZIP from `Evaluation_Results/ecu_mutations/`. Match the added line to its finding.
6. Expand the retrieved excerpt, assumptions and query/score evidence. Use Verification lab for the stored benchmark, ECU and live-model records. The supplementary control-intervention JSON is available separately at its path above.
7. Finish with the successful CI run and the evidence boundaries.

## Questions to prepare for

**Why use RAG when the detector already knows the rule?** The detector supplies a candidate type. The versioned corpus supplies inspectable advisory guidance, assumptions and provenance. The deletion control proves this support depends on supplied knowledge. The model then explains that context. This implementation does not claim retrieval independently discovers unknown semantic bugs.

**Does 95% mean 95% bug-detection accuracy?** No. It means 19 of these 20 labelled queries retrieve their relevant rule in the first five results. The ECU mutation study is separate defect-detection evidence.

**Does citation acceptance guarantee a correct answer?** No. It checks the rule/quote contract. It cannot prove all generated reasoning or remediation is semantically correct. Human confirmation remains necessary.

**Why keep the model rejection and retrieval miss?** They show what the system actually did and make the result auditable. Removing failures would overstate effectiveness.

**What would strengthen the evidence next?** Independently labelled queries and defects, a larger approved corpus, compiler AST/control-flow facts, reviewed MCU/RTOS/CAN-FD profiles, concurrency/resource measurements and hardware validation. These are future work rather than implemented capabilities.
