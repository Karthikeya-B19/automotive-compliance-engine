# Automotive Secure Code Review Assistant

## What it does

This application reviews an uploaded ZIP of a C or C++ repository without extracting or executing its contents. It validates the archive, scans supported source and header files, summarizes modules and functions, maps local quoted-header dependencies, identifies selected pointer, boundary, resource, and control-flow risks, and presents path-specific evidence and recommendations.

It can also use a locally hosted language model and a local index of approved engineering guidance to explain findings. If those services are unavailable, it clearly labels the result as a deterministic fallback. Review results can be downloaded as JSON, and a human reviewer can record an Accepted, Rejected, or Needs changes decision. Source-code bodies are not stored in the review database.

This is an educational review assistant. It does not compile code, prove MISRA compliance, certify safety, or replace approved analyzers, testing, and qualified review.

## How to use it

### Install

Use Python 3.11 or newer. From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Optional grounded explanations require a local Ollama installation and the configured model:

```powershell
ollama pull llama3.1
python create_dummy_data.py
python src/ingestion/ingest.py
```

The included guidance PDF is synthetic demonstration material, not the official MISRA standard.

### Start

```powershell
python run.py
```

Open `http://localhost:8501`. API documentation is available at `http://localhost:8000/docs`.

### Readable display

The dashboard uses a high-contrast light theme. Text, inputs, placeholders, tabs, metrics, alerts, tables, expanders, and buttons have explicit readable foreground and background colors. If an earlier color remains visible after an update, stop the app, run `python run.py` again, and hard-refresh the browser with `Ctrl+Shift+R`.

### Review a repository

1. Open **Repository ZIP review**.
2. Enter the authorized repository ID. For the included samples use `automotive-ecu-demo`, `clean-speed-monitor`, or `mixed-sensor-network`.
3. Upload a ZIP containing C/C++ files such as `.c`, `.cc`, `.cpp`, `.cxx`, `.h`, or `.hpp`.
4. Optionally paste compiler warnings and upload build, runtime, JSON, XML, or SARIF evidence. SARIF files are structurally parsed.
5. Leave local grounding enabled when Ollama and the local index are ready; otherwise disable it or allow the labeled fallback.
6. Select **Analyze repository**.
7. Inspect authorization status, repository summary, module table, dependency map, performance observations, skipped-file reasons, limitations, and findings.
8. Download the JSON report.
9. Record a human disposition with reviewer name and validation notes. Accepted findings can be reused as bounded historical context.

For a single source file, use the **Single-file review** tab instead.

### Try the included samples

- `demo/CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip`: four intentional findings and an ignored vendor file.
- `demo/CB.AI.U4AID23109_CleanSpeedMonitor_v1.0.zip`: a small repository expected to produce no deterministic findings.
- `demo/CB.AI.U4AID23109_MixedSensorNetwork_v1.0.zip`: multiple modules, dependency edges, one intentional boundary finding, and an ignored generated file.

### Run verification

```powershell
python -m pytest -q
python evaluation/run_evaluation.py
python evaluation/run_repository_evaluation.py
```

All AI output is advisory. Confirm findings by compiling the project, running tests, using approved static-analysis tools, and obtaining qualified human review.
