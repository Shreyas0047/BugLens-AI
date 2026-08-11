"""Normalization: convert raw analyzer output into unified finding dicts."""

from __future__ import annotations

from app.services.analysis.ast_python import ASTFinding

_CONFIDENCE_MAP = {"UNDEFINED": 0.5, "LOW": 0.35, "MEDIUM": 0.6, "HIGH": 0.9}


def from_ast(path: str, findings: list[ASTFinding]) -> list[dict]:
    return [
        {
            "source": "ast-custom",
            "type": f.type,
            "category": f.category,
            "file": path,
            "line": f.line,
            "column": f.column,
            "message": f.message,
            "description": f.evidence.get("detail") or f.evidence.get("name") or "",
            "confidence": f.confidence,
            "evidence": f.evidence,
        }
        for f in findings
    ]


def from_bandit(path: str, raw: dict) -> list[dict]:
    out = []
    for issue in raw.get("results", []):
        file = issue.get("filename", path)
        out.append(
            {
                "source": "bandit",
                "type": issue.get("test_name", "BANDIT"),
                "category": _bandit_category(issue),
                "file": file,
                "line": issue.get("line_number", 0),
                "column": issue.get("col_offset", 0) or 0,
                "message": issue.get("issue_text", ""),
                "description": (
                    f"{issue.get('test_id', '')} {issue.get('test_name', '')} — "
                    f"CWE: {issue.get('issue_cwe', {}).get('id', 'n/a')}"
                ),
                "confidence": _CONFIDENCE_MAP.get(issue.get("issue_confidence", "").upper(), 0.5),
                "evidence": {"rule": issue.get("test_id"), "code": issue.get("code", "")[:2000]},
            }
        )
    return out


def from_ruff(path: str, raw: list[dict]) -> list[dict]:
    out = []
    for issue in raw:
        out.append(
            {
                "source": "ruff",
                "type": issue.get("code", "RUFF"),
                "category": _ruff_category(issue.get("code", "")),
                "file": issue.get("filename", path),
                "line": issue.get("location", {}).get("row", 0),
                "column": issue.get("location", {}).get("column", 0) or 0,
                "message": issue.get("message", ""),
                "description": (
                    f"Ruff {issue.get('code', '')} — {issue.get('fix_availability', '')}"
                ),
                "confidence": 0.55,
                "evidence": {"rule": issue.get("code"), "url": issue.get("url")},
            }
        )
    return out


def _bandit_category(issue: dict) -> str:
    return "SECURITY"


def _ruff_category(code: str) -> str:
    prefix = code[:1]
    return {
        "F": "CORRECTNESS",
        "E": "STYLE",
        "W": "STYLE",
        "B": "CORRECTNESS",
        "S": "SECURITY",
        "A": "CODE_SMELL",
        "I": "STYLE",
        "N": "STYLE",
        "C": "CODE_SMELL",
        "D": "STYLE",
        "T": "CORRECTNESS",
        "UP": "STYLE",
    }.get(prefix, "CODE_SMELL")
