"""Ruff runner: fast linter (JSON output). Selection avoids noisy style rules."""

from __future__ import annotations

from pathlib import Path

from app.services.analysis import normalize
from app.services.analysis.tool_registry import ToolResult, run_tool

_EXCLUDES = [
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]


def run_ruff(workspace: Path) -> tuple[ToolResult, list[dict]]:
    workspace = workspace.resolve()
    result = run_tool(
        "ruff",
        [
            "ruff",
            "check",
            str(workspace),
            "--output-format",
            "json",
            "--select",
            "F,E7,W6,B,S,A",
            "--exclude",
            ",".join(_EXCLUDES),
            "--no-cache",
        ],
        cwd=workspace,
        timeout=120,
        json_output=True,
    )
    findings: list[dict] = []
    if result.parsed is not None and isinstance(result.parsed, list):
        findings = normalize.from_ruff(str(workspace), result.parsed)
    return result, findings
