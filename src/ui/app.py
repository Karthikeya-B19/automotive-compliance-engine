from __future__ import annotations

import base64
import html
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("REVIEW_API_URL", "http://localhost:8000/api/v1/review")
API_BASE_URL = API_URL.rsplit("/", 1)[0]
API_KEY = os.getenv("REVIEW_API_KEY", "")

st.set_page_config(
    page_title="Automotive Compliance Review",
    page_icon="🛡️",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
      --navy:#102b32; --ink:#182e35; --muted:#52676e; --line:#d6e2e4;
      --paper:#f4f7f8; --surface:#ffffff; --surface-muted:#e9f1f2;
      --accent:#087f75; --accent-hover:#075e58; --on-dark:#f7fbfb;
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      background:var(--paper) !important; color:var(--ink) !important;
    }
    .block-container { max-width:1480px; padding:2.25rem 3rem 4rem; }
    [data-testid="stSidebar"] { background:#eaf0f2; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] h2 { font-size:1.3rem; letter-spacing:-.04em; }
    h1,h2,h3 { letter-spacing:-.035em; }
    [data-baseweb="tab-list"] { gap:2rem; margin-bottom:1.2rem; }
    button[data-baseweb="tab"] { font-size:.92rem; padding-bottom:1rem; }
    [data-testid="stFileUploader"] { border:1px solid var(--line); border-radius:12px; padding:.7rem; background:white; }
    [data-testid="stMetric"] { border-radius:12px; box-shadow:0 4px 16px #102b3205; }
    [data-testid="stExpander"] details { border-radius:12px; }
    button { border-radius:8px !important; }
    .eyebrow { color:#93e0d5 !important; font-size:.7rem; font-weight:700; letter-spacing:.15em; text-transform:uppercase; }
    .hero-meta { color:#a9c5cb !important; font-size:.8rem; padding-top:1rem; }
    .empty-state { background:white; border:1px solid var(--line); border-radius:16px; padding:2rem; margin-top:1rem; }
    .empty-state h3 { margin:.3rem 0 1rem; font-size:1.35rem; }
    [data-testid="stHeader"] { background:transparent; }
    h1,h2,h3,[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,label { color:#1f2937 !important; }
    p, span, small, [data-testid="stCaptionContainer"], [data-testid="stText"] {
      color:var(--ink);
    }
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div, [data-baseweb="base-input"],
    input, textarea {
      background:var(--surface) !important; color:var(--ink) !important;
      border-color:#9fb1b7 !important;
    }
    input::placeholder, textarea::placeholder { color:#61747c !important; opacity:1; }
    [data-baseweb="tab-list"] { border-bottom-color:var(--line) !important; }
    button[data-baseweb="tab"] { color:var(--ink) !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
      color:var(--accent) !important; border-bottom-color:var(--accent) !important;
    }
    [data-testid="stMetric"] { background:var(--surface) !important; border:1px solid var(--line); padding:.65rem; }
    [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"],
    [data-testid="stMetricDelta"] { color:var(--ink) !important; }
    [data-testid="stDataFrame"], [data-testid="stDataFrame"] * { color:var(--ink); }
    [data-testid="stDataFrame"] { background:var(--surface); }
    [data-testid="stExpander"] details { background:var(--surface); border-color:var(--line); }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary span { color:var(--ink) !important; }
    [data-testid="stAlert"] { color:var(--ink) !important; }
    [data-testid="stAlert"] * { color:var(--ink) !important; }
    button[kind="primary"], [data-testid="stDownloadButton"] button {
      background:var(--navy) !important; color:var(--on-dark) !important;
    }
    button[kind="primary"] *, [data-testid="stDownloadButton"] button * {
      color:var(--on-dark) !important;
    }
    button[kind="primary"]:hover, [data-testid="stDownloadButton"] button:hover {
      background:var(--accent-hover) !important; color:var(--on-dark) !important;
    }
    button[kind="secondary"] { background:var(--surface) !important; color:var(--ink) !important; border-color:#9fb1b7 !important; }
    button[kind="secondary"] * { color:var(--ink) !important; }
    .hero { background:linear-gradient(110deg,#102b32,#164b50); border:1px solid #246067; color:#f5f8f7;
            border-radius:18px; padding:2rem 2.4rem; margin-bottom:1.2rem; }
    .hero h1 { margin:.5rem 0; font-size:2.65rem; font-weight:650; color:#f5f8f7 !important; }
    .hero p { color:#c7d5d8 !important; margin:.45rem 0 0; }
    .badge { display:inline-block; padding:.2rem .55rem; margin-right:.35rem; border-radius:3px;
             background:#e8f0f2; color:#18364a; font-size:.78rem; font-weight:700; }
    .section-label { color:#087f75; font-size:.75rem; font-weight:700; letter-spacing:.08em;
                     text-transform:uppercase; margin:.25rem 0 .5rem; }
    .rule-reference { background:#e8f0f2; border-left:4px solid var(--accent); color:#1f2937;
                      padding:.9rem 1rem; overflow-wrap:anywhere; }
    .finding { background:white; border:1px solid var(--line); border-left:4px solid var(--accent);
               border-radius:10px; padding:1.2rem 1.4rem; margin:.75rem 0; }
    .finding.critical, .finding.high { border-left-color:#b83645; }
    .finding.medium { border-left-color:#b36b19; }
    .finding code { color:#203840; background:#edf3f4; overflow-wrap:anywhere; }
    ::selection { background:#f3c7b3; color:var(--navy); }
    </style>
    """,
    unsafe_allow_html=True,
)


def _headers() -> Dict[str, str]:
    return {"X-API-Key": API_KEY} if API_KEY else {}


def _error_detail(response: requests.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail", body))
    except ValueError:
        return response.text or "Backend request failed."


def submit_review(
    code_snippet: str,
    file_name: str,
    compiler_warnings: Optional[str],
    build_logs: str,
    related_files: list[Dict[str, str]],
) -> Dict[str, Any]:
    payload = {
        "code_snippet": code_snippet,
        "file_name": file_name,
        "compiler_warnings": [
            warning.strip()
            for warning in (compiler_warnings or "").splitlines()
            if warning.strip()
        ],
        "build_logs": build_logs,
        "related_files": related_files,
    }
    response = requests.post(API_URL, json=payload, headers=_headers(), timeout=180)
    if response.status_code >= 400:
        raise RuntimeError(_error_detail(response))
    return response.json()


def submit_repository_review(
    archive_bytes: bytes,
    archive_name: str,
    repository_id: str,
    compiler_warnings: Optional[str],
    build_logs: str,
    evidence_format: str,
    use_rag: bool,
) -> Dict[str, Any]:
    payload = {
        "repository_id": repository_id,
        "archive_name": archive_name,
        "archive_base64": base64.b64encode(archive_bytes).decode("ascii"),
        "compiler_warnings": [
            warning.strip()
            for warning in (compiler_warnings or "").splitlines()
            if warning.strip()
        ],
        "build_logs": build_logs,
        "evidence_format": evidence_format,
        "use_rag": use_rag,
    }
    response = requests.post(
        f"{API_BASE_URL}/repository-review",
        json=payload,
        headers=_headers(),
        timeout=240,
    )
    if response.status_code >= 400:
        raise RuntimeError(_error_detail(response))
    return response.json()


def api_get(path: str) -> Dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=_headers(), timeout=15)
    if response.status_code >= 400:
        raise RuntimeError(_error_detail(response))
    return response.json()


def save_disposition(review_id: str, status: str, reviewer: str, notes: str) -> None:
    response = requests.patch(
        f"{API_BASE_URL}/reviews/{review_id}/disposition",
        json={"status": status, "reviewer": reviewer, "notes": notes},
        headers=_headers(),
        timeout=15,
    )
    if response.status_code >= 400:
        raise RuntimeError(_error_detail(response))


def render_review(result: Dict[str, Any]) -> None:
    st.markdown('<div class="section-label">Review result</div>', unsafe_allow_html=True)
    st.subheader("Executive summary")
    st.write(result.get("review_summary", "No summary available."))

    repository_summary = result.get("repository_summary") or {}
    summary = result.get("code_summary") or repository_summary
    metrics = st.columns(6 if repository_summary else 5)
    metrics[0].metric("Confidence", result.get("confidence", "Unknown"))
    if repository_summary:
        metrics[1].metric("Source files", repository_summary.get("source_file_count", 0))
        metrics[2].metric("Findings", repository_summary.get("finding_count", 0))
        metrics[3].metric("Functions", repository_summary.get("function_count", 0))
        metrics[4].metric("Source lines", repository_summary.get("total_lines", 0))
        metrics[5].metric("Dependencies", repository_summary.get("dependency_edge_count", 0))
    else:
        metrics[1].metric("Mode", result.get("review_mode", "Unknown"))
        metrics[2].metric("Findings", len(result.get("findings") or []))
        metrics[3].metric("Functions", summary.get("function_count", 0))
        metrics[4].metric("Source lines", summary.get("line_count", 0))

    rule_reference = html.escape(str(result.get("rule_reference", "N/A")))
    st.markdown(
        f'<div class="rule-reference"><strong>Grounded rule reference</strong><br>{rule_reference}</div>',
        unsafe_allow_html=True,
    )

    if repository_summary:
        st.subheader("Repository map")
        left, right = st.columns([1, 2])
        with left:
            tree = result.get("repository_tree") or ["No repository tree available."]
            st.code("\n".join(tree), language=None)
        with right:
            module_rows = [
                {
                    "Path": item.get("path"),
                    "Lines": item.get("line_count", 0),
                    "Functions": item.get("function_count", 0),
                    "Branches": item.get("branch_count", 0),
                    "Loops": item.get("loop_count", 0),
                    "Findings": item.get("finding_count", 0),
                    "Complexity": item.get("complexity_estimate", 0),
                    "Includes": ", ".join(item.get("quoted_includes") or []),
                }
                for item in (result.get("modules") or [])
            ]
            st.dataframe(pd.DataFrame(module_rows), use_container_width=True, hide_index=True)
        if result.get("dependency_edges"):
            with st.expander("Internal include dependencies"):
                st.dataframe(
                    pd.DataFrame(result["dependency_edges"]),
                    use_container_width=True,
                    hide_index=True,
                )
        authorization = result.get("authorization") or {}
        if authorization:
            st.caption(
                f"Authenticated user: {authorization.get('authenticated_user')} · "
                f"Repository: {authorization.get('repository_id')} · "
                f"Permission policy verified: {authorization.get('permission_verified')}"
            )
        if result.get("performance_observations"):
            with st.expander("Performance and complexity observations"):
                st.dataframe(
                    pd.DataFrame(result["performance_observations"]),
                    use_container_width=True,
                    hide_index=True,
                )
        if result.get("parsed_evidence"):
            with st.expander("Parsed static-analysis evidence"):
                st.json(result["parsed_evidence"])
        if result.get("skipped_files"):
            with st.expander(f"Skipped files ({len(result['skipped_files'])})"):
                st.dataframe(
                    pd.DataFrame(result["skipped_files"]),
                    use_container_width=True,
                    hide_index=True,
                )

    findings = result.get("findings") or []
    st.subheader("Structured findings")
    if not findings:
        st.success("No deterministic preflight candidates were detected. This is not proof of compliance.")
    if findings:
        filter_cols = st.columns([1, 1, 2])
        selected_severity = filter_cols[0].multiselect('Severity', ['Critical', 'High', 'Medium', 'Low'], key=f"severity_{result.get('review_id')}")
        selected_categories = filter_cols[1].multiselect('Category', sorted({f.get('category', 'General') for f in findings}), key=f"category_{result.get('review_id')}")
        search = filter_cols[2].text_input('Find in results', placeholder='File, rule, evidence or title', key=f"search_{result.get('review_id')}")
        findings = [f for f in findings if (not selected_severity or f.get('severity') in selected_severity)
                    and (not selected_categories or f.get('category') in selected_categories)
                    and (not search or search.casefold() in json.dumps(f).casefold())]
        st.caption(f'{len(findings):,} matching candidates. Full evidence is available in the JSON download.')
        page = st.number_input('Results page', min_value=1, max_value=max(1, (len(findings)+19)//20), value=1, key=f"page_{result.get('review_id')}")
        findings = findings[(page-1)*20:page*20]
    for finding in findings:
        title = html.escape(str(finding.get("title", "Finding")))
        severity = html.escape(str(finding.get("severity", "Unknown")))
        category = html.escape(str(finding.get("category", "General")))
        location = f"{finding.get('file', result.get('file_name', 'source'))}:{finding.get('line', '?')}"
        function = finding.get("function") or "module scope"
        evidence = html.escape(str(finding.get("evidence", "")))
        remediation = html.escape(str(finding.get("recommendation", "")))
        cwe = html.escape(str(finding.get("cwe") or "No CWE mapping"))
        st.markdown(
            f"""
            <div class="finding {severity.lower()}">
              <span class="badge">{severity}</span><span class="badge">{category}</span><span class="badge">{cwe}</span>
              <h4>{title}</h4>
              <p><strong>Location:</strong> {html.escape(location)} · {html.escape(str(function))}</p>
              <p><strong>Evidence:</strong> <code>{evidence}</code></p>
              <p><strong>Recommended action:</strong> {remediation}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        grounding = finding.get('grounding') or {}
        if grounding.get('rule_id'):
            with st.expander(f"Retrieved guidance: {grounding['rule_id']}"):
                st.write(grounding['excerpt'])
                st.caption(grounding['authority'])
                for assumption in grounding.get('assumptions', []): st.write(f'Assumption: {assumption}')
                st.code(grounding['content_sha256'], language=None)

    retrieval = result.get('retrieval_trace') or {}
    if retrieval:
        st.subheader('Retrieval evidence')
        proof_cols = st.columns(3)
        proof_cols[0].metric('Advisory rules indexed', retrieval.get('corpus_rule_count', 0))
        proof_cols[1].metric('Supported candidates', retrieval.get('supported_count', 0))
        proof_cols[2].metric('Abstained candidates', retrieval.get('abstained_count', 0))
        st.caption('Support means the retrieved guidance applies to a candidate. Human review still determines whether the code has a real defect.')
        with st.expander('Inspect queries, scores and citation decisions'):
            for trace in retrieval.get('per_finding', [])[:50]:
                st.write(f"{trace['expected_rule_id'] or 'Unknown rule'}: {trace['decision']} ({trace['strategy']})")
                st.caption(trace['query'])
                st.dataframe(pd.DataFrame([{'Rule': c['rule_id'], 'Lexical': c['lexical_score'], 'Dense': c['dense_score'], 'RRF': c['fusion_score']} for c in trace['candidates']]), hide_index=True, use_container_width=True)
            if result.get('citation_validation'): st.json(result['citation_validation'])

    left, right = st.columns(2)
    with left:
        st.subheader("Candidate root causes")
        causes = result.get("candidate_root_causes") or ["No candidate root cause was identified."]
        for cause in causes:
            st.markdown(f"- {cause}")
    with right:
        st.subheader("Suggested remediation")
        st.write(result.get("suggested_remediation", "No remediation guidance available."))

    with st.expander("Evidence, code inventory, and limitations"):
        if result.get("analysis_summary"):
            st.markdown(f"**Verification summary:** {result['analysis_summary']}")
        for evidence in result.get("source_evidence") or ["No grounded standard excerpt was returned."]:
            st.markdown(f"- {evidence}")
        functions = summary.get("functions") or []
        if functions:
            st.markdown("**Function inventory**")
            st.dataframe(pd.DataFrame(functions), use_container_width=True, hide_index=True)
        for limitation in result.get("limitations") or []:
            st.warning(limitation)

    st.download_button(
        "Download structured compliance report",
        data=json.dumps(result, indent=2),
        file_name=f"review_{result.get('review_id', 'report')}.json",
        mime="application/json",
        use_container_width=True,
    )

    st.subheader("Human review disposition")
    with st.form(f"disposition_{result.get('review_id', 'new')}"):
        disposition = st.selectbox("Decision", ["Accepted", "Needs changes", "Rejected"])
        reviewer = st.text_input("Reviewer name", placeholder="Required for the audit trail")
        notes = st.text_area("Reviewer notes", placeholder="Validation performed, rationale, follow-up work...")
        submitted = st.form_submit_button("Record disposition", use_container_width=True)
        if submitted:
            if len(reviewer.strip()) < 2:
                st.error("Enter the reviewer name before recording the decision.")
            else:
                try:
                    save_disposition(result["review_id"], disposition, reviewer, notes)
                except (requests.RequestException, RuntimeError) as exc:
                    st.error(f"Could not save disposition: {exc}")
                else:
                    st.success("Disposition recorded in the local audit database.")


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Automotive engineering / Review workspace</div>
      <h1>Confidence starts with evidence.</h1>
      <p>Inspect embedded C/C++ repositories. Trace every candidate to its source and advisory guidance.</p>
      <div class="hero-meta">LOCAL PROCESSING &nbsp; / &nbsp; TRACEABLE RETRIEVAL &nbsp; / &nbsp; HUMAN REVIEW</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Decision-support pilot · source code is processed locally · no automatic merge or release approval · "
    "validate every result with compilation, tests, certified tools, and a qualified reviewer."
)

with st.sidebar:
    st.markdown('## ECU Review Studio')
    st.caption('Digital Track / Case Study 04')
    st.divider()
    st.markdown('**Review scope**')
    st.write('C / C++ source')
    st.write('Classical CAN and embedded heuristics')
    st.write('20 synthetic advisory rules')
    st.divider()
    st.markdown('**Evidence matters**')
    st.caption('Every supported finding exposes its retrieved excerpt, rule identity, assumptions and content hash.')
    st.caption('Open Verification lab to inspect measured benchmark and RAG results.')
    st.divider()
    st.caption('Karthikeya Bellapukonda\n\nAmrita Vishwa Vidyapeetham')

repository_tab, review_tab, history_tab, proof_tab = st.tabs(
    ["Repository ZIP review", "Single-file review", "Review history & metrics", "Verification lab"]
)

with repository_tab:
    st.markdown('<div class="section-label">Repository input</div>', unsafe_allow_html=True)
    repo_left, repo_right = st.columns([1, 1])
    with repo_left:
        repository_id = st.selectbox(
            "Authorized repository ID",
            options=['uploaded-repository', 'automotive-ecu-demo', 'clean-speed-monitor', 'mixed-sensor-network'],
            help="This ID is checked against the optional repository permission policy.",
        )
        repository_archive = st.file_uploader(
            "Upload a C/C++ repository ZIP",
            type=["zip"],
            key="repository_zip",
            help="Maximum 8 MB compressed, 300 supported source files and 2 MB expanded C/C++ text.",
        )
        repo_warnings = st.text_area(
            "Repository compiler / static-analysis warnings",
            height=120,
            key="repository_warnings",
            placeholder="Optional diagnostics, one per line...",
        )
        repo_evidence = st.file_uploader(
            "Attach repository build or runtime evidence",
            type=["txt", "log", "json", "xml", "sarif"],
            key="repository_evidence",
        )
        repo_build_logs = ""
        repo_evidence_format = "text"
        if repo_evidence is not None:
            try:
                repo_build_logs = repo_evidence.getvalue().decode("utf-8")[:20000]
                repo_evidence_format = "sarif" if repo_evidence.name.lower().endswith(".sarif") else "text"
                st.caption(f"Loaded {len(repo_build_logs):,} characters from {repo_evidence.name}.")
            except UnicodeDecodeError:
                st.error("The repository evidence file must be UTF-8 text.")
        use_repository_rag = st.checkbox(
            "Ground the highest-risk module with the local standards index and Ollama",
            value=True,
        )
        run_repository_review = st.button(
            "Analyze repository",
            type="primary",
            use_container_width=True,
            key="run_repository_review",
        )
    with repo_right:
        st.markdown('<div class="empty-state"><div class="section-label">Repository intelligence</div><h3>A clear view of your codebase</h3><p>Module inventory, include dependencies, severity-ranked candidates and inspectable retrieval evidence in one review.</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Safe archive boundary</div>', unsafe_allow_html=True)
        st.markdown(
            "The service reads the ZIP in memory and never executes repository content. "
            "It rejects traversal paths, symbolic links, encrypted entries, duplicate paths, oversized files, "
            "and suspicious compression ratios. Build, vendor, generated, external, and tooling directories are ignored."
        )
        if repository_archive is not None:
            st.metric("Archive size", f"{len(repository_archive.getvalue()) / 1024:.1f} KB")
            st.write(f"Selected repository: `{repository_archive.name}`")

    if run_repository_review:
        if repository_archive is None:
            st.error("Upload a repository ZIP before starting the review.")
        else:
            with st.spinner("Mapping modules, dependencies, control flow, and candidate defects..."):
                try:
                    st.session_state["last_repository_review"] = submit_repository_review(
                        repository_archive.getvalue(),
                        repository_archive.name,
                        repository_id.strip(),
                        repo_warnings,
                        repo_build_logs,
                        repo_evidence_format,
                        use_repository_rag,
                    )
                except requests.RequestException as exc:
                    st.error(f"Unable to connect to the local review API: {exc}")
                except RuntimeError as exc:
                    st.error(str(exc))

    if st.session_state.get("last_repository_review"):
        render_review(st.session_state["last_repository_review"])

with review_tab:
    input_col, preview_col = st.columns([1, 1])
    with input_col:
        st.markdown('<div class="section-label">Review input</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Load C/C++ source", type=["c", "cc", "cpp", "cxx", "h", "hpp"])
        uploaded_code = ""
        source_name = "pasted_snippet.c"
        if uploaded_file is not None:
            source_name = uploaded_file.name
            try:
                uploaded_code = uploaded_file.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                st.error("The source file must be UTF-8 text.")

        code_snippet = st.text_area(
            "Code snippet",
            value=uploaded_code,
            height=330,
            placeholder="Paste embedded C or C++ code here...",
        )
        compiler_warnings = st.text_area(
            "Compiler / static-analysis warnings",
            height=100,
            placeholder="Optional diagnostics, one per line...",
        )
        evidence_file = st.file_uploader(
            "Attach build or runtime evidence",
            type=["txt", "log", "json", "xml", "sarif"],
        )
        build_logs = ""
        if evidence_file is not None:
            try:
                build_logs = evidence_file.getvalue().decode("utf-8")[:20000]
                st.caption(f"Loaded {len(build_logs):,} characters from {evidence_file.name}.")
            except UnicodeDecodeError:
                st.error("The evidence file must be UTF-8 text.")
        repository_uploads = st.file_uploader(
            "Add authorized related modules",
            type=["c", "cc", "cpp", "cxx", "h", "hpp"],
            accept_multiple_files=True,
            help="Up to 20 related files are supplied as untrusted repository context and are not persisted.",
        )
        related_files = []
        for related in (repository_uploads or [])[:20]:
            try:
                related_files.append(
                    {
                        "file_name": related.name,
                        "content": related.getvalue().decode("utf-8")[:10000],
                    }
                )
            except UnicodeDecodeError:
                st.error(f"Related file {related.name} must be UTF-8 text.")
        run_review = st.button("Run secure review", type="primary", use_container_width=True)

    with preview_col:
        st.markdown('<div class="section-label">Code preview</div>', unsafe_allow_html=True)
        st.code(code_snippet or "No source loaded.", language="c", line_numbers=True)

    if run_review:
        if not code_snippet.strip():
            st.error("Provide a code snippet before running the review.")
        else:
            with st.spinner("Running local preflight and grounded review..."):
                try:
                    st.session_state["last_review"] = submit_review(
                        code_snippet, source_name, compiler_warnings, build_logs, related_files
                    )
                except requests.RequestException as exc:
                    st.error(f"Unable to connect to the local review API: {exc}")
                except RuntimeError as exc:
                    st.error(str(exc))

    if st.session_state.get("last_review"):
        render_review(st.session_state["last_review"])

with history_tab:
    st.markdown('<div class="section-label">Local workflow analytics</div>', unsafe_allow_html=True)
    try:
        metrics = api_get("/metrics")
        history = api_get("/reviews?limit=100").get("reviews", [])
    except (requests.RequestException, RuntimeError) as exc:
        st.info(f"Start the API to load review history and metrics: {exc}")
    else:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Total reviews", metrics.get("total_reviews", 0))
        metric_cols[1].metric("Pending human review", metrics.get("pending_reviews", 0))
        metric_cols[2].metric("Disposition recorded", metrics.get("completed_reviews", 0))
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
        else:
            st.info("No reviews have been recorded yet.")

with proof_tab:
    st.subheader('Measured verification, with inspectable evidence')
    st.write('These results come from saved local runs. Download the underlying records to inspect source hashes, test cases, misses and limitations.')
    root = Path(__file__).resolve().parents[2] / 'Evaluation_Results'
    if not root.exists() and (root.parent.parent / 'Evaluation_Results').exists():
        root = root.parent.parent / 'Evaluation_Results'
    benchmark = root / 'public_benchmark' / 'summary.json'
    if benchmark.exists():
        report = json.loads(benchmark.read_text(encoding='utf-8'))
        cols = st.columns(4)
        for col,label,key in zip(cols,['Public repositories','Source files','Source lines','Scan failures'],['distinct_repositories','files','lines','failed']):
            col.metric(label, f"{report.get(key, 0):,}")
        st.caption('Public convenience sample. Candidates in unlabelled code do not establish detection accuracy.')
    evidence_files = {
        'Public benchmark summary': 'public_benchmark/summary.json',
        'Public repository records': 'public_benchmark/results.json',
        'Retrieval comparison and abstention controls': 'rag_evidence/retrieval_results.json',
        'Actual local LLM review traces': 'rag_evidence/live_generation.json',
        'Real ECU mutation study': 'ecu_mutations/results.json',
        'Component verification matrix': 'component_evidence.json',
    }
    for label,relative in evidence_files.items():
        path = root / relative
        with st.expander(label):
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
                st.json(data.get('summary', data) if isinstance(data, dict) else {'record_count': len(data)})
                st.download_button('Download evidence JSON', path.read_bytes(), file_name=path.name, mime='application/json', key='evidence_'+relative)
            else: st.info('Evidence has not been generated in this installation yet.')
