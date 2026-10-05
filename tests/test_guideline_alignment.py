import base64
import io
import json
import zipfile

from fastapi.testclient import TestClient

from src.analysis.evidence_parser import diagnostics_as_lines, parse_sarif
from src.analysis.repository_analyzer import RepositoryArchiveError, analyze_repository_zip
from src.api import main
from src.storage.review_store import ReviewStore


def _zip(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_sarif_is_structurally_parsed() -> None:
    parsed = parse_sarif(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "clang-tidy"}},
                        "results": [
                            {
                                "ruleId": "cppcoreguidelines-pro-bounds-array-to-pointer-decay",
                                "level": "warning",
                                "message": {"text": "Review array bounds."},
                                "locations": [
                                    {
                                        "physicalLocation": {
                                            "artifactLocation": {"uri": "src/main.c"},
                                            "region": {"startLine": 7},
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )
    )
    assert parsed["tool_names"] == ["clang-tidy"]
    assert parsed["result_count"] == 1
    assert diagnostics_as_lines(parsed)[0].startswith("src/main.c:7: warning")


def test_repository_path_permission_is_enforced() -> None:
    archive = _zip({"repo/src/main.c": "int main(void){return 0;}", "repo/test/test.c": "int x;"})
    try:
        analyze_repository_zip(archive, "repo.zip", ["repo/src/"])
    except RepositoryArchiveError as exc:
        assert "outside the authorized repository paths" in str(exc)
    else:
        raise AssertionError("Unauthorized source path was accepted")


def test_repository_performance_observation_reports_dynamic_allocation() -> None:
    result = analyze_repository_zip(
        _zip({"repo/src/main.c": "#include <stdlib.h>\nvoid f(void){void *p=malloc(4);}"}),
        "repo.zip",
    )
    assert result["repository_summary"]["dynamic_allocation_count"] == 1
    assert result["performance_observations"][0]["category"] == "dynamic-memory"


def test_api_authenticates_and_checks_repository_permission(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "review_store", ReviewStore(tmp_path / "reviews.db"))
    monkeypatch.setenv("REVIEW_API_KEY", "test-secret")
    monkeypatch.setenv("REVIEW_REQUIRE_AUTH", "true")
    monkeypatch.setenv("REVIEW_AUTH_USER", "reviewer-1")
    monkeypatch.setenv(
        "REVIEW_REPOSITORY_PERMISSIONS",
        json.dumps({"reviewer-1": {"repositories": {"authorized-repo": ["repo/src/"]}}}),
    )
    client = TestClient(main.app)
    payload = {
        "repository_id": "authorized-repo",
        "archive_name": "repo.zip",
        "archive_base64": base64.b64encode(
            _zip({"repo/src/main.c": "int main(void){return 0;}"})
        ).decode("ascii"),
        "use_rag": False,
    }
    assert client.post("/api/v1/repository-review", json=payload).status_code == 401
    response = client.post(
        "/api/v1/repository-review",
        json=payload,
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["authorization"]["permission_verified"] is True
