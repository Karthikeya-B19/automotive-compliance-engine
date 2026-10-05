from __future__ import annotations

import hashlib
import io
import posixpath
import re
import stat
import zipfile
from collections import Counter
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from src.analysis.static_analyzer import analyze_source


SUPPORTED_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}
IGNORED_PARTS = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "dist",
    "out",
    "node_modules",
    "vendor",
    "third_party",
    "third-party",
    "external",
    "generated",
}
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_SOURCE_FILES = 300
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_SOURCE_BYTES = 2 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
INCLUDE_PATTERN = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.MULTILINE)
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class RepositoryArchiveError(ValueError):
    """Raised when a repository archive violates the safe-analysis boundary."""


def _safe_member_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    if "\x00" in normalized:
        raise RepositoryArchiveError("Archive entry contains a null byte.")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RepositoryArchiveError(f"Unsafe archive path: {name}")
    if any(":" in part for part in path.parts):
        raise RepositoryArchiveError(f"Unsafe archive path: {name}")
    return path


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _is_ignored(path: PurePosixPath) -> bool:
    return any(part.lower() in IGNORED_PARTS for part in path.parts[:-1])


def _decode_source(raw: bytes, path: str) -> str:
    if b"\x00" in raw:
        raise RepositoryArchiveError(f"Binary content is not allowed in source file: {path}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RepositoryArchiveError(f"Source file must be UTF-8 text: {path}") from exc


def _resolve_include(source_path: str, include: str, all_paths: set[str]) -> str | None:
    source_parent = PurePosixPath(source_path).parent
    relative = posixpath.normpath(str(source_parent.joinpath(include)))
    if relative in all_paths:
        return relative
    normalized = str(PurePosixPath(include))
    if normalized in all_paths:
        return normalized
    suffix_matches = sorted(path for path in all_paths if path.endswith("/" + normalized))
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    basename_matches = sorted(path for path in all_paths if PurePosixPath(path).name == PurePosixPath(include).name)
    if len(basename_matches) == 1:
        return basename_matches[0]
    return None


def _repository_tree(paths: List[str]) -> List[str]:
    root: Dict[str, Any] = {}
    for path in sorted(paths):
        cursor = root
        for part in PurePosixPath(path).parts:
            cursor = cursor.setdefault(part, {})

    lines: List[str] = []

    def walk(node: Dict[str, Any], prefix: str = "") -> None:
        items = sorted(node.items())
        for index, (name, children) in enumerate(items):
            last = index == len(items) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{name}")
            if children:
                walk(children, prefix + ("    " if last else "│   "))

    walk(root)
    return lines[:500]


def analyze_repository_zip(
    archive_bytes: bytes,
    archive_name: str,
    allowed_path_prefixes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyze C/C++ files from a ZIP without extracting or executing repository content."""
    if not archive_bytes:
        raise RepositoryArchiveError("Repository archive is empty.")
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise RepositoryArchiveError(
            f"Repository archive exceeds the {MAX_ARCHIVE_BYTES // (1024 * 1024)} MB limit."
        )
    if not zipfile.is_zipfile(io.BytesIO(archive_bytes)):
        raise RepositoryArchiveError("The uploaded file is not a valid ZIP archive.")

    sources: Dict[str, str] = {}
    skipped_files: List[Dict[str, str]] = []
    total_source_bytes = 0
    seen_paths: set[str] = set()
    normalized_prefixes = [
        str(_safe_member_path(prefix.rstrip("/") + "/placeholder").parent).rstrip("/") + "/"
        for prefix in (allowed_path_prefixes or [])
        if prefix.strip()
    ]

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path_obj = _safe_member_path(info.filename)
            path = str(path_obj)
            if path in seen_paths:
                raise RepositoryArchiveError(f"Duplicate archive path: {path}")
            seen_paths.add(path)
            if info.flag_bits & 0x1:
                raise RepositoryArchiveError(f"Encrypted archive entry is not supported: {path}")
            if _is_symlink(info):
                raise RepositoryArchiveError(f"Symbolic links are not allowed: {path}")
            if _is_ignored(path_obj):
                skipped_files.append({"path": path, "reason": "ignored directory"})
                continue
            suffix = path_obj.suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                skipped_files.append({"path": path, "reason": "unsupported file type"})
                continue
            if normalized_prefixes and not any(path.startswith(prefix) for prefix in normalized_prefixes):
                raise RepositoryArchiveError(
                    f"Source path is outside the authorized repository paths: {path}"
                )
            if info.file_size > MAX_FILE_BYTES:
                raise RepositoryArchiveError(f"Source file exceeds the per-file limit: {path}")
            if info.file_size and info.compress_size == 0:
                raise RepositoryArchiveError(f"Suspicious compression metadata: {path}")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise RepositoryArchiveError(f"Suspicious compression ratio: {path}")
            total_source_bytes += info.file_size
            if total_source_bytes > MAX_TOTAL_SOURCE_BYTES:
                raise RepositoryArchiveError("Repository source exceeds the 2 MB expanded-text limit.")
            if len(sources) >= MAX_SOURCE_FILES:
                raise RepositoryArchiveError(f"Repository exceeds the {MAX_SOURCE_FILES}-file source limit.")
            sources[path] = _decode_source(archive.read(info), path)

    if not sources:
        raise RepositoryArchiveError("No supported UTF-8 C/C++ source files were found.")

    all_paths = set(sources)
    modules: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    dependency_edges: List[Dict[str, str]] = []
    unresolved_includes: List[Dict[str, str]] = []
    severity_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    total_lines = total_functions = 0
    total_branches = total_loops = dynamic_allocation_count = 0
    performance_observations: List[Dict[str, Any]] = []

    for path, source in sorted(sources.items()):
        summary, module_findings = analyze_source(source)
        includes = INCLUDE_PATTERN.findall(source)
        resolved_includes: List[str] = []
        for include in includes:
            target = _resolve_include(path, include, all_paths)
            if target:
                resolved_includes.append(target)
                dependency_edges.append({"source": path, "target": target, "include": include})
            else:
                unresolved_includes.append({"source": path, "include": include})

        total_lines += int(summary["line_count"])
        total_functions += int(summary["function_count"])
        total_branches += int(summary["branch_count"])
        total_loops += int(summary["loop_count"])
        allocations = len(re.findall(r"\b(?:malloc|calloc|realloc)\s*\(", source))
        dynamic_allocation_count += allocations
        complexity_estimate = 1 + int(summary["branch_count"]) + int(summary["loop_count"])
        if complexity_estimate >= 8:
            performance_observations.append(
                {
                    "file": path,
                    "category": "complexity",
                    "observation": f"Module cyclomatic-complexity estimate is {complexity_estimate}.",
                    "recommendation": "Profile representative execution paths and refactor complex decision logic.",
                }
            )
        if allocations:
            performance_observations.append(
                {
                    "file": path,
                    "category": "dynamic-memory",
                    "observation": f"Detected {allocations} dynamic allocation call(s).",
                    "recommendation": "Measure allocation latency/fragmentation and confirm deterministic ownership for the target ECU.",
                }
            )
        language_counts[PurePosixPath(path).suffix.lower()] += 1
        modules.append(
            {
                "path": path,
                "language": PurePosixPath(path).suffix.lower(),
                "line_count": summary["line_count"],
                "function_count": summary["function_count"],
                "functions": summary["functions"],
                "branch_count": summary["branch_count"],
                "loop_count": summary["loop_count"],
                "called_functions": summary["called_functions"],
                "quoted_includes": includes,
                "resolved_includes": resolved_includes,
                "finding_count": len(module_findings),
                "complexity_estimate": complexity_estimate,
                "dynamic_allocation_count": allocations,
            }
        )
        for finding in module_findings:
            item = dict(finding, file=path)
            identity = f"{path}:{finding['finding_id']}".encode("utf-8")
            item["finding_id"] = hashlib.sha256(identity).hexdigest()[:12]
            findings.append(item)
            severity_counts[str(item["severity"])] += 1

    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(str(item["severity"]), 9),
            str(item["file"]),
            int(item["line"]),
        )
    )
    affected_files = len({str(item["file"]) for item in findings})
    root_directories = sorted({PurePosixPath(path).parts[0] for path in sources})

    return {
        "repository_summary": {
            "archive_name": archive_name,
            "source_file_count": len(sources),
            "total_source_bytes": total_source_bytes,
            "total_lines": total_lines,
            "function_count": total_functions,
            "finding_count": len(findings),
            "affected_file_count": affected_files,
            "dependency_edge_count": len(dependency_edges),
            "unresolved_include_count": len(unresolved_includes),
            "skipped_file_count": len(skipped_files),
            "severity_counts": dict(sorted(severity_counts.items())),
            "language_counts": dict(sorted(language_counts.items())),
            "root_directories": root_directories,
            "branch_count": total_branches,
            "loop_count": total_loops,
            "complexity_estimate": len(sources) + total_branches + total_loops,
            "dynamic_allocation_count": dynamic_allocation_count,
            "authorized_path_prefixes": normalized_prefixes or ["*"],
        },
        "modules": modules,
        "dependency_edges": dependency_edges,
        "unresolved_includes": unresolved_includes,
        "skipped_files": skipped_files[:200],
        "repository_tree": _repository_tree(list(sources)),
        "findings": findings,
        "performance_observations": performance_observations,
        "_source_files": sources,
    }
