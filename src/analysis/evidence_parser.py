from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_sarif(text: str, *, max_results: int = 100) -> Dict[str, Any]:
    """Parse a bounded SARIF document into normalized diagnostic evidence."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid SARIF/JSON evidence: {exc.msg}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        raise ValueError("SARIF evidence must contain a top-level runs array.")

    diagnostics: List[Dict[str, Any]] = []
    tool_names: set[str] = set()
    for run in payload["runs"][:20]:
        if not isinstance(run, dict):
            continue
        driver = ((run.get("tool") or {}).get("driver") or {})
        if isinstance(driver, dict) and driver.get("name"):
            tool_names.add(str(driver["name"])[:120])
        for result in (run.get("results") or []):
            if len(diagnostics) >= max_results or not isinstance(result, dict):
                break
            message_value = result.get("message") or {}
            message = (
                message_value.get("text")
                if isinstance(message_value, dict)
                else str(message_value)
            ) or "No diagnostic message"
            path = "unknown"
            line = None
            locations = result.get("locations") or []
            if locations and isinstance(locations[0], dict):
                physical = locations[0].get("physicalLocation") or {}
                artifact = physical.get("artifactLocation") or {}
                region = physical.get("region") or {}
                path = str(artifact.get("uri") or "unknown")[:500]
                if isinstance(region.get("startLine"), int):
                    line = int(region["startLine"])
            diagnostics.append(
                {
                    "rule_id": str(result.get("ruleId") or "unspecified")[:160],
                    "level": str(result.get("level") or "warning")[:40],
                    "message": str(message)[:1000],
                    "file": path,
                    "line": line,
                }
            )
    return {
        "format": "sarif",
        "tool_names": sorted(tool_names),
        "result_count": len(diagnostics),
        "diagnostics": diagnostics,
    }


def diagnostics_as_lines(parsed: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for item in parsed.get("diagnostics") or []:
        location = str(item.get("file") or "unknown")
        if item.get("line") is not None:
            location += f":{item['line']}"
        lines.append(
            f"{location}: {item.get('level', 'warning')} "
            f"[{item.get('rule_id', 'unspecified')}] {item.get('message', '')}"
        )
    return lines
