# Evaluation Evidence Guide

Version 2.0. The evidence is divided by the question each experiment answers.

| Evidence | What it demonstrates | What it does not establish |
| --- | --- | --- |
| `Evaluation_Results/component_evidence.json` and `tests_v2.0.xml` | Actual component/API/UI tests, persistence, archive controls and CLI gates | Universal correctness |
| `Evaluation_Results/public_benchmark/summary.json` and `results.json` | Scan robustness across 100 distinct actual public source trees | Precision/recall on real defects or 100 production ECUs |
| `Evaluation_Results/ecu_mutations/results.json` | Expected defect detected at each injected line in 40 mutations across 10 real ECU files | Unknown defect coverage or firmware build correctness |
| `Evaluation_Results/rag_evidence/retrieval_results.json` | Lexical versus actual dense hybrid ranking and intervention controls | Large-corpus generalization |
| `Evaluation_Results/rag_evidence/live_generation.json` | Actual local Ollama generation and citation decisions | A guarantee that every model sentence is correct |
| `Evaluation_Results/*_v2.0.sarif` | Actual SARIF output and severity exit codes | Certified static analysis |

## Reproduce

Run from the repository root with the project environment active:

```powershell
python tools/build_rule_corpus.py
python evaluation/component_verification.py
python evaluation/prove_rag.py
python evaluation/prove_live_rag.py
python evaluation/ecu_mutation_study.py
python evaluation/benchmark_public_repos.py --target 100 --workers 6
```

Ollama must be running for actual generation. Local embeddings must already exist for dense retrieval. The scripts report the actual strategy and mode. A mocked response is not counted as a live-generation result.

The first public/ECU runs need Internet access. Snapshots are retained under ignored `benchmark_cache/`. Keep that cache for exact byte-for-byte replay. Catalog refresh is explicit through `--refresh-catalog`; a refreshed branch can change source bytes. The snapshot root and archive/file hashes document what was scanned.

## Benchmark scope

Public snapshots are unlabelled convenience samples. All eligible supported C/C++ files are passed through the actual ZIP scanner in bounded partitions. Ignored directories, encoding problems and oversized sources are listed. Dependencies across partitions are incomplete. The app's ordinary upload limits remain in force.

The 100-repository run covers 6,721 eligible files and 2,650,420 lines. Findings are candidates, not confirmed vulnerabilities. Timings include cache/download and scan effects. Consult the final summary for implementation hashes and exact totals.

## ECU mutations

Speeduino and rusEFI source files retain their licenses in the manual fixtures. Forty educational injections cover zero division, null dereference, fixed array bounds and unbounded copy. Detection requires the expected title at the injected line. Baseline counts, mutant counts, hashes and patches remain available. Full firmware was not compiled or executed.

## Retrieval measurements

Twenty author-labelled natural-language queries test the 20 advisory rules. Lexical recall@5 is 0.90 and top-one accuracy is 0.70. Actual hybrid recall@5 is 0.95 and top-one accuracy is 0.85. Misses remain visible. Corpus-removal, unrelated-context and forged-citation controls verify abstention and rejection.

## UI verification

### Fresh-install CI compatibility patch (2.0.1)

The initial Ubuntu/Python 3.12 CI run passed 92 tests and failed one UI test because unpinned PyArrow 26 required NumPy 2 while the project uses NumPy 1.26.4. Requirements now explicitly pin PyArrow 25.0.1, the working local version. CI checks dependency metadata and an actual NumPy-to-Arrow conversion before running the full suite. SARIF upload is conditional on the report existing, preventing a missing-report error from obscuring an earlier failure. Action versions were updated to checkout v5, setup-python v6 and upload-sarif v4. The analyser, RAG architecture and v2 report/presentation measurements are unchanged by this packaging/CI patch. Use the latest successful GitHub Actions run as the fresh-install evidence, not the earlier failed run.

Streamlit AppTest checks actual screen construction, review/evidence rendering and controls. A numeric WCAG AA check covers declared foreground/background pairs. Connected browser surfaces were unavailable during this revision, so these tests must not be described as full browser visual or accessibility certification.
