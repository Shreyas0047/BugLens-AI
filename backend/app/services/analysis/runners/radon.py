"""Radon runner: cyclomatic complexity + maintainability index (JSON)."""

from __future__ import annotations

from pathlib import Path

from app.services.analysis.tool_registry import ToolResult, run_tool

HIGH_COMPLEXITY_THRESHOLD = 15


def run_radon(workspace: Path) -> tuple[ToolResult, dict]:
    """Returns (result, {path: {cc: float, mi: float}})."""
    workspace = workspace.resolve()
    cc_result = run_tool(
        "radon",
        [
            "radon",
            "cc",
            str(workspace),
            "-s",
            "-j",
            "--exclude",
            "tests,test,.git,node_modules,dist,build",
        ],
        cwd=workspace,
        timeout=180,
        json_output=True,
    )
    mi_result = run_tool(
        "radon",
        [
            "radon",
            "mi",
            str(workspace),
            "-j",
            "--exclude",
            "tests,test,.git,node_modules,dist,build",
        ],
        cwd=workspace,
        timeout=180,
        json_output=True,
    )

    stats: dict[str, dict] = {}
    if cc_result.parsed is not None and isinstance(cc_result.parsed, dict):
        for path, blocks in cc_result.parsed.items():
            max_cc = max((b.get("complexity", 0) for b in blocks), default=0)
            stats.setdefault(path, {})["max_cc"] = max_cc
            stats[path]["cc"] = max_cc
    if mi_result.parsed is not None and isinstance(mi_result.parsed, dict):
        mi_data = mi_result.parsed.get("mi", mi_result.parsed)
        if isinstance(mi_data, dict):
            for path, value in mi_data.items():
                if isinstance(value, dict):
                    value = value.get("mi", value)
                stats.setdefault(path, {})["mi"] = round(float(value), 2)
    return cc_result, stats


def complexity_findings(workspace: Path, stats: dict) -> list[dict]:
    findings = []
    for path, info in stats.items():
        cc = info.get("cc", 0)
        if cc >= HIGH_COMPLEXITY_THRESHOLD:
            findings.append(
                {
                    "source": "radon",
                    "type": "HIGH_COMPLEXITY",
                    "category": "CODE_SMELL",
                    "file": (
                        str(Path(path).relative_to(workspace)) if Path(path).is_absolute() else path
                    ),
                    "line": 0,
                    "column": 0,
                    "message": (
                        f"Function with cyclomatic complexity {cc} — exceeds recommended "
                        f"threshold of {HIGH_COMPLEXITY_THRESHOLD}. High complexity correlates "
                        "with defect density and reduced testability."
                    ),
                    "description": f"max complexity {cc}",
                    "confidence": 0.7,
                    "evidence": {"rule": "CC>=" + str(HIGH_COMPLEXITY_THRESHOLD), "complexity": cc},
                }
            )
    return findings
