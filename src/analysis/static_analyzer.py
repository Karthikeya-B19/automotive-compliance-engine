from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple


FUNCTION_PATTERN = re.compile(
    r"(?m)^\s*(?:[A-Za-z_]\w*[\s\*]+)+(?P<name>[A-Za-z_]\w*)\s*"
    r"\([^;{}]*\)\s*\{"
)
CONTROL_WORDS = {"if", "for", "while", "switch", "return", "sizeof"}


def _line_number(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _function_ranges(source: str) -> List[Dict[str, Any]]:
    """Return best-effort C/C++ function ranges without requiring a compiler."""
    lines = source.splitlines()
    functions: List[Dict[str, Any]] = []
    for match in FUNCTION_PATTERN.finditer(source):
        name = match.group("name")
        if name in CONTROL_WORDS:
            continue

        start_line = _line_number(source, match.start())
        depth = 0
        end_line = start_line
        opened = False
        for line_no in range(start_line - 1, len(lines)):
            line = lines[line_no]
            depth += line.count("{")
            if line.count("{"):
                opened = True
            depth -= line.count("}")
            end_line = line_no + 1
            if opened and depth <= 0:
                break
        functions.append({"name": name, "start_line": start_line, "end_line": end_line})
    return functions


def _function_for_line(functions: List[Dict[str, Any]], line_no: int) -> Optional[str]:
    for function in functions:
        if function["start_line"] <= line_no <= function["end_line"]:
            return str(function["name"])
    return None


def _finding(
    *,
    title: str,
    category: str,
    severity: str,
    line: int,
    function: Optional[str],
    evidence: str,
    recommendation: str,
    cwe: Optional[str] = None,
) -> Dict[str, Any]:
    identity = f"{category}:{line}:{title}:{evidence}".encode("utf-8")
    return {
        "finding_id": hashlib.sha256(identity).hexdigest()[:12],
        "title": title,
        "category": category,
        "severity": severity,
        "line": line,
        "function": function,
        "evidence": evidence.strip(),
        "recommendation": recommendation,
        "rule_reference": "Requires confirmation against an approved coding standard",
        "cwe": cwe,
        "confidence": "High" if severity in {"Critical", "High"} else "Medium",
        "status": "Open",
        "analysis_method": "deterministic-preflight",
    }


def summarize_source(source: str) -> Dict[str, Any]:
    """Produce a compact module and control-flow inventory."""
    functions = _function_ranges(source)
    call_names = {
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", source)
        if match.group(1) not in CONTROL_WORDS
        and match.group(1) not in {function["name"] for function in functions}
    }
    return {
        "line_count": len(source.splitlines()),
        "function_count": len(functions),
        "functions": functions,
        "branch_count": len(re.findall(r"\b(?:if|switch)\s*\(", source)),
        "loop_count": len(re.findall(r"\b(?:for|while)\s*\(", source))
        + len(re.findall(r"\bdo\s*\{", source)),
        "called_functions": sorted(call_names)[:30],
    }


def analyze_source(source: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run conservative local checks and return a summary plus review candidates.

    These checks intentionally report candidates for human confirmation. They do not
    claim MISRA compliance and do not replace compilation or a certified analyzer.
    """
    summary = summarize_source(source)
    functions = summary["functions"]
    findings: List[Dict[str, Any]] = []
    lines = source.splitlines()

    dangerous_functions = {
        "gets": (
            "Critical",
            "Unbounded input function",
            "Replace gets with a bounded input routine and validate the resulting length.",
            "CWE-242",
        ),
        "strcpy": (
            "High",
            "Potential unbounded string copy",
            "Use a size-aware copy and prove that the destination capacity includes the terminator.",
            "CWE-120",
        ),
        "strcat": (
            "High",
            "Potential unbounded string concatenation",
            "Check remaining destination capacity before concatenation or use a bounded abstraction.",
            "CWE-120",
        ),
        "sprintf": (
            "High",
            "Potential unbounded formatted write",
            "Use snprintf with the destination size and validate truncation.",
            "CWE-120",
        ),
    }

    for line_no, line in enumerate(lines, start=1):
        function = _function_for_line(functions, line_no)
        for function_name, (severity, title, recommendation, cwe) in dangerous_functions.items():
            if re.search(rf"\b{function_name}\s*\(", line):
                findings.append(
                    _finding(
                        title=title,
                        category="Boundary safety",
                        severity=severity,
                        line=line_no,
                        function=function,
                        evidence=line,
                        recommendation=recommendation,
                        cwe=cwe,
                    )
                )

    null_assignments: Dict[str, int] = {}
    allocation_lines: Dict[str, int] = {}
    for line_no, line in enumerate(lines, start=1):
        code = re.sub(r"//.*$", "", line)
        null_match = re.search(
            r"(?:\b[A-Za-z_]\w*[\s\*]+)?\b([A-Za-z_]\w*)\s*=\s*(?:NULL|nullptr)\s*;",
            code,
        )
        if null_match:
            null_assignments[null_match.group(1)] = line_no

        allocation_match = re.search(
            r"\b([A-Za-z_]\w*)\s*=\s*(?:\([^;]+\)\s*)?(?:malloc|calloc|realloc)\s*\(",
            code,
        )
        if allocation_match:
            allocation_lines[allocation_match.group(1)] = line_no

        for variable, assigned_line in list(null_assignments.items()):
            if line_no < assigned_line:
                continue
            search_code = code
            if line_no == assigned_line and null_match and null_match.group(1) == variable:
                search_code = code[null_match.end() :]
            dereference = re.search(
                rf"(?:\*\s*{re.escape(variable)}\b|\b{re.escape(variable)}\s*->)",
                search_code,
            )
            guard = re.search(
                rf"\bif\s*\([^)]*{re.escape(variable)}[^)]*\)", search_code
            )
            if dereference and not guard:
                findings.append(
                    _finding(
                        title="Possible null-pointer dereference",
                        category="Pointer safety",
                        severity="Critical",
                        line=line_no,
                        function=_function_for_line(functions, line_no),
                        evidence=line,
                        recommendation=(
                            f"Prove '{variable}' is non-null before dereference and handle the failure path."
                        ),
                        cwe="CWE-476",
                    )
                )
                null_assignments.pop(variable, None)
                continue
            reassigned = re.search(
                rf"(?<!\*)\b{re.escape(variable)}\s*=\s*(?!(?:NULL|nullptr)\b)",
                search_code,
            )
            if reassigned:
                null_assignments.pop(variable, None)

    for variable, allocated_line in allocation_lines.items():
        if not re.search(rf"\bfree\s*\(\s*{re.escape(variable)}\s*\)", source):
            findings.append(
                _finding(
                    title="Allocated resource may not be released",
                    category="Resource management",
                    severity="Medium",
                    line=allocated_line,
                    function=_function_for_line(functions, allocated_line),
                    evidence=lines[allocated_line - 1],
                    recommendation=(
                        f"Define ownership for '{variable}' and release it on every exit path, or use a scoped wrapper."
                    ),
                    cwe="CWE-401",
                )
            )

    for function in functions:
        body = "\n".join(lines[function["start_line"] - 1 : function["end_line"]])
        for match in re.finditer(r"\bswitch\s*\([^)]*\)\s*\{", body):
            switch_tail = body[match.start() :]
            if not re.search(r"\bdefault\s*:", switch_tail):
                line_no = function["start_line"] + body[: match.start()].count("\n")
                findings.append(
                    _finding(
                        title="Switch statement has no default branch",
                        category="Control flow",
                        severity="Medium",
                        line=line_no,
                        function=function["name"],
                        evidence=lines[line_no - 1],
                        recommendation="Add an explicit default branch that reaches a defined safe state.",
                    )
                )

    findings.sort(
        key=lambda item: (
            {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(item["severity"], 4),
            item["line"],
        )
    )
    return summary, findings
