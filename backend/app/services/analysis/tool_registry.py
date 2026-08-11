"""Tool registry: probe availability, run analyzers in isolated subprocesses.

Every external analyzer runs with:
  - a hard timeout (configurable per tool)
  - a scrubbed environment (no user API keys / secrets)
  - resource limits (virtual memory, CPU) via preexec
  - a working directory inside the analysis workspace

A tool that is missing or misbehaves degrades gracefully: the run continues
and the report records the tool as unavailable.
"""

from __future__ import annotations

import json
import resource
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 90
MAX_OUTPUT_BYTES = 50 * 1024 * 1024

# Nothing from the user's environment leaks into analyzer subprocesses.
# The active environment's bin dir is prepended so project-installed
# analyzers (bandit/ruff/radon) are reachable from the venv.
_VENV_BIN = str(Path(sys.prefix) / "bin")
_SAFE_ENV = {
    "PATH": f"{_VENV_BIN}:/usr/bin:/bin:/usr/local/bin",
    "HOME": str(Path.home()),
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NO_COLOR": "1",
}


class ToolError(Exception):
    pass


def _limits() -> None:
    """Resource caps applied inside the analyzer subprocess (before exec)."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    except (ValueError, OSError):
        pass


@dataclass
class ToolResult:
    name: str
    available: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str | None = None
    parsed: dict | list | None = field(default=None)


def is_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_tool(
    name: str,
    argv: list[str],
    cwd: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    json_output: bool = False,
) -> ToolResult:
    """Run an external analyzer. Returns ToolResult; never raises for tool failures."""
    if not is_available(argv[0]):
        return ToolResult(name=name, available=False, error=f"{argv[0]} not found on PATH")

    proc = None
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=_SAFE_ENV,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=_limits,
            check=False,
        )
        result = ToolResult(
            name=name,
            available=True,
            exit_code=proc.returncode,
            stdout=proc.stdout[:MAX_OUTPUT_BYTES],
            stderr=proc.stderr[:MAX_OUTPUT_BYTES],
        )
        if json_output and result.stdout.strip():
            try:
                result.parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                result.error = "Tool output was not valid JSON"
        return result
    except subprocess.TimeoutExpired as exc:
        return ToolResult(
            name=name,
            available=True,
            timed_out=True,
            error=f"Timed out after {timeout}s",
            stdout=(exc.stdout or "")[:MAX_OUTPUT_BYTES] if isinstance(exc.stdout, str) else "",
        )
    except OSError as exc:
        return ToolResult(name=name, available=True, error=f"Failed to start: {exc}")


def is_json_result(result: ToolResult) -> bool:
    return result.parsed is not None
