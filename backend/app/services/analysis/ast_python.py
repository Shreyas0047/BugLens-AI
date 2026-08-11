"""Custom Python AST analyzer: deterministic pattern-based defect discovery.

Runs on every Python file regardless of external tool availability.
Every finding is labelled a *potential* issue with a confidence value;
confidence is a heuristic, documented per-rule, never a proof.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

_SQL_KEYWORDS = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|MERGE|UNION)\b", re.IGNORECASE
)
_SECRET_KEYWORDS = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|auth[_-]?key"
    r"|client[_-]?secret|aws[_-]?secret)\b"
)
_SECRET_LITERAL = re.compile(r"(?i)^(secret|token|key|password|passwd)(\W|$)")
_DANGEROUS_CALLS = {
    "eval": ("DANGEROUS_EVAL", "SECURITY", 0.75),
    "exec": ("DANGEROUS_EVAL", "SECURITY", 0.75),
    "pickle.loads": ("DANGEROUS_DESERIALIZATION", "SECURITY", 0.9),
    "pickle.load": ("DANGEROUS_DESERIALIZATION", "SECURITY", 0.9),
    "cPickle.loads": ("DANGEROUS_DESERIALIZATION", "SECURITY", 0.9),
    "yaml.load": ("DANGEROUS_DESERIALIZATION", "SECURITY", 0.8),
    "os.system": ("UNSAFE_SUBPROCESS", "SECURITY", 0.8),
    "os.popen": ("UNSAFE_SUBPROCESS", "SECURITY", 0.8),
    "subprocess.Popen": ("UNSAFE_SUBPROCESS", "SECURITY", 0.6),
    "hashlib.md5": ("WEAK_HASH", "SECURITY", 0.5),
    "hashlib.sha1": ("WEAK_HASH", "SECURITY", 0.5),
}
_RULE_DOCS = {
    "SQL_STRING_CONCAT": (
        "SQL_INJECTION",
        "SECURITY",
        0.85,
        "A query-looking string is built with concatenation or f-strings. If any part comes from "
        "user input, this is a SQL injection sink. Parameterized queries are required.",
    ),
    "SQL_FSTRING": (
        "SQL_INJECTION",
        "SECURITY",
        0.8,
        "An f-string interpolates values into a SQL query. Interpolated user input would be a "
        "SQL injection; use parameterized queries.",
    ),
    "UNSAFE_SUBPROCESS_SHELL": (
        "UNSAFE_SUBPROCESS",
        "SECURITY",
        0.8,
        "subprocess invoked with shell=True. If arguments contain user input, shell metacharacters "
        "can be injected; prefer argument lists without a shell.",
    ),
    "NONE_COMPARISON": (
        "NONE_COMPARISON",
        "CORRECTNESS",
        0.7,
        "Comparing with '==' (or '!=') to None instead of 'is'/'is not None'. This usually works "
        "but violates Python convention and can mask custom __eq__ behavior.",
    ),
    "CONSTANT_CONDITION": (
        "CONSTANT_CONDITION",
        "CORRECTNESS",
        0.9,
        "Condition is a constant, so a branch is always taken. "
        "Likely leftover debug code or a bug.",
    ),
    "SELF_COMPARISON": (
        "SELF_COMPARISON",
        "CORRECTNESS",
        0.95,
        "Expression compared with itself; the condition is always False (or True).",
    ),
    "UNREACHABLE_CODE": (
        "UNREACHABLE_CODE",
        "CODE_SMELL",
        0.95,
        "Code after a return/raise/break/continue can never execute.",
    ),
    "EMPTY_EXCEPT": (
        "EMPTY_EXCEPT",
        "CODE_SMELL",
        0.7,
        "Exception handler swallows errors silently. In production this hides failures; consider "
        "logging the exception or narrowing the clause.",
    ),
    "BROAD_EXCEPT": (
        "BROAD_EXCEPT",
        "CODE_SMELL",
        0.5,
        "Bare 'except:' catches everything including KeyboardInterrupt/SystemExit, and swallows "
        "the exception object, making debugging harder.",
    ),
    "UNUSED_IMPORT": (
        "UNUSED_IMPORT",
        "CODE_SMELL",
        0.6,
        "Imported name is never referenced in this module. May be re-exported intentionally "
        "(check for __all__ / package exports).",
    ),
    "UNUSED_VARIABLE": (
        "UNUSED_VARIABLE",
        "CODE_SMELL",
        0.55,
        "Local variable assigned but never read. Could be dead code or a sign of missing logic. "
        "Underscore-prefixed names and loop targets are intentionally skipped.",
    ),
    "ASSERT_VALIDATION": (
        "ASSERT_VALIDATION",
        "CORRECTNESS",
        0.55,
        "assert used for input validation. Asserts are stripped under python -O, so validation "
        "silently disappears in optimized deployments.",
    ),
    "HARDCODED_SECRET": (
        "HARDCODED_SECRET",
        "SECURITY",
        0.65,
        "A value that looks like a credential is assigned to a secret-named variable or passed "
        "as a literal. Real secrets belong in environment variables/secret storage.",
    ),
    "REDUNDANT_ELSE": (
        "REDUNDANT_ELSE",
        "CODE_SMELL",
        0.7,
        "An else branch follows a block that always returns/raises; the else is redundant.",
    ),
}


@dataclass
class ASTFinding:
    type: str
    category: str
    line: int
    column: int
    message: str
    confidence: float
    evidence: dict = field(default_factory=dict)


def _store_targets(node: ast.AST) -> list[str]:
    """Names bound by control-flow constructs (loop/comprehension/with/except targets)."""
    targets: list[str] = []
    if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
        targets.append(node.target.id)
    elif isinstance(node, ast.comprehension) and isinstance(node.target, ast.Name):
        targets.append(node.target.id)
    elif isinstance(node, ast.With) and isinstance(node.items[0].optional_vars, ast.Name):
        targets.append(node.items[0].optional_vars.id)
    elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
        targets.append(node.name)
    return targets


def _snippet(lines: list[str], line: int, radius: int = 2) -> str:
    start = max(0, line - 1 - radius)
    end = min(len(lines), line + radius)
    return "\n".join(f"{i + 1:>5} | {lines[i]}" for i in range(start, end))


class _Visitor(ast.NodeVisitor):
    def __init__(self, lines: list[str], used_names: set[str]) -> None:
        self.lines = lines
        self.used_names = used_names
        self.findings: list[ASTFinding] = []

    # --- helpers ---------------------------------------------------------
    def add(self, rule: str, node: ast.AST, detail: str | None = None) -> None:
        ftype, category, confidence, doc = _RULE_DOCS[rule]
        self.findings.append(
            ASTFinding(
                type=ftype,
                category=category,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0),
                message=doc,
                confidence=confidence,
                evidence={
                    "rule": rule,
                    "snippet": _snippet(self.lines, getattr(node, "lineno", 0)),
                    "detail": detail or "",
                },
            )
        )

    def safe_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Attribute):
            return f"{self.safe_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Name):
            return node.id
        return ""

    def is_sql(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return bool(_SQL_KEYWORDS.search(node.value))
        if isinstance(node, ast.JoinedStr):
            return any(
                isinstance(p, ast.Constant) and _SQL_KEYWORDS.search(p.value)
                for p in node.values
                if isinstance(p, ast.Constant)
            )
        return False

    # --- visitors --------------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_unused_locals(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            bound = (alias.asname or alias.name).split(".")[0]
            if bound not in self.used_names:
                self.add("UNUSED_IMPORT", node, detail=f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            bound = alias.asname or alias.name
            if bound not in self.used_names:
                self.add("UNUSED_IMPORT", node, detail=f"from {node.module} import {alias.name}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self.safe_name(node.func)
        if name in _DANGEROUS_CALLS:
            ftype, category, confidence = _DANGEROUS_CALLS[name]
            self.findings.append(
                ASTFinding(
                    type=ftype,
                    category=category,
                    line=getattr(node, "lineno", 0),
                    column=getattr(node, "col_offset", 0),
                    message=f"Call to {name} can be a dangerous sink when input is not trusted.",
                    confidence=confidence,
                    evidence={
                        "rule": name,
                        "snippet": _snippet(self.lines, getattr(node, "lineno", 0)),
                    },
                )
            )
        if name in (
            "subprocess.run",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
        ):
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    self.add("UNSAFE_SUBPROCESS_SHELL", node)
        if name == "yaml.load":
            for kw in node.keywords:
                if (
                    kw.arg == "Loader"
                    and isinstance(kw.value, ast.Name)
                    and kw.value.id == "FullLoader"
                ):
                    return
            self.add("DANGEROUS_DESERIALIZATION", node, detail="yaml.load without a safe Loader")
        for arg in node.args:
            if isinstance(arg, ast.BinOp) and isinstance(arg.left, ast.Constant):
                if isinstance(arg.left.value, str) and _SQL_KEYWORDS.search(arg.left.value):
                    self.add("SQL_STRING_CONCAT", node, detail="SQL constructed from concatenation")
                    break
            if isinstance(arg, ast.JoinedStr) and self.is_sql(arg):
                self.add("SQL_FSTRING", node)
                break
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Add, ast.Mod)) and isinstance(node.left, ast.Constant):
            if isinstance(node.left.value, str) and _SQL_KEYWORDS.search(node.left.value):
                self.add("SQL_STRING_CONCAT", node)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        if self.is_sql(node):
            self.add("SQL_FSTRING", node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        left = node.left
        for op, right in zip(node.ops, node.comparators, strict=True):
            if isinstance(op, (ast.Eq, ast.NotEq)):
                for side in (left, right):
                    if isinstance(side, ast.Constant) and side.value is None:
                        self.add("NONE_COMPARISON", node)
                if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                    self.add("CONSTANT_CONDITION", node)
            if isinstance(op, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) and self._same_expr(
                left, right
            ):
                self.add("SELF_COMPARISON", node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Constant):
            self.add(
                "CONSTANT_CONDITION",
                node,
                detail=f"condition is always {bool(node.test.value)}",
            )
        self.generic_visit(node)
        if isinstance(node.orelse, list) and node.orelse:
            body_terminates = self._always_terminates(node.body)
            if body_terminates:
                self.add("REDUNDANT_ELSE", node)

    def visit_While(self, node: ast.While) -> None:
        if isinstance(node.test, ast.Constant) and node.test.value is False:
            self.add("CONSTANT_CONDITION", node, detail="while condition is always False")
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.add("ASSERT_VALIDATION", node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.add("BROAD_EXCEPT", node)
        if isinstance(node.body, list) and len(node.body) == 1:
            stmt = node.body[0]
            if isinstance(stmt, ast.Pass):
                self.add("EMPTY_EXCEPT", node)
            if isinstance(stmt, ast.Raise):
                return
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                name = self.safe_name(stmt.value.func)
                if name in ("print", "pass"):
                    self.add("EMPTY_EXCEPT", node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and _SECRET_KEYWORDS.search(target.id):
                for value_node in ast.walk(node.value):
                    if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                        if value_node.value and _SECRET_LITERAL.match(value_node.value):
                            self.add("HARDCODED_SECRET", node, detail=f"assigned to {target.id}")
                            break
        self.generic_visit(node)

    visit_AnnAssign = visit_Assign

    # --- structural helpers ----------------------------------------------
    def _same_expr(self, a: ast.AST, b: ast.AST) -> bool:
        return ast.dump(a) == ast.dump(b)

    def _always_terminates(self, stmts: list[ast.stmt]) -> bool:
        return bool(stmts) and isinstance(
            stmts[-1], (ast.Return, ast.Raise, ast.Break, ast.Continue)
        )

    def _check_unused_locals(self, node: ast.FunctionDef) -> None:
        assigned: dict[str, ast.AST] = {}
        loaded: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store) and child.id not in assigned:
                    assigned[child.id] = child
                elif isinstance(child.ctx, ast.Load):
                    loaded.add(child.id)

        control_targets: set[str] = set()
        for child in ast.walk(node):
            for target in _store_targets(child):
                control_targets.add(target)

        for name, name_node in assigned.items():
            if name in loaded or name in control_targets or name.startswith("_"):
                continue
            self.findings.append(
                ASTFinding(
                    type="UNUSED_VARIABLE",
                    category="CODE_SMELL",
                    line=getattr(name_node, "lineno", 0),
                    column=getattr(name_node, "col_offset", 0),
                    message=_RULE_DOCS["UNUSED_VARIABLE"][3],
                    confidence=_RULE_DOCS["UNUSED_VARIABLE"][2],
                    evidence={
                        "rule": "UNUSED_VARIABLE",
                        "name": name,
                        "function": node.name,
                        "snippet": _snippet(self.lines, getattr(name_node, "lineno", 0)),
                    },
                )
            )

    # --- dead code detection ----------------------------------------------
    def visit_Module(self, node: ast.Module) -> None:
        for parent in ast.walk(node):
            for _field_name, child in ast.iter_fields(parent):
                if isinstance(child, list):
                    for i, stmt in enumerate(child):
                        if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                            for after in child[i + 1 :]:
                                if not isinstance(after, ast.stmt):
                                    continue
                                self.findings.append(
                                    ASTFinding(
                                        type="UNREACHABLE_CODE",
                                        category="CODE_SMELL",
                                        line=getattr(after, "lineno", 0),
                                        column=getattr(after, "col_offset", 0),
                                        message=_RULE_DOCS["UNREACHABLE_CODE"][3],
                                        confidence=_RULE_DOCS["UNREACHABLE_CODE"][2],
                                        evidence={
                                            "rule": "UNREACHABLE_CODE",
                                            "snippet": _snippet(
                                                self.lines, getattr(after, "lineno", 0)
                                            ),
                                        },
                                    )
                                )
        self.generic_visit(node)


def analyze_python_file(path) -> list[ASTFinding]:
    """Analyze one Python file. Returns [] on any parse/IO failure (reported separately)."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    lines = source.splitlines()
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    used_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)

    visitor = _Visitor(lines, used_names)
    visitor.visit(tree)
    return visitor.findings


def analyze_python_tree(root) -> dict:
    """Analyze every .py file under root. Returns {path: [ASTFinding, ...]}."""
    from app.services.profiler.detect import iter_source_files

    results: dict[str, list[ASTFinding]] = {}
    for path in iter_source_files(root):
        if path.suffix.lower() not in (".py", ".pyi"):
            continue
        findings = analyze_python_file(path)
        if findings:
            results[str(path.relative_to(root))] = findings
    return results
