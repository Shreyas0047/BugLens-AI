"""ts-morph + ESLint runners for JS/TS analysis."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.services.analysis.tool_registry import ToolResult, run_tool

_IGNORE = "node_modules,dist,build,target,.git,.venv,venv,coverage,.next,.nuxt,.svelte-kit"

_ESLINT_CATEGORY: dict[str, str] = {
    "no-eval": "SECURITY",
    "no-implied-eval": "SECURITY",
    "no-new-func": "SECURITY",
    "no-prototype-builtins": "SECURITY",
    "no-debugger": "CODE_SMELL",
    "no-unreachable": "CORRECTNESS",
    "no-constant-condition": "CORRECTNESS",
    "no-self-compare": "CORRECTNESS",
    "no-dupe-keys": "CORRECTNESS",
    "no-duplicate-case": "CORRECTNESS",
    "no-fallthrough": "CORRECTNESS",
    "no-redeclare": "CORRECTNESS",
    "no-func-assign": "CORRECTNESS",
    "no-import-assign": "CORRECTNESS",
    "no-cond-assign": "CORRECTNESS",
    "no-unused-vars": "CODE_SMELL",
    "no-empty": "CODE_SMELL",
}


def _find_node() -> str | None:
    return shutil.which("node")


def run_tsmorph(workspace: Path) -> tuple[ToolResult, list[dict]]:
    """Run the ts-morph analyzer. Returns (result, findings)."""
    if _find_node() is None:
        return ToolResult(name="ts-morph", available=False, error="node not found"), []
    workspace = workspace.resolve()
    analyzer = Path(__file__).resolve().parents[4] / "tsanalyzer" / "analyzer.mjs"
    result = run_tool(
        "ts-morph",
        ["node", str(analyzer), str(workspace), _IGNORE],
        cwd=workspace,
        timeout=300,
    )
    findings: list[dict] = []
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                findings = parsed.get("findings", [])
        except json.JSONDecodeError:
            result.error = "ts-morph output was not valid JSON"
    return result, findings


def run_eslint(workspace: Path) -> tuple[ToolResult, list[dict]]:
    """Run ESLint (core rules only, no config lookup) on .js files."""
    workspace = workspace.resolve()
    result = run_tool(
        "eslint",
        [
            "npx",
            "--yes",
            "eslint@9",
            "--no-config-lookup",
            "--format",
            "json",
            "--rule",
            "no-eval: error",
            "--rule",
            "no-implied-eval: error",
            "--rule",
            "no-new-func: error",
            "--rule",
            "no-unreachable: warn",
            "--rule",
            "no-constant-condition: warn",
            "--rule",
            "no-unused-vars: warn",
            "--rule",
            "no-self-compare: warn",
            "--rule",
            "no-dupe-keys: error",
            "--rule",
            "no-duplicate-case: error",
            "--rule",
            "no-fallthrough: warn",
            "--rule",
            "no-prototype-builtins: warn",
            "--rule",
            "no-redeclare: warn",
            "--rule",
            "no-func-assign: error",
            "--rule",
            "no-import-assign: error",
            "--rule",
            "no-debugger: warn",
            "--rule",
            "no-cond-assign: warn",
            "--rule",
            "no-empty: warn",
            "--ignore-pattern",
            "node_modules",
            "--ignore-pattern",
            "dist",
            "--ignore-pattern",
            "build",
            "--ignore-pattern",
            "*.min.js",
            "--ext",
            ".js,.jsx,.mjs,.cjs",
            str(workspace),
        ],
        cwd=workspace,
        timeout=180,
        json_output=True,
    )
    findings: list[dict] = []
    if result.parsed is not None and isinstance(result.parsed, list):
        for file_result in result.parsed:
            file = file_result.get("filePath", "")
            for msg in file_result.get("messages", []):
                if msg.get("fatal"):
                    continue
                findings.append(
                    {
                        "source": "eslint",
                        "type": msg.get("ruleId") or "SYNTAX",
                        "category": _ESLINT_CATEGORY.get(msg.get("ruleId"), "CORRECTNESS"),
                        "file": (
                            str(Path(file).relative_to(workspace))
                            if Path(file).is_absolute()
                            else file
                        ),
                        "line": msg.get("line", 0),
                        "column": msg.get("column", 0) or 0,
                        "message": msg.get("message", ""),
                        "description": f"severity {msg.get('severity')}",
                        "confidence": 0.6,
                        "evidence": {"rule": msg.get("ruleId")},
                    }
                )
    return result, findings
