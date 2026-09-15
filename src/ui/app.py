from __future__ import annotations

import json
import html
from typing import Any, Dict, Optional

import requests
import streamlit as st

API_URL = "http://localhost:8000/api/v1/review"

st.set_page_config(
    page_title="Automotive Compliance Review",
    page_icon="A",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #102433;
        --ink: #182b36;
        --line: #d9e2e5;
        --paper: #f7faf9;
        --accent: #d77742;
        --accent-dark: #a94e26;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container { max-width: 1500px; padding: 2.5rem 3rem 4rem; }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3,
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    label { color: #1f2937 !important; }
    .hero {
        background: var(--navy);
        border-left: 8px solid var(--accent);
        color: #f5f8f7;
        padding: 1.6rem 2rem;
        margin-bottom: 1.5rem;
    }
    .hero h1 { margin: 0; font-size: 2rem; letter-spacing: 0; }
    .hero p { color: #c7d5d8; margin: .45rem 0 0; }
    .hero h1 { color: #f5f8f7 !important; }
    .hero p { color: #c7d5d8 !important; }
    [data-testid="stFileUploader"] {
        border: 1px dashed #afc0c4;
        background: #eef4f2;
        padding: .35rem;
    }
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--line);
        padding: .75rem;
    }
    .section-label {
        color: var(--accent-dark);
        font-size: .75rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        margin: .25rem 0 .5rem;
    }
    .rule-reference {
        background: #e8f0f2;
        border-left: 4px solid var(--accent);
        color: #1f2937;
        padding: .9rem 1rem;
        overflow-wrap: anywhere;
        white-space: normal;
    }
    .rule-reference strong { color: #1f2937; display: block; margin-bottom: .25rem; }
    [data-testid="stDownloadButton"] button {
        background: var(--navy);
        border-color: var(--navy);
        color: #ffffff !important;
    }
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button span { color: #ffffff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def submit_review(code_snippet: str, compiler_warnings: Optional[str]) -> Dict[str, Any]:
    payload = {
        "code_snippet": code_snippet,
        "compiler_warnings": (
            [warning.strip() for warning in compiler_warnings.splitlines() if warning.strip()]
            if compiler_warnings
            else []
        ),
    }

    response = requests.post(API_URL, json=payload, timeout=120)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"detail": response.text}
        raise RuntimeError(detail.get("detail", "Backend request failed."))

    return response.json()


st.markdown(
    """
    <div class="hero">
        <h1>Automotive Compliance Review</h1>
        <p>Evidence-bound secure code analysis for embedded engineering teams.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="section-label">Review Input</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Load source file",
        type=["c", "cpp", "h"],
        help="Upload a C, C++, or header file to populate the editor.",
    )
    uploaded_code = ""
    if uploaded_file is not None:
        try:
            uploaded_code = uploaded_file.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            st.error("The uploaded file is not valid UTF-8 text.")

    code_snippet = st.text_area(
        "Code Snippet",
        value=uploaded_code,
        height=330,
        placeholder="Paste C or embedded code here...",
    )
    compiler_warnings = st.text_area(
        "Compiler / Static Analysis Warnings",
        height=120,
        placeholder="Optional warnings or diagnostics, one per line...",
    )
    run_review = st.button("Run Secure Review", type="primary", use_container_width=True)

with col2:
    st.markdown('<div class="section-label">Code Preview</div>', unsafe_allow_html=True)
    st.code(code_snippet or "No source loaded.", language="c")

    if run_review:
        if not code_snippet.strip():
            st.error("Please provide a code snippet before running the review.")
        else:
            with st.spinner("Running local secure review..."):
                try:
                    result = submit_review(code_snippet, compiler_warnings)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Unable to connect to the local review API: {exc}")
                except RuntimeError as exc:
                    st.error(str(exc))
                else:
                    st.success("Review completed successfully.")
                    st.markdown('<div class="section-label">Review Result</div>', unsafe_allow_html=True)
                    st.subheader("Executive Summary")
                    st.write(result.get("review_summary", "No summary available."))

                    st.metric("Confidence", result.get("confidence", "unknown"))
                    rule_reference = html.escape(str(result.get("rule_reference", "N/A")))
                    st.markdown(
                        f'<div class="rule-reference"><strong>Rule Reference</strong>{rule_reference}</div>',
                        unsafe_allow_html=True,
                    )

                    st.subheader("Suggested Remediation")
                    st.write(result.get("suggested_remediation", "No remediation guidance available."))

                    st.subheader("Candidate Root Causes")
                    causes = result.get("candidate_root_causes") or [
                        "No candidate root causes were identified from retrieved evidence."
                    ]
                    for cause in causes:
                        st.markdown(f"- {cause}")

                    with st.expander("Source Evidence"):
                        evidence = result.get("source_evidence") or ["No source evidence was returned."]
                        for item in evidence:
                            st.markdown(item)

                    retrieved_context = result.get("retrieved_context")
                    if retrieved_context:
                        with st.expander("Retrieved Standards Context"):
                            for item in retrieved_context:
                                st.markdown(
                                    f"**{item.get('source', 'Unknown source')} / chunk "
                                    f"{item.get('chunk_index', 0)}**"
                                )
                                st.code(item.get("content", ""), language="text")

                    st.download_button(
                        "Download Compliance Report",
                        data=json.dumps(result, indent=2),
                        file_name="compliance_report.json",
                        mime="application/json",
                        use_container_width=True,
                    )
