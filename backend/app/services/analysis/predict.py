"""Risk engine: heuristic severity prediction for stored findings.

Computes a risk_score in [0, 1] and a severity band per finding by
combining the rule's inherent severity, its category, the analyzer's
confidence, and the complexity of the file it was found in.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finding import FileStat, Finding

MODEL_VERSION = "heuristic-v1"

# Rule types with an inherent higher (or lower) severity. Base of 0.5.
_RULE_DELTAS: dict[str, float] = {
    "SQL_INJECTION": 0.25,
    "DANGEROUS_DESERIALIZATION": 0.25,
    "DANGEROUS_EVAL": 0.25,
    "DANGEROUS_FUNCTION": 0.2,
    "HARDCODED_SECRET": 0.25,
    "UNSAFE_INNER_HTML": 0.2,
    "UNSAFE_SUBPROCESS": 0.2,
    "SELF_COMPARISON": 0.3,
    "ASSERT_VALIDATION": 0.05,
    "NONE_COMPARISON": 0.05,
    "UNUSED_VARIABLE": -0.15,
    "UNUSED_FUNCTION": -0.1,
    "UNUSED_CLASS": -0.1,
}

_CATEGORY_DELTAS: dict[str, float] = {
    "SECURITY": 0.1,
    "CORRECTNESS": 0.05,
    "PERFORMANCE": -0.05,
    "CODE_SMELL": -0.05,
}

# Radon cyclomatic complexity thresholds for file-level risk.
_HIGH_COMPLEXITY = 10.0
_MODERATE_COMPLEXITY = 5.0
_COMPLEXITY_BOOST = 0.03


def _severity_band(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.45:
        return "medium"
    if score >= 0.25:
        return "low"
    return "info"


@dataclass
class Prediction:
    risk_score: float
    severity: str


def predict_finding(
    finding_type: str,
    category: str,
    confidence: float,
    file_complexity: float | None,
) -> Prediction:
    score = 0.5 + _RULE_DELTAS.get(finding_type, 0.0) + _CATEGORY_DELTAS.get(category, 0.0)
    score = score * confidence + (1 - confidence) * 0.5
    if file_complexity is not None:
        if file_complexity >= _HIGH_COMPLEXITY:
            score += _COMPLEXITY_BOOST
        elif file_complexity >= _MODERATE_COMPLEXITY:
            score += _COMPLEXITY_BOOST / 2
    score = max(0.05, min(0.98, score))
    return Prediction(risk_score=round(score, 3), severity=_severity_band(score))


def run_predict(db: Session, run_id: int) -> int:
    """Score every finding in a run. Returns the number of findings updated."""
    findings = list(db.scalars(select(Finding).where(Finding.run_id == run_id)).all())
    if not findings:
        return 0

    complexity_by_file = {
        stat.path: stat.complexity
        for stat in db.scalars(select(FileStat).where(FileStat.run_id == run_id)).all()
    }

    updated = 0
    for finding in findings:
        prediction = predict_finding(
            finding_type=finding.type,
            category=finding.category,
            confidence=finding.confidence,
            file_complexity=complexity_by_file.get(finding.file),
        )
        finding.risk_score = prediction.risk_score
        finding.severity_predicted = prediction.severity
        finding.model_version = MODEL_VERSION
        updated += 1
    db.commit()
    return updated
