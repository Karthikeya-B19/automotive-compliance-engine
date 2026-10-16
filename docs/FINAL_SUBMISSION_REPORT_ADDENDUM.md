# Final submission supplement

Release 3.0, 16 October 2026. This supplement updates packaging, reproducibility, dataset understanding and rubric traceability. The active review logic and its retained 12 October retrieval/model experiments are unchanged. Component and CLI checks were rerun on 16 October: 93 passed, zero failures, zero skips. A nonfatal Starlette deprecation warning remains.

## Problem, users and measurable objectives

Case Study 4 addresses review of confidential automotive C/C++ without transmitting source to a hosted AI endpoint. Embedded developers and reviewers receive module summaries, located candidates, diagnostics and cited advisory guidance. The measurable contracts are safe archive handling, repeatable pattern detection, evidence preservation, retrieval ranking, abstention, citation validation and recorded human disposition. No measured reduction in engineer debugging time or defect leakage is claimed because a controlled human study was not performed.

## Dataset understanding, preprocessing and exploratory analysis

The public benchmark is a convenience sample of 100 actual public repositories, including tutorials and prototypes. It contains 6,721 eligible source records and 105,296,667 source bytes. Extensions are 3,448 .h, 3,137 .c, 132 .cpp, three .hpp and one .cc. Median file size is 3,916 bytes; the observed nearest-rank-style p95 index used by the audit gives 76,231 bytes. Files range from zero to 261,307 bytes. Empty files are retained as valid robustness inputs rather than fabricated source.

The retained source hashes identify 5,542 unique contents and 1,179 duplicate-content instances. Of the hashes, 193 occur in more than one repository. Duplicates remain in the source-tree robustness test, so repository and file counts do not imply statistical independence. They are not counted as independently labelled real defects. Candidate precision and recall on this corpus remain unknown.

The scanner excludes 584 entries in ignored directories, 46 non-UTF8 entries and 94 oversized sources in the retained records. These are listed by reason and path. It validates archive paths, sizes and encodings before source analysis; masks comments/literals while retaining offsets; inventories functions/includes; and partitions large corpora within the same upload-source limits. Cross-partition dependencies are incomplete. Repository license metadata is incomplete or unasserted in 50 records; full public snapshots are therefore excluded from the final submission. The two redistributed ECU fixture families preserve their upstream licenses in every ZIP.

There is no supervised model training, model fitting, random train/test split or PCA step. Frozen sentence embeddings provide semantic representations. BM25 tokens preserve exact identifiers. The author wrote the 20 labelled retrieval queries and advisory cards, so selection bias and optimistic overlap are possible. There is no independently adjudicated unseen holdout. ECU baseline/mutant files intentionally share source as paired controls. No independence or leakage-free generalization claim is made.

Audit source: evaluation/audit_submission_evidence.py. Retained output: Evaluation_Results/CB.AI.U4AID23109_EvidenceAudit_v3.0.json. The audit recomputes repository, file, line and candidate counts; recalculates both retrieval strategies' metrics; and compares implementation hashes with the actual source. All eight numerical/inventory checks pass and the recorded implementation hash comparisons have no mismatches.

## Approach selection and syllabus relevance

Lexical BM25 gives an interpretable baseline. Local sentence embeddings help with paraphrases. Reciprocal rank fusion combines rankings without assuming equal score scales. The measured comparison is BM25 versus BM25 plus embeddings on identical queries and corpus, not a comparison between multiple trained language models. Retrieval improves recall@5 from 18/20 to 19/20, top-one accuracy from 14/20 to 17/20 and MRR@5 from 0.792 to 0.892. All 20 ranks and the remaining shift-rule miss are preserved.

The representation choices match this retrieval task: identifier-preserving tokens, normalized semantic vectors, typed rule IDs, explicit applicability assumptions and structured evidence. Supervised feature importance, PCA and training curves do not apply to an unfitted retrieval index. An 8B quantized local llama3.1 generates explanations, but the project does not claim it outperforms other LLMs. The project-specific contribution is the composition of detector evidence, hybrid retrieval, applicability gating, citation validation and inspectable control interventions, rather than invention of the underlying retrieval algorithms.

## Configuration and deployment boundaries

The tested evaluator path is Python 3.12, requirements.txt and python run.py from Code. Requirements pin NumPy 1.26.4 and PyArrow 25.0.1 to avoid the fresh-install table-rendering failure exposed by CI. The launcher binds API and UI to localhost, generates matching temporary API credentials and selects available ports. Existing user processes are not terminated. Source code, model weights, SQLite data and review outputs require the evaluator's approved local storage.

The approved all-MiniLM-L6-v2 embedding model must already be cached. Ollama must run locally with llama3.1 for actual generation. Optional model setup requires an explicit network download before an offline evaluation. No model weights or virtual environment are bundled. Without local models, lexical retrieval and clearly labelled deterministic/template results remain available. A fallback must not be presented as actual model generation.

The active card vectors are cached in memory. The legacy PDF ingestion code can create a persistent Chroma index, but that index does not supply active v2 review context. Persistent project-scoped vector storage, enterprise IAM, application-level encryption and full compiler data flow remain gaps relative to the proposed enterprise reference architecture. Host encryption and network isolation must be confirmed by the student/institution; localhost binding does not prove encryption. Docker configuration is supplied as optional deployment material and was not built or certified during this final audit.

Fresh Ubuntu/Python 3.12 CI run 38263557545 passed dependencies, 93 tests, SARIF generation and upload for implementation commit 789505fa7558aa94c52441ee2c4e404e78e8a136. The final package receives its own test and HTTP smoke-test records. CI runs component tests without claiming to execute Ollama or a real ECU build. The independent GCC warning covers one synthetic host snippet only.

## Responsible AI and mandatory human actions

Source and logs are untrusted data. Prompt delimiters, bounded inputs, typed applicability and exact citation/quote validation reduce unsupported output. They do not prove immunity to every prompt injection. Source excerpts can occur in reports and the SQLite database even though separate source bodies are not intentionally stored. Reviewers must treat these artifacts as sensitive. Confidence labels are not calibrated probabilities.

The system records human acceptance/rejection/needs-changes; it never merges or approves vehicle software. Suggested fixes require compilation, tests, approved analysis and qualified reviewer confirmation. No vehicle firmware is compiled, flashed or executed by the benchmark. Synthetic AUTO cards are project guidance, not authoritative MISRA/ISO clauses.

The located synopsis and declarations were unsigned and described the earlier method. Current technical content is supplied in new unsigned forms. The student must review and sign both declarations, obtain faculty approval for the synopsis, and verify the AI-use table personally. The assistant cannot fabricate these approvals or attest to the student's personal verification.

The supplied recording is 7 minutes 15.77 seconds, created on 7 October 2026. Sampled frames show the older three-tab UI, predating the revised retrieval pipeline and Verification lab. It is preserved as historical demonstration evidence, not proof of the submitted implementation. A fresh 5-10-minute recording of the submitted version remains required. Presentation timing is 10 minutes, live demonstration 10 minutes, technical Q&A eight minutes and evaluator transition two minutes. Evaluation/scoring and faculty sign-off remain faculty responsibilities.

## Reflection and conclusion

The initial implementation's mock-PDF citation check could not establish reliable applicability. Explicit advisory provenance, typed rule matching and extractive citation validation make narrower, auditable claims. Actual model output includes both a valid unsafe-copy citation and a rejected zero-division source quote, demonstrating why generation still needs an independent gate. The 100-repository robustness result, 40 controlled ECU mutations, 20-query retrieval experiment and 93 component tests answer separate questions.

The strongest next improvements are independently labelled queries/defects, compiler AST and control-flow facts, reviewed MCU/RTOS/CAN-FD profiles, persistent project-isolated retrieval, measured concurrency and hardware validation. The final package documents these limits and personal completion actions openly rather than treating a passing test suite as proof of unrestricted correctness.
