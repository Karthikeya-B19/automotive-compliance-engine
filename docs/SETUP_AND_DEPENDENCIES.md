# Evaluator setup and dependency disclosure

Tested baseline: Python 3.12 on Windows and fresh Ubuntu CI. Run commands from Code in the submission folder, or the repository root in a source checkout. Do not copy a virtual environment between machines.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe run.py
```

The launcher binds to localhost, selects available ports and supplies temporary matching API credentials. Open its printed Dashboard URL. No .env file is needed for the default pilot. The supplied .env.example is an administrator template; its deliberately narrow sample policy must be adjusted before using arbitrary uploaded repositories. Never commit real keys or local databases.

## Optional local-model setup

The application does not download models during review. With institutional permission and network access, pre-stage the models before an offline demonstration:

```powershell
.venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ollama pull llama3.1
ollama list
```

Ollama must be installed separately and its local service running. Start it only if it is not already running. The installed service typically uses localhost:11434; OLLAMA_BASE_URL can specify an approved local/private endpoint. Model license review, disk capacity and approved network access are the institution/student's responsibility. The observed llama3.1 package was approximately 4.9 GB; it is not bundled. Dense retrieval requires the embedding cache on the evaluator's machine.

Without these optional assets, the app still performs local deterministic analysis and lexical retrieval, and reports the actual template/fallback mode. Do not describe such a result as actual LLM generation. The supplied live-generation JSON remains dated evidence of the earlier measured run.

## Evidence and authoring tools

Run `.venv\Scripts\python.exe -m pytest -q` for component tests. The evaluation scripts reproduce separate experiments; public/ECU source acquisition requires network access. The final evidence audit reads saved results and hashes without downloading or executing upstream source.

PDF authoring helpers additionally require ReportLab in an authoring environment. They are not needed to run or evaluate the app. Presentation editing requires a separate authoring environment. PDF/PPT outputs are supplied ready to inspect. Optional Docker material is included but was not built during the final audit.

## Privacy and deployment

Normal source review uses local processes; offline policies and encrypted host storage must still be confirmed. Loopback HTTP is not transport encryption. Reports and SQLite can contain source excerpts. Use an approved encrypted host/network and do not expose ports, tunnels or recording content publicly. Enterprise IAM, application encryption, certified analysis and hardware validation are outside the demonstrated pilot.
