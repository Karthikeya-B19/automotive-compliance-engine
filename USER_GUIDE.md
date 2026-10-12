# ECU Review Studio User Guide

Version 2.0. The app inspects C/C++ code, maps source modules and include dependencies, reports deterministic candidates, retrieves advisory rule cards, and records human review decisions.

## Starting the app

Install `requirements.txt` into a virtual environment and run `python run.py`. Open the Dashboard URL printed in the terminal. The launcher selects free ports and supplies matching API credentials to the interface. Keep the terminal running.

Optional RAG dependencies are a locally cached `all-MiniLM-L6-v2` model and a running Ollama service with `llama3.1`. No review-time model download occurs. A missing model is shown through the actual retrieval strategy or fallback mode.

## Repository reviews

Select **Repository ZIP review** and choose `uploaded-repository` for your own authorized upload. The named demonstration IDs apply narrower source-prefix permissions. Upload a ZIP containing UTF-8 `.c`, `.cc`, `.cpp`, `.cxx`, `.h` or `.hpp` files. Arduino `.ino` files are outside the present scope.

Optionally add warnings and text or SARIF build evidence. Enable local grounding to retrieve guidance for all detected candidates and request an LLM explanation for the highest-risk module. Click **Analyze repository**.

Inspect the module map and dependencies. Use severity, category and text filters to narrow candidates. Results display 20 candidates per page. Each candidate shows its source location, evidence and recommendation. A retrieved rule expander shows the advisory excerpt, assumptions and hash.

Open **Retrieval evidence** to inspect queries, top-five candidates, lexical/dense scores and fusion scores. `supported-candidate` means the guidance applies to that candidate. `abstain` means the corpus did not supply a matching retrieved rule. Neither confirms a defect without review.

Download the structured JSON for full findings and traces. Record your decision, reviewer name and rationale after confirming the result.

## Single file and history

**Single-file review** accepts pasted source or an uploaded supported source file, warnings and related modules. Click **Run secure review**. **Review history & metrics** displays saved reviews and their human dispositions.

## Manual examples

The ZIPs in `demo/` provide faulty, cleaner and mixed source trees. The files in `Evaluation_Results/ecu_mutations/` contain actual Speeduino and rusEFI source with corresponding baseline and deliberately mutated versions. Upload a baseline and its matching mutant to compare the injected line. These are static-analysis examples, never deployable vehicle firmware.

## Verification lab

The Verification lab reads saved evidence from `Evaluation_Results/`. Expand and download the public repository records, retrieval comparison, actual local LLM outputs, ECU mutation study and component checks. Results are dated artifacts, not a claim that the benchmark reruns every time the page opens.

## Interpreting modes

`rag-assisted` means a local model generated a structured answer. Inspect `citation_validation` to see whether its citation passed. `retrieval-grounded-template` means retrieval succeeded but the LLM was unavailable. `deterministic-only` means no applicable model context was available. Repository modes carry a `repository-` prefix.

The active 20 rule cards are synthetic advisory guidance. Confidence is not a calibrated probability. The analyser uses heuristics and does not prove MISRA compliance, timing correctness, alias safety or absence of defects.
