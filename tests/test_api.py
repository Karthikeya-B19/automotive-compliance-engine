from fastapi.testclient import TestClient

from src.api import main


client = TestClient(main.app)


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

    def fake_review_code(code_snippet: str, compiler_warnings: list[str]) -> dict:
        assert code_snippet == "int speed; return speed;"
        assert compiler_warnings == ["use of uninitialized variable"]
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
