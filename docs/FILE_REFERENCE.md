# Project File Reference

This guide explains the purpose of every maintained file in the Automotive Secure Code Review Assistant repository. It is a navigation aid for the project owner, evaluator, and future user. Runtime-only folders such as `.venv/`, `.git/`, generated caches, local databases, temporary uploads, and packaged submission copies are intentionally excluded because they are not maintained source artifacts.

## Start Here

| File | Purpose |
| --- | --- |
| `README.md` | Primary project overview: capabilities, setup, architecture, safety boundaries, and quick-start commands. |
| `USER_GUIDE.md` | User-facing instructions for running the application and performing a review. |
| `run.py` | Starts the FastAPI backend and Streamlit interface together, selecting available ports safely. |
| `requirements.txt` | Python dependencies required to run and test the application. |
| `pytest.ini` | Pytest discovery and test configuration. |
| `.env.example` | Safe template for environment variables; contains no real secrets. |
| `.gitignore` | Prevents local environments, caches, databases, uploads, and submission-package copies from being committed. |
| `create_dummy_data.py` | Creates demonstration data for local development where required. |

## Application Source Code

| File | Purpose |
| --- | --- |
| `src/api/__init__.py` | Marks the API directory as a Python package. |
| `src/api/main.py` | FastAPI backend: health endpoint, review endpoints, validation, and orchestration of analysis services. |
| `src/analysis/__init__.py` | Marks the analysis directory as a Python package. |
| `src/analysis/static_analyzer.py` | Finds security and automotive C/C++ code issues using deterministic rules and produces structured findings. |
| `src/analysis/repository_analyzer.py` | Safely examines an uploaded repository or ZIP, applies scope limits, traverses source files, and aggregates findings. |
| `src/analysis/evidence_parser.py` | Parses uploaded compiler or SARIF evidence into normalized review findings. |
| `src/ingestion/__init__.py` | Marks the ingestion directory as a Python package. |
| `src/ingestion/ingest.py` | Loads and chunks the local automotive-standard reference for retrieval. |
| `src/rag/__init__.py` | Marks the RAG directory as a Python package. |
| `src/rag/orchestrator.py` | Retrieves relevant standard excerpts and, when configured, requests an Ollama explanation grounded in those excerpts. |
| `src/storage/__init__.py` | Marks the storage directory as a Python package. |
| `src/storage/review_store.py` | Provides local SQLite persistence for review records, authentication data, and workflow state. |
| `src/ui/__init__.py` | Marks the user-interface directory as a Python package. |
| `src/ui/app.py` | Streamlit interface for code, repository, and evidence reviews; includes readable theme and accessible contrast styling. |
| `tools/ci_review.py` | Command-line/CI entry point that runs a review and emits a machine-readable result. |

## Configuration, Deployment, and Automation

| File | Purpose |
| --- | --- |
| `.streamlit/config.toml` | Defines the application theme, including explicit high-contrast foreground and background colours. |
| `.github/workflows/secure-code-review.yml` | GitHub Actions workflow that installs dependencies and runs the test suite on repository changes. |
| `docker/Dockerfile` | Container recipe for a reproducible application environment. |
| `docker/docker-compose.yml` | Docker Compose configuration for running the project services together. |

## Standards, Tests, and Evaluation

| File | Purpose |
| --- | --- |
| `data/standards/MISRA_C_Mock_Standard.pdf` | Local reference document used as the retrieval corpus for standards-grounded explanations. |
| `tests/test_api.py` | Verifies API health and review request behaviour. |
| `tests/test_evaluation.py` | Checks evaluation logic and expected findings against labelled cases. |
| `tests/test_guideline_alignment.py` | Tests the implementation against the stated case-study and submission requirements. |
| `tests/test_repository_analyzer.py` | Tests safe repository/ZIP handling, file selection, and repository review behaviour. |
| `tests/test_static_analyzer.py` | Unit tests for the deterministic static-analysis rules. |
| `evaluation/__init__.py` | Marks the evaluation directory as a Python package. |
| `evaluation/ground_truth.json` | Labelled expected results used to measure the analyser on known cases. |
| `evaluation/run_evaluation.py` | Runs the code-snippet evaluation and produces evaluation metrics. |
| `evaluation/run_repository_evaluation.py` | Runs the repository-level evaluation and produces aggregate results. |
| `Evaluation_Results/CB.AI.U4AID23109_EvaluationCases_v1.0.csv` | Human-readable list of evaluation cases and expected outcomes. |
| `Evaluation_Results/CB.AI.U4AID23109_EvaluationResults_v1.0.json` | Saved results of the snippet-level evaluation. |
| `Evaluation_Results/CB.AI.U4AID23109_RepositoryEvaluation_v1.0.json` | Saved results of the repository-level evaluation. |
| `Evaluation_Results/CB.AI.U4AID23109_SampleReview_v1.0.json` | Example structured output from a review. |
| `Evaluation_Results/CB.AI.U4AID23109_TestLog_v1.0.txt` | Initial automated-test execution record. |
| `Evaluation_Results/CB.AI.U4AID23109_TestLog_v1.1.txt` | Updated automated-test execution record. |
| `Evaluation_Results/CB.AI.U4AID23109_TestLog_v1.2.txt` | Current recorded automated-test execution evidence. |

## Demonstration Inputs

| File | Purpose |
| --- | --- |
| `demo/CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip` | Intentionally faulty automotive-style sample repository for the upload demo. |
| `demo/CB.AI.U4AID23109_CleanSpeedMonitor_v1.0.zip` | Cleaner comparison repository for demonstrating lower-severity output. |
| `demo/CB.AI.U4AID23109_MixedSensorNetwork_v1.0.zip` | Mixed-quality repository for demonstrating scope and finding diversity. |
| `demo/unsafe_ecu_state.c` | Small standalone unsafe C example for a quick code-paste review. |
| `demo/compiler_warnings.txt` | Sample compiler-warning evidence for evidence-import demonstrations. |
| `demo/repository/automotive_ecu_demo/README.md` | Description of the intentionally faulty ECU demo repository. |
| `demo/repository/automotive_ecu_demo/include/vehicle_state.h` | Header used by the ECU demo sources. |
| `demo/repository/automotive_ecu_demo/src/main.c` | ECU demo entry point containing reviewable patterns. |
| `demo/repository/automotive_ecu_demo/src/vehicle_state.c` | ECU state-management source containing reviewable patterns. |
| `demo/repository/automotive_ecu_demo/vendor/legacy_copy.c` | Vendor-like copy used to demonstrate exclusion/scope handling. |
| `demo/repository/clean_speed_monitor/README.md` | Description of the cleaner speed-monitor demo. |
| `demo/repository/clean_speed_monitor/include/speed_monitor.h` | Header for the cleaner speed-monitor demo. |
| `demo/repository/clean_speed_monitor/src/speed_monitor.c` | Source for the cleaner speed-monitor demo. |
| `demo/repository/mixed_sensor_network/README.md` | Description of the mixed-quality sensor-network demo. |
| `demo/repository/mixed_sensor_network/include/sensor.h` | Header for the sensor-network demo. |
| `demo/repository/mixed_sensor_network/src/sensor_name.c` | Sensor-name source used in the mixed demo. |
| `demo/repository/mixed_sensor_network/src/sensor_reader.c` | Sensor-reading source with reviewable patterns. |
| `demo/repository/mixed_sensor_network/generated/generated_copy.c` | Generated-like copy used to demonstrate exclusion/scope handling. |

## Documentation and Submission Evidence

| File | Purpose |
| --- | --- |
| `docs/EVALUATION_GUIDE.md` | Explains the evaluation dataset, commands, metrics, and interpretation of results. |
| `docs/GUIDELINE_TRACEABILITY.md` | Maps project features and artifacts to the case-study and submission guidelines. |
| `docs/MODEL_CONFIG.md` | Describes the local model configuration, fallback behaviour, and responsible-use controls. |
| `docs/PACKAGE_README.md` | Explains the final-submission folder/package contents and how an evaluator should inspect it. |
| `docs/PROMPT_GUARDRAILS.md` | Documents prompts, grounding requirements, and guardrails used for AI-assisted explanations. |
| `docs/SUBMISSION_CHECKLIST.md` | Final pre-submission checklist for required structure, files, and verification. |
| `docs/VIDEO_PLACEHOLDER.txt` | Placeholder explaining where to place the final demonstration video. |
| `docs/VIDEO_SCRIPT.md` | Narration and action script for recording the project demonstration. |
| `docs/FILE_REFERENCE.md` | This file: a purpose-by-purpose map of the maintained repository files. |

## Visual Evidence and Final Deliverables

| File | Purpose |
| --- | --- |
| `assets/automotive_security_cover.png` | Cover/branding image used in project documentation and presentation. |
| `assets/app_interface_evidence.png` | Screenshot evidence of the user interface. |
| `assets/app_review_evidence.png` | Screenshot evidence of an application review. |
| `assets/repository_review_evidence.png` | Screenshot evidence of a repository-upload review. |
| `deliverables/CB.AI.U4AID23109_TechnicalReport_v1.2.docx` | Earlier editable technical-report revision, retained for revision history. |
| `deliverables/CB.AI.U4AID23109_TechnicalReport_v1.2.pdf` | Earlier PDF technical-report revision, retained for revision history. |
| `deliverables/CB.AI.U4AID23109_TechnicalReport_v1.3.docx` | Current editable technical report for submission. |
| `deliverables/CB.AI.U4AID23109_TechnicalReport_v1.3.pdf` | Current PDF technical report for submission. |
| `deliverables/CB.AI.U4AID23109_Presentation_v1.4.pptx` | Earlier presentation revision, retained for revision history. |
| `deliverables/CB.AI.U4AID23109_Presentation_v1.5.pptx` | Current presentation deck for submission and evaluation. |

## Package Copies and Generated Local Files

The `submission_v*` folders and their ZIP files are versioned, self-contained copies prepared for final delivery. They repeat the maintained materials above under the prescribed submission folder structure. They are deliberately not tracked by Git to avoid duplicating the repository content.

During normal use, the app may also create local SQLite data, Chroma/RAG indexes, temporary extracted uploads, and Python cache folders. These files are operational state rather than submission artifacts; they are excluded by `.gitignore` and should not be committed or submitted unless an evaluator explicitly requests them.
