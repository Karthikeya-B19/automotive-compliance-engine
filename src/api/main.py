from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.analysis.repository_analyzer import RepositoryArchiveError, analyze_repository_zip
from src.analysis.evidence_parser import diagnostics_as_lines, parse_sarif
from src.rag.orchestrator import review_code
from src.storage.review_store import ReviewStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DATABASE = Path(os.getenv("REVIEW_DATABASE", PROJECT_ROOT / "data" / "reviews.db"))
review_store = ReviewStore(REVIEW_DATABASE)

logger = logging.getLogger("secure_code_review_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
    )
    logger.addHandler(handler)


class RelatedSourceFile(BaseModel):
    file_name: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("file_name")
    @classmethod
    def validate_related_file_name(cls, value: str) -> str:
        cleaned = Path(value.strip()).name
        if Path(cleaned).suffix.lower() not in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}:
            raise ValueError("related file must use a supported C/C++ extension")
        return cleaned


class CodeReviewRequest(BaseModel):
    code_snippet: str = Field(
        ..., min_length=1, max_length=20000, description="Source code to review"
    )
    file_name: str = Field(default="pasted_snippet.c", min_length=1, max_length=180)
    compiler_warnings: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional compiler or static analysis warnings",
    )
    build_logs: str = Field(
        default="",
        max_length=20000,
        description="Optional build, static-analysis, or runtime evidence",
    )
    related_files: List[RelatedSourceFile] = Field(
        default_factory=list,
        max_length=20,
        description="Authorized related modules supplied for repository-aware context",
    )
    evidence_format: str = Field(default="text", pattern="^(text|sarif)$")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        cleaned = Path(value.strip()).name
        if not cleaned or cleaned in {".", ".."}:
            raise ValueError("file_name must identify a source file")
        if Path(cleaned).suffix.lower() not in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}:
            raise ValueError("file_name must use a supported C/C++ extension")
        return cleaned

    @field_validator("compiler_warnings")
    @classmethod
    def validate_warnings(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return []
        cleaned = [warning.strip()[:1000] for warning in value if warning and warning.strip()]
        if len(cleaned) > 100:
            raise ValueError("A maximum of 100 warning lines is supported")
        return cleaned


class CodeReviewResponse(BaseModel):
    review_id: str
    created_at: str
    file_name: str
    review_summary: str
    candidate_root_causes: List[str] = Field(default_factory=list)
    suggested_remediation: str
    analysis_summary: str = ""
    rule_reference: str
    source_evidence: List[str] = Field(default_factory=list)
    confidence: str
    review_mode: str
    code_summary: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    retrieved_context: Optional[List[Dict[str, Any]]] = Field(default=None)
    parsed_evidence: Dict[str, Any] = Field(default_factory=dict)


class RepositoryReviewRequest(BaseModel):
    repository_id: str = Field(default="uploaded-repository", min_length=1, max_length=160)
    archive_name: str = Field(min_length=5, max_length=180)
    archive_base64: str = Field(min_length=4, max_length=12_000_000)
    compiler_warnings: Optional[List[str]] = Field(default_factory=list)
    build_logs: str = Field(default="", max_length=20000)
    use_rag: bool = True
    evidence_format: str = Field(default="text", pattern="^(text|sarif)$")

    @field_validator("archive_name")
    @classmethod
    def validate_archive_name(cls, value: str) -> str:
        cleaned = Path(value.strip()).name
        if Path(cleaned).suffix.lower() != ".zip":
            raise ValueError("archive_name must identify a ZIP file")
        return cleaned

    @field_validator("compiler_warnings")
    @classmethod
    def validate_repository_warnings(cls, value: Optional[List[str]]) -> List[str]:
        cleaned = [warning.strip()[:1000] for warning in (value or []) if warning and warning.strip()]
        if len(cleaned) > 100:
            raise ValueError("A maximum of 100 warning lines is supported")
        return cleaned


class RepositoryReviewResponse(BaseModel):
    review_id: str
    created_at: str
    file_name: str
    review_summary: str
    candidate_root_causes: List[str] = Field(default_factory=list)
    suggested_remediation: str
    analysis_summary: str = ""
    rule_reference: str
    source_evidence: List[str] = Field(default_factory=list)
    confidence: str
    review_mode: str
    repository_summary: Dict[str, Any] = Field(default_factory=dict)
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    dependency_edges: List[Dict[str, str]] = Field(default_factory=list)
    unresolved_includes: List[Dict[str, str]] = Field(default_factory=list)
    skipped_files: List[Dict[str, str]] = Field(default_factory=list)
    repository_tree: List[str] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    compiler_warning_count: int = 0
    build_log_chars: int = 0
    parsed_evidence: Dict[str, Any] = Field(default_factory=dict)
    performance_observations: List[Dict[str, Any]] = Field(default_factory=list)
    authorization: Dict[str, Any] = Field(default_factory=dict)


class ReviewDispositionRequest(BaseModel):
    status: str
    reviewer: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"Accepted", "Rejected", "Needs changes"}
        if value not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
        return value


app = FastAPI(
    title="Secure Code Debugging and Review Assistant",
    version="0.2.0",
    description=(
        "Offline-only repository-scale secure code review API for automotive engineering workflows. "
        "The system grounds findings in locally retrieved coding standards only."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repository_permission(user_id: str, repository_id: str) -> Optional[List[str]]:
    """Return authorized path prefixes, or reject access when a policy is configured."""
    raw_policy = os.getenv("REVIEW_REPOSITORY_PERMISSIONS", "").strip()
    if not raw_policy:
        return None
    try:
        policy = json.loads(raw_policy)
        repositories = policy[user_id]["repositories"]
        allowed = repositories[repository_id]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=403,
            detail="The authenticated user is not authorized for this repository.",
        ) from exc
    if allowed == "*" or allowed == ["*"]:
        return None
    if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
        raise HTTPException(status_code=500, detail="Repository permission policy is invalid.")
    return [item for item in allowed if item.strip()]


def _parse_evidence(build_logs: str, evidence_format: str) -> tuple[Dict[str, Any], List[str]]:
    if evidence_format != "sarif" or not build_logs.strip():
        return {}, []
    try:
        parsed = parse_sarif(build_logs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return parsed, diagnostics_as_lines(parsed)


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Log all requests and responses as a local audit trail for review traceability."""
    configured_key = os.getenv("REVIEW_API_KEY", "").strip()
    require_auth = os.getenv("REVIEW_REQUIRE_AUTH", "false").strip().lower() in {"1", "true", "yes"}
    if (configured_key or require_auth) and request.url.path.startswith("/api/v1/"):
        supplied_key = request.headers.get("X-API-Key", "")
        if not configured_key or not secrets.compare_digest(supplied_key, configured_key):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key."})
        request.state.user_id = os.getenv("REVIEW_AUTH_USER", "local-reviewer").strip()
    else:
        request.state.user_id = "anonymous-local-pilot"

    start_time = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    end_time = datetime.now(timezone.utc)

    logger.info(
        "AUDIT|request_id=%s|method=%s|path=%s|status=%s|duration_ms=%s|content_length=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        round((end_time - start_time).total_seconds() * 1000, 2),
        request.headers.get("content-length", "unknown"),
    )

    return response


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning("VALIDATION_ERROR|path=%s|detail=%s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("REQUEST_VALIDATION_ERROR|path=%s|detail=%s", request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTP_ERROR|path=%s|status=%s|detail=%s", request.url.path, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("UNEXPECTED_ERROR|path=%s|error=%s", request.url.path, str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error while generating secure code review results."},
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "secure-code-review-assistant"}


@app.get("/api/v1/metrics")
async def review_metrics() -> Dict[str, Any]:
    """Return local workflow metrics without exposing source code."""
    return review_store.metrics()


@app.get("/api/v1/reviews")
async def list_reviews(limit: int = 50) -> Dict[str, Any]:
    """List review metadata and current human disposition."""
    safe_limit = max(1, min(limit, 200))
    return {"reviews": review_store.list_reviews(safe_limit)}


@app.get("/api/v1/reviews/{review_id}")
async def get_review(review_id: str) -> Dict[str, Any]:
    record = review_store.get_review(review_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return record


@app.patch("/api/v1/reviews/{review_id}/disposition")
async def update_review_disposition(
    review_id: str, payload: ReviewDispositionRequest
) -> Dict[str, str]:
    updated_at = _utc_now()
    updated = review_store.update_disposition(
        review_id=review_id,
        status=payload.status,
        reviewer=payload.reviewer.strip(),
        notes=payload.notes.strip(),
        updated_at=updated_at,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found.")
    return {"review_id": review_id, "status": payload.status, "updated_at": updated_at}


@app.post("/api/v1/review", response_model=CodeReviewResponse)
async def review_endpoint(request: Request, payload: CodeReviewRequest) -> CodeReviewResponse:
    """Review code snippets using the local RAG-based secure coding policy engine."""
    request_id = getattr(request.state, "request_id", "unknown")
    code_hash = hashlib.sha256(payload.code_snippet.encode("utf-8")).hexdigest()
    parsed_evidence, evidence_warnings = _parse_evidence(payload.build_logs, payload.evidence_format)
    effective_warnings = list(payload.compiler_warnings or []) + evidence_warnings
    warnings_text = "\n".join(effective_warnings)
    warnings_hash = hashlib.sha256(warnings_text.encode("utf-8")).hexdigest()
    review_id = str(uuid.uuid4())
    created_at = _utc_now()
    try:
        findings = await run_in_threadpool(
            partial(
                review_code,
                code_snippet=payload.code_snippet,
                compiler_warnings=effective_warnings,
                file_name=payload.file_name,
                build_logs=payload.build_logs,
                related_files=[item.model_dump() for item in payload.related_files],
                historical_findings=review_store.approved_findings(),
            )
        )
    except Exception as exc:
        logger.exception(
            "REVIEW_FAILURE|request_id=%s|code_hash=%s|code_length=%s|warnings_hash=%s|warning_count=%s",
            request_id,
            code_hash,
            len(payload.code_snippet),
            warnings_hash,
            len(payload.compiler_warnings or []),
        )
        raise HTTPException(
            status_code=500,
            detail="The secure code review orchestrator could not produce a valid result.",
        ) from exc

    if not findings:
        raise HTTPException(
            status_code=404,
            detail="No relevant secure coding evidence was retrieved for the provided input.",
        )

    response = CodeReviewResponse(
        review_id=review_id,
        created_at=created_at,
        file_name=payload.file_name,
        review_summary=findings.get("review_summary", "No review summary available."),
        candidate_root_causes=findings.get("candidate_root_causes", []),
        suggested_remediation=findings.get("suggested_remediation", "No remediation suggestion available."),
        analysis_summary=findings.get("analysis_summary", ""),
        rule_reference=findings.get("rule_reference", "Not available"),
        source_evidence=findings.get("source_evidence", []),
        confidence=findings.get("confidence", "Low"),
        review_mode=findings.get("review_mode", "unknown"),
        code_summary=findings.get("code_summary", {}),
        findings=findings.get("findings", []),
        limitations=findings.get("limitations", []),
        retrieved_context=findings.get("retrieved_context"),
        parsed_evidence=parsed_evidence,
    )

    await run_in_threadpool(
        partial(
            review_store.save_review,
            review_id=review_id,
            created_at=created_at,
            file_name=payload.file_name,
            code_hash=code_hash,
            warnings_hash=warnings_hash,
            response=response.model_dump(),
        )
    )

    logger.info(
        "REVIEW_RESULT|request_id=%s|code_hash=%s|code_length=%s|warnings_hash=%s|warning_count=%s|confidence=%s|source_evidence_count=%s",
        request_id,
        code_hash,
        len(payload.code_snippet),
        warnings_hash,
        len(effective_warnings),
        response.confidence,
        len(response.source_evidence),
    )
    return response


@app.post("/api/v1/repository-review", response_model=RepositoryReviewResponse)
async def repository_review_endpoint(
    request: Request, payload: RepositoryReviewRequest
) -> RepositoryReviewResponse:
    """Safely inspect and review all supported C/C++ files in a repository ZIP."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        archive_bytes = base64.b64decode(payload.archive_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="archive_base64 is not valid Base64 data.") from exc

    archive_hash = hashlib.sha256(archive_bytes).hexdigest()
    parsed_evidence, evidence_warnings = _parse_evidence(payload.build_logs, payload.evidence_format)
    effective_warnings = list(payload.compiler_warnings or []) + evidence_warnings
    warnings_text = "\n".join(effective_warnings)
    warnings_hash = hashlib.sha256(warnings_text.encode("utf-8")).hexdigest()
    review_id = str(uuid.uuid4())
    created_at = _utc_now()

    user_id = getattr(request.state, "user_id", "anonymous-local-pilot")
    authorized_paths = _repository_permission(user_id, payload.repository_id)
    try:
        repository = await run_in_threadpool(
            analyze_repository_zip, archive_bytes, payload.archive_name, authorized_paths
        )
    except RepositoryArchiveError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    source_files: Dict[str, str] = repository.pop("_source_files")
    findings = repository["findings"]
    primary_path = str(findings[0]["file"]) if findings else sorted(source_files)[0]
    grounding: Dict[str, Any] = {
        "rule_reference": "No applicable rule found",
        "source_evidence": [],
        "confidence": "Low",
        "analysis_summary": "Repository structure and deterministic checks completed locally.",
        "review_mode": "deterministic-only",
    }
    if payload.use_rag:
        related_files = [
            {"file_name": path, "content": content[:10000]}
            for path, content in sorted(source_files.items())
            if path != primary_path
        ][:20]
        grounding = await run_in_threadpool(
            partial(
                review_code,
                code_snippet=source_files[primary_path][:20000],
                compiler_warnings=effective_warnings,
                file_name=primary_path,
                build_logs=payload.build_logs,
                related_files=related_files,
                historical_findings=review_store.approved_findings(),
            )
        )

    summary = repository["repository_summary"]
    unique_causes = list(dict.fromkeys(str(item["title"]) for item in findings))[:12]
    response = RepositoryReviewResponse(
        review_id=review_id,
        created_at=created_at,
        file_name=payload.archive_name,
        review_summary=(
            f"Analyzed {summary['source_file_count']} C/C++ files and {summary['total_lines']} source lines. "
            f"The repository scan identified {summary['finding_count']} candidate finding(s) "
            f"across {summary['affected_file_count']} file(s)."
        ),
        candidate_root_causes=unique_causes,
        suggested_remediation=(
            "Review Critical and High findings first, reproduce each issue with compilation and tests, "
            "then validate the repository with an approved static analyzer and qualified reviewer."
        ),
        analysis_summary=(
            f"Mapped {summary['function_count']} functions and {summary['dependency_edge_count']} internal "
            f"quoted-include dependencies. Deep grounding targeted {primary_path}. "
            + str(grounding.get("analysis_summary", ""))
        ).strip(),
        rule_reference=str(grounding.get("rule_reference", "No applicable rule found")),
        source_evidence=list(grounding.get("source_evidence") or []),
        confidence=str(grounding.get("confidence", "Low")),
        review_mode=f"repository-{grounding.get('review_mode', 'unknown')}",
        repository_summary=summary,
        modules=repository["modules"],
        dependency_edges=repository["dependency_edges"],
        unresolved_includes=repository["unresolved_includes"],
        skipped_files=repository["skipped_files"],
        repository_tree=repository["repository_tree"],
        findings=findings,
        limitations=[
            "Repository files are parsed as untrusted text and are never executed.",
            "The deterministic checks are conservative patterns, not a complete C/C++ parser or certified analyzer.",
            "Local RAG grounding, when enabled, targets the highest-risk module and uses up to 20 neighboring files as context.",
            "Ignored build, vendor, generated, hidden-tooling, and unsupported files are listed separately.",
            "All findings require compilation, tests, approved tooling, and qualified human review.",
        ],
        compiler_warning_count=len(effective_warnings),
        build_log_chars=len(payload.build_logs),
        parsed_evidence=parsed_evidence,
        performance_observations=repository["performance_observations"],
        authorization={
            "authenticated_user": user_id,
            "repository_id": payload.repository_id,
            "allowed_path_prefixes": authorized_paths or ["*"],
            "permission_verified": bool(os.getenv("REVIEW_REPOSITORY_PERMISSIONS", "").strip()),
        },
    )

    await run_in_threadpool(
        partial(
            review_store.save_review,
            review_id=review_id,
            created_at=created_at,
            file_name=payload.archive_name,
            code_hash=archive_hash,
            warnings_hash=warnings_hash,
            response=response.model_dump(),
        )
    )
    logger.info(
        "REPOSITORY_REVIEW_RESULT|request_id=%s|archive_hash=%s|source_files=%s|findings=%s|confidence=%s",
        request_id,
        archive_hash,
        summary["source_file_count"],
        summary["finding_count"],
        response.confidence,
    )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
