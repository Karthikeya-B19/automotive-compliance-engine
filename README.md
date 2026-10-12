# ECU Review Studio

Automotive Secure Code Review Assistant for embedded C/C++ repositories. Individual TechPulse Case Study 4 capstone by Karthikeya Bellapukonda, CB.AI.U4AID23109, Amrita Vishwa Vidyapeetham.

The app reviews a source snippet or repository ZIP, shows located security and embedded-system review candidates, retrieves synthetic advisory guidance, and exports an inspectable JSON report. Version 2.0 includes 20 rule families, hybrid retrieval, citation validation, finding filters, review history and a Verification lab.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Open the Dashboard URL printed by the launcher. Occupied ports are skipped automatically.

For local model explanations, start Ollama with the installed `llama3.1` model. The approved `all-MiniLM-L6-v2` embedding model must already be cached locally. Without these dependencies, the app labels lexical retrieval and template/fallback modes explicitly.

## Use the app

Choose **Repository ZIP review**, select `uploaded-repository`, upload a UTF-8 C/C++ ZIP and click **Analyze repository**. Inspect candidates, retrieved guidance and assumptions. Filter by severity, category or text, and download the JSON result. **Single-file review** accepts pasted or uploaded source. **Review history & metrics** shows saved reviews and human decisions.

Try the three ZIPs in `demo/`. Real ECU baseline/mutant fixtures are under `Evaluation_Results/ecu_mutations/`; choose matching filenames for comparison. They are educational fixtures containing deliberate defects and must never be flashed to hardware.

Open **Verification lab** for the measured public benchmark, RAG experiments, actual local model traces, component results and ECU mutations.

## Reference material

- [User guide](USER_GUIDE.md)
- [Detailed technical report and examination preparation](docs/TECHNICAL_REPORT_v2.md)
- [Testing evidence and reproduction commands](docs/EVALUATION_GUIDE.md)
- [File reference](docs/FILE_REFERENCE.md)
- [Model configuration](docs/MODEL_CONFIG.md)

The active rule corpus is synthetic project guidance, not official MISRA or ISO clauses. Findings require qualified human confirmation. A clean scan does not prove compliance. Normal upload limits are 8 MB ZIP, 300 supported files, 256 KB per file and 2 MB expanded source. Runtime review is local; benchmark reproduction initially downloads public sources.
