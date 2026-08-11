"""Repository profiler: language detection, manifests, structure, ignore rules."""

from __future__ import annotations

import json
from pathlib import Path

IGNORE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "out",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".coverage",
    "coverage",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".cache",
    ".idea",
    ".vscode",
    "site-packages",
    ".eggs",
    "htmlcov",
    ".gradle",
}

IGNORE_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "Gemfile.lock",
    "composer.lock",
    "Cargo.lock",
}

EXT_LANGUAGES = {
    ".py": ("python", "Python"),
    ".pyi": ("python", "Python"),
    ".js": ("javascript", "JavaScript"),
    ".jsx": ("javascript", "JavaScript"),
    ".mjs": ("javascript", "JavaScript"),
    ".cjs": ("javascript", "JavaScript"),
    ".ts": ("typescript", "TypeScript"),
    ".tsx": ("typescript", "TypeScript"),
    ".html": ("html", "HTML"),
    ".css": ("css", "CSS"),
    ".json": ("json", "JSON"),
    ".md": ("markdown", "Markdown"),
}

MANIFEST_PATTERNS = {
    "package.json": "npm",
    "pyproject.toml": "pyproject",
    "setup.py": "setuptools",
    "setup.cfg": "setuptools",
    "requirements.txt": "pip-requirements",
    "Pipfile": "pipenv",
    "go.mod": "go",
    "Cargo.toml": "cargo",
    "Gemfile": "bundler",
    "pom.xml": "maven",
    "build.gradle": "gradle",
}

FRAMEWORK_MARKERS = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "tornado": "Tornado",
    "express": "Express",
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "svelte": "Svelte",
}

SUPPORTED_LANGUAGES = {"python", "javascript", "typescript"}


def iter_source_files(workspace: Path):
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if path.name in IGNORE_FILES:
            continue
        yield path


def detect_languages(workspace: Path) -> dict:
    langs: dict[str, dict] = {}
    total_loc = 0
    total_files = 0
    for path in iter_source_files(workspace):
        total_files += 1
        ext = path.suffix.lower()
        key, label = EXT_LANGUAGES.get(ext, ("other", "Other"))
        entry = langs.setdefault(
            key, {"label": label, "files": 0, "loc": 0, "supported": key in SUPPORTED_LANGUAGES}
        )
        entry["files"] += 1
        try:
            loc = sum(1 for _ in path.open("r", errors="ignore"))
            entry["loc"] += loc
            total_loc += loc
        except OSError:
            pass
    return langs


def detect_manifests(workspace: Path) -> list[dict]:
    manifests = []
    for path in iter_source_files(workspace):
        if path.name in MANIFEST_PATTERNS:
            manifests.append(
                {"path": str(path.relative_to(workspace)), "kind": MANIFEST_PATTERNS[path.name]}
            )
    return manifests


def detect_frameworks(workspace: Path, manifests: list[dict]) -> list[str]:
    found: set[str] = set()
    for manifest in manifests:
        rel = manifest["path"]
        if rel == "package.json":
            path = workspace / rel
            try:
                data = json.loads(path.read_text(errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            for dep in deps:
                for marker, label in FRAMEWORK_MARKERS.items():
                    if marker in dep.lower():
                        found.add(label)
    for path in iter_source_files(workspace):
        if path.suffix.lower() != ".py":
            continue
        try:
            text = path.read_text(errors="ignore")[:200_000]
        except OSError:
            continue
        for marker, label in FRAMEWORK_MARKERS.items():
            if f"import {marker}" in text or f"from {marker}" in text:
                found.add(label)
    return sorted(found)


def profile_repository(workspace: Path) -> dict:
    languages = detect_languages(workspace)
    manifests = detect_manifests(workspace)
    frameworks = detect_frameworks(workspace, manifests)
    top_level = sorted(
        p.name
        for p in workspace.iterdir()
        if p.is_dir() and p.name not in IGNORE_DIRS and not p.name.startswith(".")
    )
    return {
        "languages": languages,
        "manifests": manifests,
        "frameworks": frameworks,
        "top_level_dirs": top_level,
        "supported_languages": sorted(
            lang for lang, info in languages.items() if info["supported"]
        ),
    }
