"""Bandit runner: security-oriented static analysis (JSON output)."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
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
    "tests",
    "test",
]


def run_bandit(workspace: Path) -> tuple[ToolResult, list[dict]]:
    workspace = workspace.resolve()
    settings = get_settings()
    excludes = ",".join(_EXCLUDES)
    result = run_tool(
        "bandit",
        [
            "bandit",
            "-r",
            str(workspace),
            "-f",
            "json",
            "-q",
            "--exclude",
            excludes,
            "-lll",  # report all severities; confidence LOW and up default
        ],
        cwd=workspace,
        timeout=settings.clone_timeout_seconds,
        json_output=True,
    )
    findings: list[dict] = []
    if result.parsed is not None and isinstance(result.parsed, dict):
        findings = normalize.from_bandit(str(workspace), result.parsed)
    return result, findings
