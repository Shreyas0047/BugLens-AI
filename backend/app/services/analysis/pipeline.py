"""Analysis stage: run static analyzers per language and store normalized findings."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.models.finding import FileStat, Finding
from app.models.repository import AnalysisRun, Repository
from app.services.analysis import normalize
from app.services.analysis.ast_python import analyze_python_tree
from app.services.analysis.runners.bandit import run_bandit
from app.services.analysis.runners.jsts import run_eslint, run_tsmorph
from app.services.analysis.runners.radon import complexity_findings, run_radon
from app.services.analysis.runners.ruff import run_ruff

# Per-tool caps prevent pathological repos from flooding the findings table.
MAX_PER_SOURCE = 500


def _cap(findings: list[dict], cap: int) -> list[dict]:
    return findings[:cap]


def _dedupe(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out = []
    for f in findings:
        key = (f["source"], f["type"], f["file"], f["line"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def run_analysis(
    db: Session, repo: Repository, run: AnalysisRun, workspace: Path
) -> tuple[int, list[dict]]:
    """Execute all analyzers for the repository's supported languages.

    Returns (stored_count, tool_status) where tool_status lists each tool's
    availability/failure for the report.
    """
    workspace = workspace.resolve()
    languages = (repo.languages_json or {}).keys()
    status: list[dict] = []
    all_findings: list[dict] = []

    if "python" in languages:
        # 1. custom AST (always runs, no external deps)
        for path, findings in analyze_python_tree(workspace).items():
            all_findings.extend(normalize.from_ast(path, findings))

        # 2. bandit
        result, findings = run_bandit(workspace)
        status.append(_tool_status(result))
        all_findings.extend(_cap(findings, MAX_PER_SOURCE))

        # 3. ruff
        result, findings = run_ruff(workspace)
        status.append(_tool_status(result))
        all_findings.extend(_cap(findings, MAX_PER_SOURCE))

        # 4. radon complexity
        result, stats = run_radon(workspace)
        status.append(_tool_status(result))
        findings = complexity_findings(workspace, stats)
        all_findings.extend(_cap(findings, 200))
        _store_file_stats(db, run.id, workspace, stats)

    if "javascript" in languages or "typescript" in languages:
        result, findings = run_tsmorph(workspace)
        status.append(_tool_status(result))
        all_findings.extend(_cap(findings, MAX_PER_SOURCE))
        if "javascript" in languages:
            result, findings = run_eslint(workspace)
            status.append(_tool_status(result))
            all_findings.extend(_cap(findings, MAX_PER_SOURCE))

    all_findings = _dedupe(all_findings)
    stored = _store_findings(db, run, repo, all_findings)
    return stored, status


def _store_findings(db: Session, run: AnalysisRun, repo: Repository, findings: list[dict]) -> int:
    for f in findings:
        db.add(
            Finding(
                run_id=run.id,
                repository_id=repo.id,
                source=f["source"],
                type=f["type"],
                category=f["category"],
                file=f["file"],
                line=f.get("line", 0),
                column=f.get("column", 0),
                message=f.get("message", ""),
                description=f.get("description", ""),
                confidence=f.get("confidence", 0.5),
                evidence_json=f.get("evidence"),
            )
        )
    db.commit()
    return len(findings)


def _store_file_stats(db: Session, run_id: int, workspace: Path, stats: dict) -> None:
    for path, info in stats.items():
        rel = str(Path(path).relative_to(workspace)) if Path(path).is_absolute() else path
        db.add(
            FileStat(
                run_id=run_id,
                path=rel,
                language="python",
                loc=0,
                complexity=float(info.get("cc", 0)),
                maintainability=float(info["mi"]) if info.get("mi") is not None else None,
            )
        )
    db.commit()


def _tool_status(result) -> dict:
    if not result.available:
        return {"tool": result.name, "available": False, "error": result.error}
    if result.timed_out:
        return {"tool": result.name, "available": True, "timed_out": True, "error": result.error}
    if result.exit_code not in (0, 1, 2) and result.error:
        return {
            "tool": result.name,
            "available": True,
            "exit_code": result.exit_code,
            "error": result.error,
        }
    return {"tool": result.name, "available": True, "exit_code": result.exit_code}
