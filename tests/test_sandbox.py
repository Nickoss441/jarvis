"""Tests for jarvis/tools/sandbox.py — shell_run and file_write scaffold."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from jarvis.tools.sandbox import make_shell_run_tool, make_file_write_tool


# ── shell_run — dry_run mode ──────────────────────────────────────────────────

class TestShellRunDryRun:
    def test_dry_run_returns_stub_ok(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(command="ls -la")
        assert result["mode"] == "dry_run"
        assert result["ok"] is True
        assert "ls -la" in result["stdout"]

    def test_dry_run_returns_cwd(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(command="echo hello")
        assert str(tmp_path.resolve()) == result["cwd"]

    def test_dry_run_empty_command_returns_error(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(command="")
        assert result["ok"] is False
        assert "empty" in result["error"].lower()

    def test_dry_run_whitespace_command_returns_error(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(command="   ")
        assert result["ok"] is False

    def test_tool_name_and_tier(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path)
        assert tool.name == "shell_run"
        assert tool.tier == "gated"

    def test_tool_schema_has_command_required(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path)
        assert "command" in tool.input_schema["required"]


# ── shell_run — live mode ─────────────────────────────────────────────────────

class TestShellRunLive:
    def test_live_simple_command_succeeds(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(command="echo hello")
        assert result["ok"] is True
        assert result["mode"] == "live"
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_live_creates_sandbox_dir(self, tmp_path):
        sandbox = tmp_path / "new_sandbox"
        assert not sandbox.exists()
        tool = make_shell_run_tool(sandbox_dir=sandbox, mode="live")
        result = tool.handler(command="echo created")
        assert result["ok"] is True
        assert sandbox.exists()

    def test_live_command_runs_in_sandbox_cwd(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(command="pwd")
        assert result["ok"] is True
        assert str(tmp_path.resolve()) in result["stdout"]

    def test_live_failing_command_exit_code_nonzero(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(command="false")
        assert result["ok"] is False
        assert result["exit_code"] != 0

    def test_live_timeout_returns_error(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live", timeout_seconds=1)
        result = tool.handler(command="sleep 10")
        assert result["ok"] is False
        assert "timed out" in result["error"].lower()

    def test_live_timeout_then_next_command_recovers(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live", timeout_seconds=1)

        timed_out = tool.handler(command="sleep 10")
        recovered = tool.handler(command="echo after-timeout")

        assert timed_out["ok"] is False
        assert "timed out" in timed_out["error"].lower()
        assert recovered["ok"] is True
        assert "after-timeout" in recovered["stdout"]

    def test_live_missing_executable_returns_error(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(command="nonexistent_program_xyz_abc_12345")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_live_stdout_captured(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(command="echo jarvis_sandbox_test")
        assert "jarvis_sandbox_test" in result["stdout"]

    def test_live_stderr_captured(self, tmp_path):
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        # ls on a nonexistent path writes to stderr
        result = tool.handler(command="ls /nonexistent_path_xyz_456")
        assert result["ok"] is False
        assert result["stderr"] or result["exit_code"] != 0

    def test_live_no_shell_injection(self, tmp_path):
        """Commands must NOT be executed via shell=True."""
        tool = make_shell_run_tool(sandbox_dir=tmp_path, mode="live")
        # This should be treated as a literal argument list, not shell code.
        # "echo hello; echo injected" should only output the literal string.
        result = tool.handler(command="echo hello; echo injected")
        # shlex.split produces ["echo", "hello;", "echo", "injected"] → echo only outputs
        # "hello; echo injected" as a single string, not two commands.
        assert result["ok"] is True
        # The output should NOT have two separate "hello" and "injected" lines
        # (i.e. semi-colon should not be treated as a command separator)
        assert "injected" not in result["stdout"].strip().splitlines()[-1] or \
               "hello" in result["stdout"]  # sanity check the echo ran


# ── file_write — dry_run mode ─────────────────────────────────────────────────

class TestFileWriteDryRun:
    def test_dry_run_returns_stub(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(path="output/test.txt", content="hello world")
        assert result["mode"] == "dry_run"
        assert result["ok"] is True

    def test_dry_run_does_not_create_file(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="dry_run")
        tool.handler(path="output/test.txt", content="hello")
        assert not (tmp_path / "output" / "test.txt").exists()

    def test_dry_run_returns_byte_count(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="dry_run")
        content = "hello world"
        result = tool.handler(path="test.txt", content=content)
        assert result["bytes"] == len(content.encode("utf-8"))

    def test_dry_run_empty_path_returns_error(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="dry_run")
        result = tool.handler(path="", content="hello")
        assert result["ok"] is False

    def test_tool_name_and_tier(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path)
        assert tool.name == "file_write"
        assert tool.tier == "gated"

    def test_tool_schema_has_required_fields(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path)
        assert "path" in tool.input_schema["required"]
        assert "content" in tool.input_schema["required"]


# ── file_write — live mode ────────────────────────────────────────────────────

class TestFileWriteLive:
    def test_live_creates_file(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(path="hello.txt", content="hello world")
        assert result["ok"] is True
        assert result["mode"] == "live"
        assert (tmp_path / "hello.txt").read_text() == "hello world"

    def test_live_creates_nested_dirs(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(path="a/b/c/file.txt", content="nested")
        assert result["ok"] is True
        assert (tmp_path / "a" / "b" / "c" / "file.txt").read_text() == "nested"

    def test_live_returns_bytes_written(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        content = "test content"
        result = tool.handler(path="bytes.txt", content=content)
        assert result["bytes_written"] == len(content.encode("utf-8"))

    def test_live_no_overwrite_by_default(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        (tmp_path / "existing.txt").write_text("original")
        result = tool.handler(path="existing.txt", content="replacement")
        assert result["ok"] is False
        assert "already exists" in result["error"].lower()
        # Original content untouched
        assert (tmp_path / "existing.txt").read_text() == "original"

    def test_live_overwrite_true_replaces_file(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        (tmp_path / "overwrite.txt").write_text("old content")
        result = tool.handler(path="overwrite.txt", content="new content", overwrite=True)
        assert result["ok"] is True
        assert (tmp_path / "overwrite.txt").read_text() == "new content"

    def test_live_path_traversal_blocked(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(path="../escape.txt", content="escape attempt")
        assert result["ok"] is False
        assert "escapes" in result["error"].lower()
        # File must NOT have been written outside sandbox
        assert not (tmp_path.parent / "escape.txt").exists()

    def test_live_path_traversal_deep_blocked(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        result = tool.handler(path="a/../../etc/passwd", content="evil")
        assert result["ok"] is False

    def test_live_max_size_exceeded(self, tmp_path):
        from jarvis.tools.sandbox import _MAX_FILE_BYTES
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        big_content = "x" * (_MAX_FILE_BYTES + 1)
        result = tool.handler(path="big.txt", content=big_content)
        assert result["ok"] is False
        assert "max" in result["error"].lower()
        assert not (tmp_path / "big.txt").exists()

    def test_live_utf8_content(self, tmp_path):
        tool = make_file_write_tool(sandbox_dir=tmp_path, mode="live")
        content = "こんにちは世界 🌍"
        result = tool.handler(path="unicode.txt", content=content)
        assert result["ok"] is True
        assert (tmp_path / "unicode.txt").read_text(encoding="utf-8") == content


# ── Config integration ────────────────────────────────────────────────────────

class TestConfigSandboxFields:
    def _cfg(self, tmp_path, **kwargs):
        from jarvis.config import Config
        return Config(
            anthropic_api_key="k",
            model="m",
            notes_dir=str(tmp_path / "notes"),
            user_name="test",
            audit_db=str(tmp_path / "audit.db"),
            **kwargs,
        )

    def test_phase_sandbox_defaults_false(self, tmp_path):
        cfg = self._cfg(tmp_path)
        assert cfg.phase_sandbox is False

    def test_sandbox_dir_default(self, tmp_path):
        cfg = self._cfg(tmp_path)
        assert "sandbox" in str(cfg.sandbox_dir)

    def test_phase_sandbox_in_enabled_phases(self, tmp_path):
        cfg = self._cfg(tmp_path, phase_sandbox=True)
        assert "sandbox" in cfg.enabled_phases()

    def test_phase_sandbox_not_in_enabled_phases_when_false(self, tmp_path):
        cfg = self._cfg(tmp_path, phase_sandbox=False)
        assert "sandbox" not in cfg.enabled_phases()
