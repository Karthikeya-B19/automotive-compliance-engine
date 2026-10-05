"""Deterministic acceptance check for the submitted repository demo archive."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.repository_analyzer import analyze_repository_zip


ARCHIVE_NAME = "CB.AI.U4AID23109_AutomotiveECURepository_v1.0.zip"
ARCHIVE = ROOT / "demo" / ARCHIVE_NAME
if not ARCHIVE.exists():
    ARCHIVE = ROOT.parent / "Input_Data" / ARCHIVE_NAME

OUTPUT_DIR = ROOT / "Evaluation_Results"
if not OUTPUT_DIR.exists() and (ROOT.parent / "Evaluation_Results").exists():
    OUTPUT_DIR = ROOT.parent / "Evaluation_Results"
OUTPUT = OUTPUT_DIR / "CB.AI.U4AID23109_RepositoryEvaluation_v1.0.json"


def main() -> None:
    result = analyze_repository_zip(ARCHIVE.read_bytes(), ARCHIVE.name)
    summary = result["repository_summary"]
    skipped = {item["path"]: item["reason"] for item in result["skipped_files"]}
    checks = {
        "three_supported_source_files_scanned": summary["source_file_count"] == 3,
        "two_internal_include_dependencies_resolved": summary["dependency_edge_count"] == 2,
        "four_expected_findings_reported": summary["finding_count"] == 4,
        "only_unsafe_module_affected": summary["affected_file_count"] == 1,
        "all_local_includes_resolved": summary["unresolved_include_count"] == 0,
        "vendor_directory_excluded": skipped.get(
            "automotive_ecu_demo/vendor/legacy_copy.c"
        )
        == "ignored directory",
    }
    payload = {
        "artifact": "CB.AI.U4AID23109_RepositoryEvaluation_v1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": ARCHIVE.name,
        "overall_status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "repository_summary": summary,
        "dependency_edges": result["dependency_edges"],
        "finding_titles": [finding["title"] for finding in result["findings"]],
        "limitations": [
            "Synthetic acceptance scenario; not a production-accuracy benchmark.",
            "Regex-based findings require compiler, approved analyzer, tests, and human validation.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{payload['overall_status']}: {OUTPUT}")


if __name__ == "__main__":
    main()
