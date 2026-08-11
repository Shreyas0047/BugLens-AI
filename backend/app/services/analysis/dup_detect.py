"""Cross-file duplicate detection via normalized AST shape signatures.

Two functions are considered duplicates when their bodies produce the
same normalized token shape: statement/expression node kinds, operators,
and attribute access, with identifiers and literals replaced by
placeholders. Renaming variables or copying a function wholesale is
therefore still detected, while unrelated code rarely collides.
"""

from __future__ import annotations

import ast
from pathlib import Path

_IGNORED_DIRS = {
    "node_modules",
    "dist",
    "build",
    "target",
    ".git",
    ".venv",
    "venv",
    "coverage",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "tests",
    "test",
    "__pycache__",
}

# Bodies shorter than this are too trivial to count as duplication.
_MIN_TOKENS = 8

# Cap findings per duplicate group to keep reports readable.
MAX_PER_GROUP = 4
# Cap total findings for this detector.
MAX_TOTAL = 100


def _shape_tokens(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    tokens: list[str] = []
    for child in ast.walk(node):
        if child is node:
            continue
        kind = type(child).__name__
        if kind in {"FunctionDef", "AsyncFunctionDef"}:
            # Nested functions are reported on their own; mark the parent
            # shape without descending into their bodies.
            tokens.append("DEF")
            continue
        if kind in {"Name", "Constant", "Load", "Store", "Del", "arg", "arguments"}:
            continue
        tokens.append(kind)
    return tokens


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...] | None:
    tokens = _shape_tokens(node)
    if len(tokens) < _MIN_TOKENS:
        return None
    return tuple(tokens)


def analyze_duplicates(files: list[Path]) -> list[dict]:
    """Return DUPLICATE_FUNCTION findings for copy-pasted function bodies."""
    findings: list[dict] = []
    groups: dict[tuple[str, ...], list[tuple[str, int, str, str]]] = {}

    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            sig = _signature(node)
            if sig is None:
                continue
            groups.setdefault(sig, []).append(
                (str(path), node.lineno, node.name, ast.get_source_segment(source, node) or "")
            )

    total = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        total += 1
        if total > MAX_TOTAL:
            break
        others = [f"{Path(m[0]).name}:{m[1]} ({m[2]})" for m in members[1 : MAX_PER_GROUP + 1]]
        for file, line, name, snippet in members[:MAX_PER_GROUP]:
            findings.append(
                {
                    "source": "dup",
                    "type": "DUPLICATE_FUNCTION",
                    "category": "CODE_SMELL",
                    "file": file,
                    "line": line,
                    "message": (
                        f"Function '{name}' has the same body shape as "
                        f"{len(members) - 1} other location(s): {', '.join(others)}. "
                        "Likely copy-pasted code; consider extracting a shared helper."
                    ),
                    "description": "normalized AST shape fingerprint",
                    "confidence": 0.6,
                    "evidence": {"rule": "DUPLICATE_FUNCTION", "snippet": snippet},
                }
            )
    return findings


def python_files(workspace: Path) -> list[Path]:
    return [
        p for p in workspace.rglob("*.py") if not any(part in _IGNORED_DIRS for part in p.parts)
    ]
