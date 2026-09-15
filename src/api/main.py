from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.rag.orchestrator import review_code

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


class CodeReviewRequest(BaseModel):
    code_snippet: str = Field(..., min_length=1, description="Source code to review")
    compiler_warnings: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional compiler or static analysis warnings",
    )

    @field_validator("compiler_warnings")
    @classmethod
    def validate_warnings(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return []
        return [warning.strip() for warning in value if warning and warning.strip()]


class CodeReviewResponse(BaseModel):
    review_summary: str
    candidate_root_causes: List[str] = Field(default_factory=list)
    suggested_remediation: str
    rule_reference: str
    source_evidence: List[str] = Field(default_factory=list)
    confidence: str
    retrieved_context: Optional[List[Dict[str, Any]]] = Field(default=None)


app = FastAPI(
    title="Secure Code Debugging and Review Assistant",
    version="0.1.0",
    description=(
        "Offline-only secure code review API for automotive engineering workflows. "
        "The system grounds findings in locally retrieved coding standards only."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Log all requests and responses as a local audit trail for review traceability."""
    start_time = datetime.now(timezone.utc)
    request_body = None
    try:
        body = await request.body()
        if body:
            request_body = body.decode("utf-8", errors="replace")
    except Exception:
        request_body = "[unreadable request body]"

    response = await call_next(request)
    end_time = datetime.now(timezone.utc)

    logger.info(
        "AUDIT|method=%s|path=%s|status=%s|duration_ms=%s|request_body=%s",
        request.method,
        request.url.path,
        response.status_code,
        round((end_time - start_time).total_seconds() * 1000, 2),
        request_body,
    )

    return response


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning("VALIDATION_ERROR|path=%s|detail=%s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


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


@app.post("/api/v1/review", response_model=CodeReviewResponse)
async def review_endpoint(payload: CodeReviewRequest) -> CodeReviewResponse:
    """Review code snippets using the local RAG-based secure coding policy engine."""
    try:
        findings = review_code(
            code_snippet=payload.code_snippet,
            compiler_warnings=payload.compiler_warnings,
        )
    except Exception as exc:
        logger.exception("REVIEW_FAILURE|code_snippet_length=%s|warnings=%s", len(payload.code_snippet), payload.compiler_warnings)
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
        review_summary=findings.get("review_summary", "No review summary available."),
        candidate_root_causes=findings.get("candidate_root_causes", []),
        suggested_remediation=findings.get("suggested_remediation", "No remediation suggestion available."),
        rule_reference=findings.get("rule_reference", "Not available"),
        source_evidence=findings.get("source_evidence", []),
        confidence=findings.get("confidence", "medium"),
        retrieved_context=findings.get("retrieved_context"),
    )

    logger.info(
        "REVIEW_RESULT|rule_reference=%s|confidence=%s|source_evidence_count=%s",
        response.rule_reference,
        response.confidence,
        len(response.source_evidence),
    )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
