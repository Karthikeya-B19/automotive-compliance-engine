# TechPulse Case Study 4 — Submission Package

Student: Karthikeya Bellapukonda  
Register number: CB.AI.U4AID23109  
University: Amrita Vishwa Vidyapeetham  
Submission type: Individual  
Project: Automotive Secure Code Debugging and Review Assistant

## Quick start

From the `Code/` directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Open `http://localhost:8501`. For fully grounded RAG mode, pre-stage the approved SentenceTransformer model, start Ollama with the configured model, and use an approved/licensed local standards index. Without those dependencies, the application returns a clearly labeled deterministic fallback.

## Demonstration inputs

Open **Repository ZIP review** and upload one of the three ZIPs in `Input_Data/`:

- `AutomotiveECURepository`: 3 scanned files, 2 internal dependencies, 4 intentional findings and an ignored vendor file.
- `CleanSpeedMonitor`: 2 scanned files, 1 dependency and no target deterministic finding.
- `MixedSensorNetwork`: 3 scanned files, 2 dependencies, 1 boundary finding and an ignored generated file.

Optional compiler warnings and SARIF evidence are also provided. See `Documentation/CB.AI.U4AID23109_UserGuide_v1.4.md` for what the application does and how to use it.

The maintained public source repository is `https://github.com/Karthikeya-B19/automotive-compliance-engine`.

## Mandatory before submission

1. Obtain the faculty signature on page 3 of the synopsis.
2. Review, tick, sign and date the declaration.
3. Record a 5–10 minute video named `CB.AI.U4AID23109_Demo_v1.0.mp4` and place it in `Video/`.
4. Recreate the ZIP after the signed documents and MP4 are added.

The current ZIP is technically complete but intentionally contains unsigned approval/declaration fields and a video placeholder; those personal/official actions cannot be generated on the student’s behalf.
