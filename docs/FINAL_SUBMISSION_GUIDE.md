# Individual capstone submission - release 3.0

Karthikeya Bellapukonda, CB.AI.U4AID23109, Amrita Vishwa Vidyapeetham. Digital Track, TechPulse, Case Study 4: Secure Code Debugging and Review Assistant. Prepared 16 October 2026.

## Readiness

Technical packaging and automated checks are recorded in the submission manifest and verification report. The package must not be represented as administratively complete until the student supplies faculty approval, signs both declarations and records the submitted version. The supplied October 7 video is clearly historical. No official approval or personal signature has been invented.

## Folder contents

| Folder | What to inspect |
| --- | --- |
| Synopsis | Current synopsis with an uncompleted faculty approval record |
| Input_Data | Synthetic demo ZIPs, actual ECU baseline/mutant fixtures and input catalog |
| Code | Runnable source, tests, canonical evidence, configuration and source documentation |
| Model_Prompts_Config | Model/configuration details, prompt guardrails and synthetic advisory corpus |
| Evaluation_Results | Register-prefixed metric/audit records and a complete raw-evidence ZIP |
| Documentation | Current technical report PDF/source, user and RAG guides, rubric map and presentations |
| Video | Historical recording, provenance/review note and updated recording script |
| Declarations | Separate integrity and AI-use forms for student review/signature, plus third-party notice |

Evaluator-facing artifacts use the register-number, descriptive artifact and version convention. Native Python, package, CI, Docker, source-fixture and canonical machine-readable filenames inside Code and archive payloads retain their required functional names. Renaming importable modules or fixed runtime paths would break the code. This source-layout exception is explicit in the manifest. Input ZIP fixtures retain upstream filenames and license notices internally.

## What it does and how to use it

The assistant reviews embedded C/C++ snippets and repository ZIPs, shows located review candidates, maps includes, retrieves advisory guidance and records human decisions. It is local engineering decision support, not certified automotive analysis.

From the Code folder on a machine with Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Open the Dashboard URL printed by the launcher and select uploaded-repository. Upload a supported C/C++ ZIP from Input_Data, select optional local grounding, and run the review. Inspect findings, excerpts, assumptions and retrieval scores; download JSON and record a human decision. The normal limits are 8 MB compressed ZIP, 300 supported files, 256 KB per source and 2 MB expanded source. No uploaded repository code executes.

For actual local generation, Ollama must run with llama3.1 installed. The all-MiniLM-L6-v2 sentence transformer must be cached locally for dense retrieval. Download/stage approved models before an offline demonstration. Missing models cause labelled fallback modes, not a claim that generation ran. Weights are excluded from this package. Code/docs/MODEL_CONFIG.md explains the active implementation.

For proof, start with the RAG proof presentation and its speaker notes, then the accompanying RAG guide. The current report includes architecture/workflow, dataset quality/duplicates, evaluation, ethics and rubric boundaries. Evaluation_Results holds evaluator-facing summaries. Canonical raw records also live in Code/Evaluation_Results for the app's Verification lab and reproducible scripts.

The maintained source repository is https://github.com/Karthikeya-B19/automotive-compliance-engine. Private recordings, signatures and final ZIP copies are kept local rather than published to the public repository.
