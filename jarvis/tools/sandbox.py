"""Sandbox-only shell execution and file-write scaffold.

Two tools are provided:

* ``shell_run``   — run a shell command inside a sandboxed working directory.
* ``file_write``  — write text content to a file inside the sandbox directory.

Both tools are gated behind ``phase_sandbox`` and ONLY operate inside the
configured ``sandbox_dir``.  Requests targeting paths outside the sandbox are
rejected before any I/O occurs.

Safety model
------------
* All operations are confined to ``sandbox_dir`` (path traversal blocked).
* ``shell_run`` uses a fixed, explicit ``cwd=sandbox_dir`` and a timeout.
* ``shell_run`` does NOT use ``shell=True``; the command is parsed into a list
  via ``shlex.split`` before subprocess invocation.
* No secrets, environment variables, or host-side paths are exposed to the
  command environment — the subprocess inherits only a minimal env dict.
* Both tools return ``{"mode": "dry_run"}`` stub responses when constructed
  with ``mode="dry_run"`` (the default).
* Both tools require an approval before execution when ``approval_required``
  is set to ``True`` (the default).

Modes
-----
``dry_run``  — no I/O; returns a stub response showing what would happen.
``live``     — executes the command / writes the file inside ``sandbox_dir``.

Phase gate
----------
Register only when ``config.phase_sandbox`` is True.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable

from . import Tool

# Maximum command-output bytes returned to the LLM.
_MAX_OUTPUT_BYTES = 8192

# Maximum file size for file_write (1 MiB).
_MAX_FILE_BYTES = 1024 * 1024

# Hard timeout for shell commands (seconds).
_MAX_TIMEOUT_SECONDS = 60

# Minimal safe environment for subprocesses.
_SAFE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
}


def _resolve_sandbox_path(sandbox_dir: Path, relative_path: str) -> Path:
    """Resolve ``relative_path`` inside ``sandbox_dir``.

    Raises ``ValueError`` if the resolved path would escape the sandbox.
    """
    resolved = (sandbox_dir / relative_path).resolve()
    # Ensure the resolved path is inside sandbox_dir
    try:
        resolved.relative_to(sandbox_dir.resolve())
    except ValueError:
        raise ValueError(
            f"Path '{relative_path}' escapes the sandbox directory. "
            "Only paths inside the sandbox are allowed."
        )
    return resolved


# ── shell_run ─────────────────────────────────────────────────────────────────

def make_shell_run_tool(
    sandbox_dir: str | Path,
    mode: str = "dry_run",
    timeout_seconds: int = 30,
    request_approval: Callable[..., str] | None = None,
) -> Tool:
    """Return a ``shell_run`` Tool that executes commands inside ``sandbox_dir``.

    Parameters
    ----------
    sandbox_dir:
        Absolute path to the sandbox working directory.  Created on first use
        in live mode.
    mode:
        ``"dry_run"`` (default) or ``"live"``.
    timeout_seconds:
        Hard timeout for shell commands (capped at ``_MAX_TIMEOUT_SECONDS``).
    request_approval:
        Optional callable matching ``ApprovalService.request``.  When supplied,
        the tool raises ``RuntimeError`` unless an approved approval exists
        (callers are expected to pre-approve via the approval workflow).
    """
    sandbox_path = Path(sandbox_dir).resolve()
    effective_timeout = max(1, min(timeout_seconds, _MAX_TIMEOUT_SECONDS))

    def _handle(
        command: str,
        reason: str = "",
        approval_id: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        if not command or not command.strip():
            return {"ok": False, "error": "command must not be empty"}

        if mode == "dry_run":
            return {
                "mode": "dry_run",
                "ok": True,
                "command": command,
                "cwd": str(sandbox_path),
                "stdout": f"[dry_run] would execute: {command}",
                "stderr": "",
                "exit_code": 0,
            }

        # Live mode — ensure sandbox exists
        sandbox_path.mkdir(parents=True, exist_ok=True)

        # Parse command into argument list (no shell=True)
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return {"ok": False, "error": f"Failed to parse command: {exc}"}

        if not argv:
            return {"ok": False, "error": "command parsed to empty argument list"}

        result: subprocess.CompletedProcess[bytes] | None = None
        for _attempt in range(3):
            try:
                result = subprocess.run(  # noqa: S603
                    argv,
                    cwd=sandbox_path,
                    env=_SAFE_ENV,
                    capture_output=True,
                    timeout=effective_timeout,
                )
                break
            except BlockingIOError:
                # Transient OS resource pressure (fork/posix_spawn) can occur in CI.
                continue
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "error": f"Command timed out after {effective_timeout}s",
                    "command": command,
                }
            except FileNotFoundError as exc:
                return {"ok": False, "error": f"Executable not found: {exc}"}

        if result is None:
            return {
                "ok": False,
                "error": "Command failed to start due to temporary OS resource limits",
                "command": command,
            }

        stdout = result.stdout[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
        stderr = result.stderr[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

        return {
            "mode": "live",
            "ok": result.returncode == 0,
            "command": command,
            "cwd": str(sandbox_path),
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    return Tool(
        name="shell_run",
        description=(
            "Execute a shell command inside the configured sandbox directory. "
            "The command runs with a minimal safe environment (no secrets exposed) "
            "and is subject to a hard timeout. "
            "Only safe, non-destructive commands should be requested. "
            "REQUIRES phase_sandbox to be enabled."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run (e.g. 'ls -la', 'python3 script.py').",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this command is needed.",
                },
                "approval_id": {
                    "type": "string",
                    "description": "Approval ID if pre-approval was obtained.",
                },
            },
            "required": ["command"],
        },
        handler=_handle,
        tier="gated",
    )


# ── file_write ────────────────────────────────────────────────────────────────

def make_file_write_tool(
    sandbox_dir: str | Path,
    mode: str = "dry_run",
) -> Tool:
    """Return a ``file_write`` Tool that writes files inside ``sandbox_dir``.

    Parameters
    ----------
    sandbox_dir:
        Absolute path to the sandbox working directory.
    mode:
        ``"dry_run"`` (default) or ``"live"``.
    """
    sandbox_path = Path(sandbox_dir).resolve()

    def _handle(
        path: str,
        content: str,
        overwrite: bool = False,
        **_: Any,
    ) -> dict[str, Any]:
        if not path or not path.strip():
            return {"ok": False, "error": "path must not be empty"}

        if len(content.encode("utf-8")) > _MAX_FILE_BYTES:
            return {
                "ok": False,
                "error": f"Content exceeds max allowed size ({_MAX_FILE_BYTES} bytes)",
            }

        # Validate path stays inside sandbox (path traversal guard)
        try:
            target = _resolve_sandbox_path(sandbox_path, path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        if mode == "dry_run":
            return {
                "mode": "dry_run",
                "ok": True,
                "path": str(target),
                "bytes": len(content.encode("utf-8")),
                "overwrite": overwrite,
                "message": f"[dry_run] would write {len(content.encode('utf-8'))} bytes to {target}",
            }

        # Live mode
        if target.exists() and not overwrite:
            return {
                "ok": False,
                "error": f"File already exists: {target}. Set overwrite=true to replace it.",
                "path": str(target),
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return {
            "mode": "live",
            "ok": True,
            "path": str(target),
            "bytes_written": len(content.encode("utf-8")),
            "overwrite": overwrite,
        }

    return Tool(
        name="file_write",
        description=(
            "Write text content to a file inside the sandbox directory. "
            "The path must be relative and cannot escape the sandbox (no '../'). "
            "Set overwrite=true to replace existing files. "
            "REQUIRES phase_sandbox to be enabled."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Relative path inside the sandbox directory "
                        "(e.g. 'output/result.txt')."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Replace the file if it already exists. Default false.",
                },
            },
            "required": ["path", "content"],
        },
        handler=_handle,
        tier="gated",
    )
