"""Tests for the app_status tool."""
import json
import platform
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from jarvis.tools.app_status import make_app_status_tool


class TestAppStatusDryRun:
    """Tests for app_status in dry_run mode."""

    def test_app_status_dry_run_installed_app(self):
        """Dry-run mode returns mock status for allowlisted apps."""
        tool = make_app_status_tool(mode="dry_run")
        handler = tool["handler"]
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["installed"] is True
        assert result["version"] == "1.0.0 (dry-run mock)"

    def test_app_status_dry_run_all_allowlisted_apps(self):
        """Dry-run handles all allowlisted apps."""
        tool = make_app_status_tool(mode="dry_run")
        handler = tool["handler"]
        
        for app in ["arc", "spotify", "visual studio code", "google chrome", "slack"]:
            result = handler(app=app)
            assert result["ok"] is True
            assert result["installed"] is True
            assert result["version"] == "1.0.0 (dry-run mock)"

    def test_app_status_dry_run_case_insensitive(self):
        """Dry-run matches app names case-insensitively."""
        tool = make_app_status_tool(mode="dry_run")
        handler = tool["handler"]
        
        result = handler(app="SPOTIFY")
        assert result["ok"] is True
        assert result["app"] == "Spotify"

    def test_app_status_dry_run_not_allowlisted(self):
        """Dry-run rejects non-allowlisted apps."""
        tool = make_app_status_tool(mode="dry_run")
        handler = tool["handler"]
        
        result = handler(app="nonexistent")
        assert result["ok"] is False
        assert result["error"] == "app_not_allowlisted"


class TestAppStatusLive:
    """Tests for app_status in live mode."""

    def test_app_status_live_not_macos(self):
        """Live mode fails gracefully on non-macOS."""
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        with patch("jarvis.tools.app_status.platform.system", return_value="Linux"):
            result = handler(app="spotify")
            assert result["ok"] is False
            assert result["error"] == "not_macos"

    def test_app_status_live_not_allowlisted(self):
        """Live mode rejects non-allowlisted apps."""
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="nonexistent")
        assert result["ok"] is False
        assert result["error"] == "app_not_allowlisted"

    @patch("jarvis.tools.app_status.platform.system")
    @patch("jarvis.tools.app_status.subprocess.run")
    def test_app_status_live_app_not_installed(self, mock_run, mock_platform):
        """Live mode returns installed=False when mdfind returns nothing."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["installed"] is False
        assert result["version"] is None

    @patch("jarvis.tools.app_status.platform.system")
    @patch("jarvis.tools.app_status.subprocess.run")
    def test_app_status_live_app_installed_with_version(self, mock_run, mock_platform):
        """Live mode detects installed app and its version."""
        mock_platform.return_value = "Darwin"
        
        # First call: mdfind for app path
        # Second call: mdls for version
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if "mdfind" in cmd:
                return MagicMock(stdout="/Applications/Spotify.app", stderr="", returncode=0)
            elif "mdls" in cmd:
                return MagicMock(stdout="1.2.3", stderr="", returncode=0)
            return MagicMock(stdout="", stderr="", returncode=0)
        
        mock_run.side_effect = side_effect
        
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["installed"] is True
        assert result["version"] == "1.2.3"

    @patch("jarvis.tools.app_status.platform.system")
    @patch("jarvis.tools.app_status.subprocess.run")
    def test_app_status_live_installed_no_version(self, mock_run, mock_platform):
        """Live mode handles installed app without detectable version."""
        mock_platform.return_value = "Darwin"
        
        def side_effect(*args, **kwargs):
            cmd = args[0] if args else []
            if "mdfind" in cmd:
                return MagicMock(stdout="/Applications/Arc.app", stderr="", returncode=0)
            elif "mdls" in cmd:
                # mdls returns "(null)" when version not found
                return MagicMock(stdout="(null)", stderr="", returncode=0)
            return MagicMock(stdout="", stderr="", returncode=0)
        
        mock_run.side_effect = side_effect
        
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="arc")
        assert result["ok"] is True
        assert result["app"] == "Arc"
        assert result["installed"] is True
        assert result["version"] is None

    @patch("jarvis.tools.app_status.platform.system")
    @patch("jarvis.tools.app_status.subprocess.run")
    def test_app_status_live_timeout_handling(self, mock_run, mock_platform):
        """Live mode handles subprocess timeout gracefully."""
        mock_platform.return_value = "Darwin"
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        
        tool = make_app_status_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["installed"] is False


class TestAppStatusToolSchema:
    """Tests for tool schema."""

    def test_app_status_schema_required_fields(self):
        """Tool schema has required fields."""
        tool = make_app_status_tool(mode="dry_run")
        
        assert tool["name"] == "app_status"
        assert tool["description"]
        assert "input_schema" in tool
        assert "handler" in tool

    def test_app_status_schema_input_properties(self):
        """Input schema requires 'app' parameter."""
        tool = make_app_status_tool(mode="dry_run")
        schema = tool["input_schema"]
        
        assert schema["type"] == "object"
        assert "app" in schema["properties"]
        assert schema["properties"]["app"]["type"] == "string"
        assert schema["required"] == ["app"]

    def test_app_status_handler_is_callable(self):
        """Handler is a callable."""
        tool = make_app_status_tool(mode="dry_run")
        assert callable(tool["handler"])


class TestAppStatusApprovalCallbacks:
    """Tests for approval callback parameters (for consistency with install_app)."""

    def test_app_status_accepts_approval_callbacks(self):
        """app_status accepts approval callbacks (though unused)."""
        def mock_request(prompt: str) -> str:
            return "approval_id_123"
        
        def mock_get(approval_id: str):
            return {"status": "approved"}
        
        # Should not raise
        tool = make_app_status_tool(
            mode="dry_run",
            request_approval=mock_request,
            get_approval=mock_get,
        )
        handler = tool["handler"]
        result = handler(app="spotify")
        assert result["ok"] is True
