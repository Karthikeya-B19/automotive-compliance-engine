# 7-Minute Demonstration Script

Artifact: `CB.AI.U4AID23109_VideoScript_v1.3`

Student: Karthikeya Bellapukonda — CB.AI.U4AID23109  
Project: Automotive Secure Code Debugging and Review Assistant — Case Study 4

## Before recording

- Record the same submitted version.
- Start the API/UI with `python run.py` or Docker Compose.
- Keep `demo/CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip` and `demo/compiler_warnings.txt` ready.
- Use repository ID `automotive-ecu-demo`; `run.py` supplies the temporary authenticated session key to the UI.
- If Ollama and the approved local index are available, demonstrate RAG mode. Otherwise explicitly demonstrate and explain deterministic fallback.
- Do not claim MISRA compliance; the included standard sample is synthetic.

## Timeline and narration

### 0:00–0:40 — Problem and boundary

“Automotive teams need faster C/C++ review, but proprietary source should not be sent to a public AI service. This project runs locally, grounds standard guidance in approved evidence, and keeps a human reviewer in control.”

Show the title slide and identify yourself, the university, register number and Case Study 4.

### 0:40–1:25 — Architecture

Show the architecture slide. Explain Streamlit, FastAPI, deterministic preflight, ChromaDB, local Ollama and SQLite. Emphasize that source bodies are not stored in SQLite and embeddings are local-only.

### 1:25–2:10 — Inputs and knowledge base

Open the Repository ZIP review page. Point out:

- bounded repository ZIP input;
- all-file C/C++ scanning, repository tree and include-dependency mapping;
- compiler/static-analysis warnings;
- build/runtime evidence;
- approved local standards index.

Point out the authenticated identity, repository ID and verified path permission before starting the analysis.

Explain that all repository content is treated as untrusted data.

### 2:10–3:40 — Live review

Upload `CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip` and `CB.AI.U4AID23109_CompilerWarnings_v1.0.txt`. Click Analyze repository.

Walk through the output:

- executive summary and review mode;
- confidence;
- function/source inventory;
- module count, internal dependency edges, repository tree and ignored vendor file;
- authorization status, complexity estimate, dynamic-allocation observation and parsed SARIF evidence;
- grounded rule reference or honest no-rule response;
- null-pointer, unbounded-copy and resource-leak candidates;
- exact file/function/line evidence and recommendations.

### 3:40–4:30 — Human disposition

Scroll to Human review disposition. Explain that the model cannot approve code. Describe Accepted, Needs changes and Rejected, then record a demo disposition with a concise validation note if desired.

### 4:30–5:20 — History and auditability

Open Review history & metrics. Show total reviews, pending/completed counts and a stored review. Explain that input hashes and generated output are stored, while source bodies are excluded.

### 5:20–6:10 — Evaluation evidence

Open the evaluation JSON/CSV and test log. State:

“Fifteen automated tests pass. They include authentication, path authorization, SARIF parsing and performance observations. Five targeted defect cases pass within this narrow benchmark, and the repository evaluation confirms three scanned source files, two internal dependencies, four findings, and safe exclusion of the vendor directory. This does not establish production accuracy or MISRA compliance.”

### 6:10–7:00 — Responsible AI and next steps

Summarize safe ZIP handling, local-only loading, citation validation, prompt boundaries, deterministic fallback and human oversight. Explain that SARIF parsing and the CI severity gate already work in the pilot. Close with the roadmap: Clang AST and data-flow analysis, provider-native authenticated Git checkout, OIDC/RBAC, encryption, a larger labeled benchmark and controlled rollout.

## Video fallback checklist

- Export MP4 at 1080p if possible.
- Confirm audio is clear and source text is readable.
- Keep duration between 5 and 10 minutes.
- Name the file `CB.AI.U4AID23109_Demo_v1.0.mp4`.
- Play the first and last 20 seconds before submission.
