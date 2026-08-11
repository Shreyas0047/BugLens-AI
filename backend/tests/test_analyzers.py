from pathlib import Path

from app.services.analysis.ast_python import analyze_python_file
from app.services.analysis.dup_detect import analyze_duplicates
from app.services.analysis.predict import predict_finding
from app.services.analysis.runners.jsts import _ESLINT_CATEGORY


class TestPredict:
    def test_sql_injection_is_high(self):
        p = predict_finding("SQL_INJECTION", "SECURITY", 0.85, None)
        assert p.severity == "high"
        assert 0.7 < p.risk_score < 0.9

    def test_hardcoded_secret_in_complex_file_is_critical(self):
        p = predict_finding("HARDCODED_SECRET", "SECURITY", 0.85, 12.0)
        assert p.severity == "critical"
        assert p.risk_score >= 0.8

    def test_unused_variable_is_low(self):
        p = predict_finding("UNUSED_VARIABLE", "CODE_SMELL", 0.5, None)
        assert p.severity == "low"
        assert p.risk_score < 0.5

    def test_self_comparison_is_critical(self):
        p = predict_finding("SELF_COMPARISON", "CORRECTNESS", 0.9, 3.0)
        assert p.severity == "critical"
        assert p.risk_score >= 0.8

    def test_confidence_zero_floors_at_half(self):
        p = predict_finding("UNUSED_CLASS", "CODE_SMELL", 0.0, None)
        assert p.risk_score == 0.5
        assert p.severity == "medium"

    def test_clamped_high(self):
        p = predict_finding("SELF_COMPARISON", "CORRECTNESS", 1.0, 20.0)
        assert p.risk_score <= 0.98


class TestEslintCategories:
    def test_security_rules_map_to_security(self):
        assert _ESLINT_CATEGORY["no-eval"] == "SECURITY"
        assert _ESLINT_CATEGORY["no-implied-eval"] == "SECURITY"
        assert _ESLINT_CATEGORY["no-new-func"] == "SECURITY"

    def test_smell_rules(self):
        assert _ESLINT_CATEGORY["no-debugger"] == "CODE_SMELL"
        assert _ESLINT_CATEGORY["no-unused-vars"] == "CODE_SMELL"

    def test_correctness_rules(self):
        assert _ESLINT_CATEGORY["no-dupe-keys"] == "CORRECTNESS"
        assert _ESLINT_CATEGORY["no-self-compare"] == "CORRECTNESS"

    def test_unknown_rule_falls_back(self):
        assert _ESLINT_CATEGORY.get("no-such-rule", "CORRECTNESS") == "CORRECTNESS"


class TestAstPythonAnalyzer:
    def test_sql_injection_detected(self, tmp_path: Path):
        source = (
            "import sqlite3\n"
            "def query(user_id):\n"
            "    conn = sqlite3.connect('app.db')\n"
            '    cur = conn.execute("SELECT * FROM users WHERE id=\'" + user_id + "\'")\n'
            "    return cur.fetchall()\n"
        )
        f = tmp_path / "app.py"
        f.write_text(source)
        findings = analyze_python_file(f)
        types = {fn.type for fn in findings}
        assert "SQL_INJECTION" in types

    def test_assert_validation_detected(self, tmp_path: Path):
        source = (
            "def login(username, password):\n"
            "    assert username and password, 'missing credentials'\n"
            "    return authenticate(username, password)\n"
        )
        f = tmp_path / "auth.py"
        f.write_text(source)
        findings = analyze_python_file(f)
        types = {fn.type for fn in findings}
        assert "ASSERT_VALIDATION" in types

    def test_unused_variable_detected(self, tmp_path: Path):
        source = "def compute():\n    result = 42\n    return 0\n"
        f = tmp_path / "calc.py"
        f.write_text(source)
        findings = analyze_python_file(f)
        types = {fn.type for fn in findings}
        assert "UNUSED_VARIABLE" in types

    def test_clean_file_has_no_findings(self, tmp_path: Path):
        source = "def add(a, b):\n    return a + b\n"
        f = tmp_path / "clean.py"
        f.write_text(source)
        findings = analyze_python_file(f)
        assert findings == []


class TestDuplicateDetection:
    BODY = (
        "def compute(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        if item.is_valid():\n"
        "            total += item.value\n"
        "        else:\n"
        "            total -= item.penalty\n"
        "    return total\n"
    )

    def test_identical_bodies_in_two_files(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(self.BODY.replace("compute", "calc_a"))
        (tmp_path / "b.py").write_text(self.BODY.replace("compute", "calc_b"))
        findings = analyze_duplicates([tmp_path / "a.py", tmp_path / "b.py"])
        types = {f["type"] for f in findings}
        assert "DUPLICATE_FUNCTION" in types
        assert len(findings) == 2

    def test_renamed_variables_still_match(self, tmp_path: Path):
        a = self.BODY
        b = (
            "def recompute(rows):\n"
            "    acc = 0\n"
            "    for row in rows:\n"
            "        if row.is_valid():\n"
            "            acc += row.value\n"
            "        else:\n"
            "            acc -= row.penalty\n"
            "    return acc\n"
        )
        (tmp_path / "a.py").write_text(a)
        (tmp_path / "b.py").write_text(b)
        findings = analyze_duplicates([tmp_path / "a.py", tmp_path / "b.py"])
        assert any(f["type"] == "DUPLICATE_FUNCTION" for f in findings)

    def test_distinct_bodies_no_findings(self, tmp_path: Path):
        (tmp_path / "a.py").write_text(
            "def parse(text):\n"
            "    parts = text.split(':')\n"
            "    return {'left': parts[0], 'right': parts[1]}\n"
        )
        (tmp_path / "b.py").write_text(
            "def render(node):\n"
            "    html = '<div>'\n"
            "    for child in node.children:\n"
            "        html += child.text\n"
            "    return html + '</div>'\n"
        )
        findings = analyze_duplicates([tmp_path / "a.py", tmp_path / "b.py"])
        assert findings == []

    def test_trivial_short_bodies_ignored(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("def one():\n    return 1\n")
        (tmp_path / "b.py").write_text("def two():\n    return 2\n")
        findings = analyze_duplicates([tmp_path / "a.py", tmp_path / "b.py"])
        assert findings == []
