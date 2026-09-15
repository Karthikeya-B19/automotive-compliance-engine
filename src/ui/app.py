from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_URL = "http://localhost:8000/api/v1/review"

st.set_page_config(
    page_title="Secure Code Review Assistant",
    page_icon="🛡️",
    layout="wide",
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


st.title("Secure Code Debugging and Review Assistant")
st.caption("Offline-only automotive secure code review for engineering teams.")

with st.container():
    st.markdown(
        """
        This local review assistant checks source code against retrieved automotive coding standards and evidence-based secure coding guidance.
        It never sends source code to external services.
        """
    )

code_snippet = st.text_area(
    "Code Snippet",
    height=260,
    placeholder="Paste C or embedded code here...",
)
compiler_warnings = st.text_area(
    "Compiler / Static Analysis Warnings (optional)",
    height=120,
    placeholder="Optional warnings or diagnostics...",
)

run_review = st.button("Run Secure Review", type="primary")

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

                st.subheader("Executive Summary")
                st.markdown(f"**{result.get('review_summary', 'No summary available.')}**")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence", result.get("confidence", "unknown"))
                with col2:
                    st.metric("Rule Reference", result.get("rule_reference", "N/A"))
                with col3:
                    st.metric("Sources", str(len(result.get("source_evidence", []))))

                st.subheader("Candidate Root Causes")
                causes = result.get("candidate_root_causes") or ["No candidate root causes were identified from retrieved evidence."]
                for cause in causes:
                    st.markdown(f"- {cause}")

                st.subheader("Suggested Remediation")
                st.markdown(result.get("suggested_remediation", "No remediation guidance available."))

                st.subheader("Evidence and Rule Citations")
                evidence = result.get("source_evidence") or ["No source evidence was returned."]
                for idx, item in enumerate(evidence, start=1):
                    with st.expander(f"Evidence {idx}"):
                        st.markdown(item)

                retrieved_context = result.get("retrieved_context")
                if retrieved_context:
                    st.subheader("Retrieved Standards Context")
                    for item in retrieved_context:
                        with st.expander(f"{item.get('source', 'Unknown source')} / chunk {item.get('chunk_index', 0)}"):
                            st.code(item.get("content", ""), language="text")
