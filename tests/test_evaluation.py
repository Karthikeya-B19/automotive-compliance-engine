import json
from pathlib import Path

from evaluation.run_evaluation import evaluate


def test_synthetic_evaluation_dataset_matches_expected_patterns() -> None:
    project_root = Path(__file__).resolve().parents[1]
    dataset = json.loads(
        (project_root / "evaluation" / "ground_truth.json").read_text(encoding="utf-8")
    )

    results = evaluate(dataset)

    assert results["passed_cases"] == results["case_count"]
    assert results["precision"] == 1.0
    assert results["recall"] == 1.0
