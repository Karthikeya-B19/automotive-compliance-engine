# Case Study 4 Guideline Traceability

This matrix distinguishes implemented pilot functionality from controls that require an organization’s production infrastructure. No roadmap item is represented as already deployed.

Public implementation repository: `https://github.com/Karthikeya-B19/automotive-compliance-engine`

| Guideline item | Submitted implementation | Verification evidence |
|---|---|---|
| Local/private AI | Ollama, local-only SentenceTransformer loading and local ChromaDB | Deterministic fallback test and runtime configuration |
| Repository-aware retrieval | Safe all-file ZIP scan, module inventory, repository tree and include graph | Repository acceptance evaluation |
| Authentication | `run.py` creates a random per-run API key and authenticated local identity | API rejects missing/invalid key in secure mode |
| Repository permission | Repository ID mapped to authorized path prefixes | Permission test rejects source outside allowlist |
| Compiler/log analysis | Warning and bounded evidence inputs | API tests |
| Static-analysis reports | Structured SARIF 2.1 result extraction with rule, level, message and location | SARIF parser test |
| Defect/root-cause assistance | Deterministic candidates plus optional grounded explanation | Five-case evaluation |
| MISRA-oriented assistance | Approved local PDF retrieval and fail-closed rule-reference validation | Prompt guardrails and fallback behavior |
| Security review | Pointer, boundary, resource and control-flow checks with CWE where applicable | Analyzer tests |
| Performance investigation | Complexity estimates, branch/loop totals and dynamic-allocation observations | Performance-observation test |
| Structured findings | File, function, line, evidence, severity, confidence, recommendation and status | API schema and JSON exports |
| Historical approved findings | Findings from Accepted reviews retrieved as bounded context | ReviewStore `approved_findings` |
| Human approval | Accepted, Rejected and Needs changes disposition with reviewer/notes/events | Workflow test |
| Workflow integration | SQLite record plus CI JSON/SARIF export | Metrics, history and `tools/ci_review.py` |
| CI/CD | Severity-gated CLI and example GitHub Actions SARIF workflow | Local CI command and workflow file |
| Review interface accessibility | Explicit high-contrast light theme for application surfaces, text, inputs, tabs, metrics, alerts, tables and buttons | Theme configuration plus UI style rules; contrast ratios verified for normal, accent, placeholder and button text |
| Prompt-injection boundary | Repository, logs, diagnostics and history delimited as data | Prompt guardrails |
| Source confidentiality | Local processing; source body excluded from database and audit logs | Storage schema and tests |
| Review metrics | Counts, findings, actionable-review rate and average disposition time | `/api/v1/metrics` |
| Automatic merge/release | Deliberately absent | Human disposition remains separate and advisory |
| Certified-tool replacement | Deliberately prohibited | Limitations shown in every report |

## Organization-provided production dependencies

The following cannot be truthfully manufactured by a student artifact and must be supplied by the adopting organization: enterprise IAM/OIDC identities, provider-native Git permissions, licensed MISRA publications, production repositories, encryption keys and managed encrypted storage, firewall/egress policy, certified analyzers, real CI branch-protection rules, historical defect-leakage data, and qualified safety/compliance approvals.
