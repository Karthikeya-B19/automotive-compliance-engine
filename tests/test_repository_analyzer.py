from __future__ import annotations

import io
import stat
import zipfile

import pytest

from src.analysis.repository_analyzer import RepositoryArchiveError, analyze_repository_zip


def build_repository_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "ecu/include/state.h",
            "typedef struct { int mode; } State; void update(State *state, const char *input);",
        )
        archive.writestr(
            "ecu/src/main.c",
            '#include "../include/state.h"\nint main(void) { State state = {0}; update(&state, "x"); return 0; }',
        )
        archive.writestr(
            "ecu/src/state.c",
            '#include "../include/state.h"\n#include <stdlib.h>\n#include <string.h>\n'
            "void update(State *state, const char *input) {\n"
            "  char target[4];\n  char *buffer = malloc(8U);\n  State *selected = NULL;\n"
            "  strcpy(target, input);\n  selected->mode = 1;\n"
            "  switch (state->mode) { case 1: state->mode = 2; break; }\n  buffer[0] = 0;\n}",
        )
        archive.writestr("ecu/vendor/ignored.c", "void ignored(void) { gets(0); }")
        archive.writestr("ecu/README.md", "Synthetic test repository")
    return buffer.getvalue()


def test_repository_zip_maps_modules_dependencies_and_findings() -> None:
    result = analyze_repository_zip(build_repository_zip(), "ecu.zip")
    summary = result["repository_summary"]

    assert summary["source_file_count"] == 3
    assert summary["dependency_edge_count"] == 2
    assert summary["finding_count"] == 4
    assert summary["affected_file_count"] == 1
    assert any(item["reason"] == "ignored directory" for item in result["skipped_files"])
    assert {item["file"] for item in result["findings"]} == {"ecu/src/state.c"}
    assert {item["title"] for item in result["findings"]} == {
        "Possible null-pointer dereference",
        "Potential unbounded string copy",
        "Allocated resource may not be released",
        "Switch statement has no default branch",
    }


def test_repository_zip_rejects_path_traversal() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.c", "int main(void) { return 0; }")

    with pytest.raises(RepositoryArchiveError, match="Unsafe archive path"):
        analyze_repository_zip(buffer.getvalue(), "unsafe.zip")


def test_repository_zip_rejects_symbolic_links() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("ecu/src/link.c")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target.c")

    with pytest.raises(RepositoryArchiveError, match="Symbolic links"):
        analyze_repository_zip(buffer.getvalue(), "unsafe.zip")
