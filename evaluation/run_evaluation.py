from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.static_analyzer import analyze_source


DEFAULT_DATASET = PROJECT_ROOT / "evaluation" / "ground_truth.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "Evaluation_Results"


def evaluate(dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    true_positives = false_positives = false_negatives = 0

    for case in dataset:
        _, findings = analyze_source(case["source"])
        expected = set(case["expected_titles"])
        predicted = {finding["title"] for finding in findings}
        tp = len(expected & predicted)
        fp = len(predicted - expected)
        fn = len(expected - predicted)
        true_positives += tp
        false_positives += fp
        false_negatives += fn
        rows.append(
            {
                "case_id": case["case_id"],
                "description": case["description"],
                "expected": sorted(expected),
                "predicted": sorted(predicted),
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "passed": fp == 0 and fn == 0,
            }
        )

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 1.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Five-case synthetic unit benchmark for targeted deterministic patterns",
        "case_count": len(dataset),
        "passed_cases": sum(1 for row in rows if row["passed"]),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "limitations": [
            "The dataset is synthetic and intentionally small.",
            "Metrics cover only the implemented deterministic patterns.",
            "These results do not measure full MISRA compliance or production defect recall.",
        ],
        "cases": rows,
    }


def write_results(results: Dict[str, Any], output_dir: Path, prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}_EvaluationResults_v1.0.json"
    csv_path = output_dir / f"{prefix}_EvaluationCases_v1.0.csv"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "description",
                "expected",
                "predicted",
                "true_positives",
                "false_positives",
                "false_negatives",
                "passed",
            ],
        )
        writer.writeheader()
        for row in results["cases"]:
            writer.writerow({**row, "expected": " | ".join(row["expected"]), "predicted": " | ".join(row["predicted"])})
    print(json_path)
    print(csv_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic review patterns.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default="RegisterNo")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    results = evaluate(dataset)
    write_results(results, args.output_dir, args.prefix)


if __name__ == "__main__":
    main()
