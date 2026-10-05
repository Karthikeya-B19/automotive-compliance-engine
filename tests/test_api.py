import base64
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.api import main
from src.storage.review_store import ReviewStore


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def isolated_review_store(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "review_store", ReviewStore(tmp_path / "reviews.db"))


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "secure-code-review-assistant",
    }


def test_review_endpoint_returns_validated_response(monkeypatch) -> None:
    expected_review = {
        "review_summary": "The snippet may read an uninitialized automatic variable.",
        "candidate_root_causes": ["Automatic variable is used before assignment."],
        "suggested_remediation": "Initialize the variable before evaluating it.",
        "rule_reference": "Rule 9.1 (Required)",
        "source_evidence": [
            "Rule 9.1 (Required): All automatic variables shall have been assigned a value before being used."
        ],
        "confidence": "high",
        "retrieved_context": [
            {
                "content": "Rule 9.1 (Required): All automatic variables shall have been assigned a value before being used.",
                "source": "MISRA_C_Mock_Standard.pdf",
                "chunk_index": 0,
                "score": None,
            }
        ],
    }

    def fake_review_code(
        code_snippet: str,
        compiler_warnings: list[str],
        **kwargs,
    ) -> dict:
        assert code_snippet == "int speed; return speed;"
        assert compiler_warnings == ["use of uninitialized variable"]
        assert kwargs["file_name"] == "pasted_snippet.c"
        return expected_review

    monkeypatch.setattr(main, "review_code", fake_review_code)

    response = client.post(
        "/api/v1/review",
        json={
            "code_snippet": "int speed; return speed;",
            "compiler_warnings": [" use of uninitialized variable "],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_summary"] == expected_review["review_summary"]
    assert body["candidate_root_causes"] == expected_review["candidate_root_causes"]
    assert body["suggested_remediation"] == expected_review["suggested_remediation"]
    assert body["rule_reference"] == expected_review["rule_reference"]
    assert body["source_evidence"] == expected_review["source_evidence"]
    assert body["confidence"] == expected_review["confidence"]
    assert body["retrieved_context"] == expected_review["retrieved_context"]
    assert body["review_id"]
    assert body["review_mode"] == "unknown"

    history = client.get("/api/v1/reviews")
    assert history.status_code == 200
    assert history.json()["reviews"][0]["review_id"] == body["review_id"]

    disposition = client.patch(
        f"/api/v1/reviews/{body['review_id']}/disposition",
        json={
            "status": "Accepted",
            "reviewer": "Test Reviewer",
            "notes": "Confirmed with compilation and unit tests.",
        },
    )
    assert disposition.status_code == 200
    assert disposition.json()["status"] == "Accepted"

    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["completed_reviews"] == 1


def test_review_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/api/v1/review",
        json={"code_snippet": "print('not C')", "file_name": "sample.py"},
    )

    assert response.status_code == 422


def test_repository_review_scans_entire_zip_and_persists_result() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "repo/include/state.h",
            "typedef struct { int value; } State; void update(State *state);",
        )
        archive.writestr(
            "repo/src/state.c",
            '#include "../include/state.h"\nvoid update(State *state) { State *target = NULL; target->value = 1; }',
        )
        archive.writestr("repo/vendor/ignored.c", "void ignored(void) { gets(0); }")

    response = client.post(
        "/api/v1/repository-review",
        json={
            "archive_name": "repo.zip",
            "archive_base64": base64.b64encode(buffer.getvalue()).decode("ascii"),
            "compiler_warnings": ["repo/src/state.c:2: possible null dereference"],
            "use_rag": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["repository_summary"]["source_file_count"] == 2
    assert body["repository_summary"]["dependency_edge_count"] == 1
    assert body["repository_summary"]["finding_count"] == 1
    assert body["findings"][0]["file"] == "repo/src/state.c"
    assert body["review_mode"] == "repository-deterministic-only"
    assert body["compiler_warning_count"] == 1
    stored = client.get(f"/api/v1/reviews/{body['review_id']}")
    assert stored.status_code == 200
    assert stored.json()["response"]["repository_summary"]["source_file_count"] == 2


def test_repository_review_rejects_invalid_archive() -> None:
    response = client.post(
        "/api/v1/repository-review",
        json={
            "archive_name": "repo.zip",
            "archive_base64": base64.b64encode(b"not-a-zip").decode("ascii"),
            "use_rag": False,
        },
    )

    assert response.status_code == 422
