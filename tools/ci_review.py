"""CI-friendly repository review that emits JSON or SARIF and enforces a severity gate."""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.repository_analyzer import IGNORED_PARTS, SUPPORTED_SUFFIXES, analyze_repository_zip

SEVERITY = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}


def archive_directory(repository: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(repository.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            relative = path.relative_to(repository)
            if any(part.lower() in IGNORED_PARTS for part in relative.parts[:-1]):
                continue
            archive.writestr(str(Path(repository.name) / relative).replace("\\", "/"), path.read_bytes())
    return buffer.getvalue()


def as_sarif(result: dict) -> dict:
    findings = result["findings"]
    rules = {}
    sarif_results = []
    for finding in findings:
        rule_id = finding.get("cwe") or finding["category"].replace(" ", "-").lower()
        rules[rule_id] = {
            "id": rule_id,
            "name": finding["title"],
            "shortDescription": {"text": finding["category"]},
            "help": {"text": finding["recommendation"]},
        }
        sarif_results.append(
            {
                "ruleId": rule_id,
                "level": {"Critical": "error", "High": "error", "Medium": "warning"}.get(
                    finding["severity"], "note"
                ),
                "message": {"text": finding["title"]},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding["file"]},
                            "region": {"startLine": finding["line"]},
                        }
                    }
                ],
            }
        )
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": "Automotive Secure Code Review", "rules": list(rules.values())}},
                "results": sarif_results,
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("--format", choices=("json", "sarif"), default="sarif")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on", choices=tuple(SEVERITY), default="High")
    args = parser.parse_args()
    if not args.repository.is_dir():
        parser.error("repository must be an existing directory")
    result = analyze_repository_zip(archive_directory(args.repository), f"{args.repository.name}.zip")
    result.pop("_source_files", None)
    payload = as_sarif(result) if args.format == "sarif" else result
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    threshold = SEVERITY[args.fail_on]
    return 1 if any(SEVERITY.get(item["severity"], 0) >= threshold for item in result["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
