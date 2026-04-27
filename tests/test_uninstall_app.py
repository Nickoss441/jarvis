"""Tests for the uninstall_app tool."""
import json
import platform
import subprocess
from unittest.mock import MagicMock, patch, call

import pytest

from jarvis.tools.uninstall_app import make_uninstall_app_tool, dispatch_uninstall_app


class TestUninstallAppDryRun:
    """Tests for uninstall_app in dry_run mode."""

    def test_uninstall_app_dry_run_returns_plan(self):
        """Dry-run mode returns removal plan for allowlisted apps."""
        tool = make_uninstall_app_tool(mode="dry_run")
        handler = tool["handler"]
        result = handler(app="spotify")
        
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["status"] == "dry_run_plan"
        assert "brew uninstall --cask" in result["plan"]

    def test_uninstall_app_dry_run_all_allowlisted_apps(self):
        """Dry-run handles all allowlisted apps."""
        tool = make_uninstall_app_tool(mode="dry_run")
        handler = tool["handler"]
        
        for app in ["arc", "spotify", "visual studio code", "google chrome", "slack"]:
            result = handler(app=app)
            assert result["ok"] is True
            assert result["status"] == "dry_run_plan"

    def test_uninstall_app_dry_run_case_insensitive(self):
        """Dry-run matches app names case-insensitively."""
        tool = make_uninstall_app_tool(mode="dry_run")
        handler = tool["handler"]
        
        result = handler(app="SPOTIFY")
        assert result["ok"] is True
        assert result["app"] == "Spotify"

    def test_uninstall_app_dry_run_not_allowlisted(self):
        """Dry-run rejects non-allowlisted apps."""
        tool = make_uninstall_app_tool(mode="dry_run")
        handler = tool["handler"]
        
        result = handler(app="nonexistent")
        assert result["ok"] is False
        assert result["error"] == "app_not_allowlisted"


class TestUninstallAppLiveNoApproval:
    """Tests for live mode without approval service."""

    def test_uninstall_app_live_not_macos(self):
        """Live mode fails gracefully on non-macOS."""
        tool = make_uninstall_app_tool(mode="live")
        handler = tool["handler"]
        
        with patch("jarvis.tools.uninstall_app.platform.system", return_value="Linux"):
            result = handler(app="spotify")
            assert result["ok"] is False
            assert result["error"] == "not_macos"

    def test_uninstall_app_live_not_allowlisted(self):
        """Live mode rejects non-allowlisted apps."""
        tool = make_uninstall_app_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="nonexistent")
        assert result["ok"] is False
        assert result["error"] == "app_not_allowlisted"

    @patch("jarvis.tools.uninstall_app.platform.system")
    @patch("jarvis.tools.uninstall_app.subprocess.run")
    def test_uninstall_app_live_brew_success(self, mock_run, mock_platform):
        """Live mode successfully uninstalls via brew."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Uninstalling spotify...",
            stderr="",
        )
        
        tool = make_uninstall_app_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["status"] == "uninstalled"
        assert result["method"] == "brew_uninstall"

    @patch("jarvis.tools.uninstall_app.platform.system")
    @patch("jarvis.tools.uninstall_app.subprocess.run")
    def test_uninstall_app_live_brew_failure_fallback(self, mock_run, mock_platform):
        """Live mode falls back to manual removal directions when brew fails."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: unknown cask 'spotify'",
        )
        
        tool = make_uninstall_app_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["status"] == "manual_removal_needed"
        assert result["method"] == "manual"
        assert "Applications" in result["directions"]
        assert "Trash" in result["directions"]

    @patch("jarvis.tools.uninstall_app.platform.system")
    @patch("jarvis.tools.uninstall_app.subprocess.run")
    def test_uninstall_app_live_timeout_handling(self, mock_run, mock_platform):
        """Live mode handles subprocess timeout gracefully."""
        mock_platform.return_value = "Darwin"
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        
        tool = make_uninstall_app_tool(mode="live")
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["status"] == "manual_removal_needed"
        assert "command timed out" in result["directions"]


class TestUninstallAppWithApprovalService:
    """Tests for live mode with approval service callbacks."""

    def test_uninstall_app_live_with_approval_returns_approval_id(self):
        """Live mode with approval callbacks returns approval_id immediately."""
        def mock_request(prompt: str) -> str:
            return "approval_id_123"
        
        def mock_get(approval_id: str):
            return {"status": "pending"}
        
        tool = make_uninstall_app_tool(
            mode="live",
            request_approval=mock_request,
            get_approval=mock_get,
        )
        handler = tool["handler"]
        
        result = handler(app="spotify")
        assert result["ok"] is True
        assert result["status"] == "approval_requested"
        assert result["approval_id"] == "approval_id_123"

    def test_uninstall_app_live_without_approval_executes_immediately(self):
        """Live mode without callbacks executes uninstall immediately."""
        with patch("jarvis.tools.uninstall_app.platform.system", return_value="Darwin"):
            with patch("jarvis.tools.uninstall_app.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                
                tool = make_uninstall_app_tool(mode="live")
                handler = tool["handler"]
                
                result = handler(app="spotify")
                # Should execute immediately without approval flow
                assert result["ok"] is True
                assert result["status"] == "uninstalled"


class TestDispatchUninstallApp:
    """Tests for the dispatch_uninstall_app handler."""

    def test_dispatch_uninstall_app_dry_run(self):
        """Dispatch handler works in dry_run mode."""
        payload = {"app": "spotify"}
        result = dispatch_uninstall_app(mode="dry_run", payload=payload)
        
        assert result["ok"] is True
        assert result["app"] == "Spotify"
        assert result["status"] == "dry_run_plan"

    @patch("jarvis.tools.uninstall_app.platform.system")
    @patch("jarvis.tools.uninstall_app.subprocess.run")
    def test_dispatch_uninstall_app_live(self, mock_run, mock_platform):
        """Dispatch handler works in live mode."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        payload = {"app": "spotify"}
        result = dispatch_uninstall_app(mode="live", payload=payload)
        
        assert result["ok"] is True
        assert result["status"] == "uninstalled"

    def test_dispatch_uninstall_app_not_allowlisted(self):
        """Dispatch handler rejects non-allowlisted apps."""
        payload = {"app": "nonexistent"}
        result = dispatch_uninstall_app(mode="dry_run", payload=payload)
        
        assert result["ok"] is False
        assert result["error"] == "app_not_allowlisted"


class TestUninstallAppToolSchema:
    """Tests for tool schema."""

    def test_uninstall_app_schema_required_fields(self):
        """Tool schema has required fields."""
        tool = make_uninstall_app_tool(mode="dry_run")
        
        assert tool["name"] == "uninstall_app"
        assert tool["description"]
        assert "input_schema" in tool
        assert "handler" in tool

    def test_uninstall_app_schema_input_properties(self):
        """Input schema requires 'app' parameter."""
        tool = make_uninstall_app_tool(mode="dry_run")
        schema = tool["input_schema"]
        
        assert schema["type"] == "object"
        assert "app" in schema["properties"]
        assert schema["properties"]["app"]["type"] == "string"
        assert schema["required"] == ["app"]

    def test_uninstall_app_handler_is_callable(self):
        """Handler is a callable."""
        tool = make_uninstall_app_tool(mode="dry_run")
        assert callable(tool["handler"])
