# Evaluation Guide

## One-sentence pitch

This project is a local-first, repository-scale automotive C/C++ review workflow that safely maps an uploaded ZIP, combines deterministic safety checks with evidence-grounded AI, and requires an auditable human decision.

## Recommended live flow

1. Start with the confidentiality problem: public AI can expose proprietary ECU source.
2. Show the architecture diagram in the README.
3. Upload `demo/CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip` and its warning file.
4. Show the repository tree, scanned modules, internal dependencies, ignored vendor path, and archive safety boundary.
5. Explain the difference between all-file deterministic findings and bounded RAG guidance; show file, function, line, evidence, severity, CWE mapping, confidence, and remediation.
6. Emphasize that the system refuses unsupported rule citations and labels degraded mode.
7. Download the structured JSON report.
8. Record a human disposition and show the audit history/metrics tab.
9. Close with the production roadmap: Clang AST/data flow, provider-native Git checkout, enterprise OIDC/RBAC, encrypted storage, and larger benchmark evaluation. Repository/path authorization, structured SARIF and a CI gate are implemented in the pilot.

## Likely evaluator questions

**Why use both deterministic rules and an LLM?**

Deterministic rules give reproducible high-signal checks and exact locations. The LLM explains context and retrieves approved guidance. Neither is treated as autonomous approval.

**How do you prevent hallucinated MISRA rules?**

The model can only cite retrieved local context. The orchestrator verifies that the returned reference exists in that context; otherwise it forces `No applicable rule found` and low confidence.

**What happens if Ollama is down?**

The app returns a labeled deterministic fallback report and does not invent evidence. This keeps the demo and core preflight useful while making the limitation visible.

**Is source code stored?**

The workflow database stores a SHA-256 hash and the generated report, not the submitted source body. Source remains in process memory for the review request.

**Does it really review a repository?**

Yes. The repository endpoint validates a ZIP without extracting or executing it, scans every supported C/C++ file within bounded limits, builds module and include-dependency maps, and reports path-specific findings. Only the optional contextual RAG step is deliberately bounded.

**Is this MISRA compliant?**

No compliance claim is made. It is review assistance and must be used with licensed standards, compilation, tests, certified tools, and qualified reviewers.

**How would this scale to a company?**

Connect the pilot’s authentication, repository/path permission, SARIF and CI controls to enterprise identity, provider-native Git permissions, project-isolated collections, encrypted storage, production observability, and benchmark gates.

## Final pre-presentation checklist

- Ollama service running and `llama3.1` available.
- Standards PDF indexed successfully.
- `python -m pytest -q -p no:cacheprovider` passes.
- Dashboard and API docs open in separate tabs.
- Demo repository ZIP and warnings ready.
- A fallback explanation ready if the local model is slow.
- Never describe the synthetic MISRA-style PDF as the official MISRA standard.
