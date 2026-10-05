from src.analysis.static_analyzer import analyze_source


def test_analyzer_reports_location_and_function_for_high_value_defects() -> None:
    source = """
#include <stdlib.h>
#include <string.h>

void update(char *input) {
    char target[8];
    char *buffer = malloc(32);
    char *state = NULL;
    strcpy(target, input);
    *state = 'A';
}
"""

    summary, findings = analyze_source(source)

    assert summary["function_count"] == 1
    assert summary["functions"][0]["name"] == "update"
    titles = {finding["title"] for finding in findings}
    assert "Potential unbounded string copy" in titles
    assert "Possible null-pointer dereference" in titles
    assert "Allocated resource may not be released" in titles
    assert all(finding["line"] > 0 for finding in findings)
    assert all(finding["function"] == "update" for finding in findings)


def test_analyzer_does_not_claim_compliance_when_no_pattern_matches() -> None:
    summary, findings = analyze_source("int add(int a, int b) { return a + b; }")

    assert summary["line_count"] == 1
    assert findings == []
