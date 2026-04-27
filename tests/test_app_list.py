"""Tests for the app_list tool."""
import unittest
from unittest.mock import patch, MagicMock

from jarvis.tools.app_list import (
    make_app_list_tool,
    _check_app_live,
    _list_apps_dry_run,
    _list_apps_live,
    ALLOWED_APPS,
)


class TestAppListDryRun(unittest.TestCase):
    """Test dry_run mode for app_list tool."""

    def test_list_apps_dry_run_returns_all_apps(self):
        """Dry run mode returns all allowlisted apps with mock status."""
        result = _list_apps_dry_run()
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["count"], len(ALLOWED_APPS))
        self.assertEqual(len(result["apps"]), len(ALLOWED_APPS))

    def test_list_apps_dry_run_app_structure(self):
        """Each dry-run app has correct structure."""
        result = _list_apps_dry_run()
        for app in result["apps"]:
            self.assertIn("name", app)
            self.assertIn("label", app)
            self.assertIn("installed", app)
            self.assertIn("version", app)

    def test_list_apps_dry_run_contains_all_allowed_apps(self):
        """Dry run includes all allowlisted apps."""
        result = _list_apps_dry_run()
        names = {app["name"] for app in result["apps"]}
        self.assertEqual(names, set(ALLOWED_APPS.keys()))

    def test_list_apps_dry_run_all_not_installed(self):
        """In dry run, all apps show as not installed."""
        result = _list_apps_dry_run()
        for app in result["apps"]:
            self.assertFalse(app["installed"])
            self.assertIsNone(app["version"])

    def test_app_list_tool_dry_run_mode(self):
        """Tool factory with dry_run mode."""
        tool = make_app_list_tool(mode="dry_run")
        result = tool["handler"]()
        self.assertEqual(result["ok"], True)
        self.assertGreater(result["count"], 0)


class TestAppListLive(unittest.TestCase):
    """Test live mode for app_list tool (mocked)."""

    @patch("jarvis.tools.app_list.platform.system")
    @patch("jarvis.tools.app_list._check_app_live")
    def test_list_apps_live_checks_all_apps(self, mock_check, mock_platform):
        """Live mode queries each app."""
        mock_platform.return_value = "Darwin"
        mock_check.return_value = {
            "name": "test",
            "label": "Test",
            "installed": False,
            "version": None,
        }

        result = _list_apps_live()

        self.assertEqual(result["ok"], True)
        self.assertEqual(result["count"], len(ALLOWED_APPS))
        self.assertEqual(mock_check.call_count, len(ALLOWED_APPS))

    @patch("jarvis.tools.app_list.platform.system")
    def test_list_apps_live_not_darwin(self, mock_platform):
        """Non-macOS platform returns empty list."""
        mock_platform.return_value = "Linux"

        result = _list_apps_live()

        self.assertEqual(result["ok"], False)
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["apps"]), 0)

    @patch("jarvis.tools.app_list.subprocess.run")
    @patch("jarvis.tools.app_list.platform.system")
    def test_check_app_live_found_with_version(self, mock_platform, mock_run):
        """App found with version."""
        mock_platform.return_value = "Darwin"

        # First call (mdfind) returns app path
        # Second call (mdls) returns version
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/Applications/Slack.app\n"),
            MagicMock(returncode=0, stdout='kMDItemVersion = "4.37.0"\n'),
        ]

        result = _check_app_live("slack")

        self.assertEqual(result["name"], "slack")
        self.assertTrue(result["installed"])
        self.assertEqual(result["version"], "4.37.0")

    @patch("jarvis.tools.app_list.subprocess.run")
    @patch("jarvis.tools.app_list.platform.system")
    def test_check_app_live_not_found(self, mock_platform, mock_run):
        """App not found (mdfind returns empty)."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = _check_app_live("slack")

        self.assertEqual(result["name"], "slack")
        self.assertFalse(result["installed"])
        self.assertIsNone(result["version"])

    @patch("jarvis.tools.app_list.subprocess.run")
    @patch("jarvis.tools.app_list.platform.system")
    def test_check_app_live_mdfind_fails(self, mock_platform, mock_run):
        """mdfind command fails."""
        mock_platform.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _check_app_live("slack")

        self.assertFalse(result["installed"])
        self.assertIsNone(result["version"])

    @patch("jarvis.tools.app_list.subprocess.run")
    @patch("jarvis.tools.app_list.platform.system")
    def test_check_app_live_timeout(self, mock_platform, mock_run):
        """subprocess timeout handled gracefully."""
        mock_platform.return_value = "Darwin"
        mock_run.side_effect = TimeoutError()

        result = _check_app_live("slack")

        self.assertFalse(result["installed"])
        self.assertIsNone(result["version"])

    @patch("jarvis.tools.app_list.subprocess.run")
    @patch("jarvis.tools.app_list.platform.system")
    def test_check_app_live_no_version(self, mock_platform, mock_run):
        """App found but version lookup fails."""
        mock_platform.return_value = "Darwin"

        # mdfind succeeds, mdls fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/Applications/Arc.app\n"),
            MagicMock(returncode=1, stdout=""),
        ]

        result = _check_app_live("arc")

        self.assertTrue(result["installed"])
        self.assertIsNone(result["version"])


class TestAppListToolSchema(unittest.TestCase):
    """Test app_list tool schema."""

    def test_tool_schema_has_required_fields(self):
        """Tool schema includes name, description, input_schema, handler."""
        tool = make_app_list_tool()
        self.assertIn("name", tool)
        self.assertIn("description", tool)
        self.assertIn("input_schema", tool)
        self.assertIn("handler", tool)

    def test_tool_name_is_app_list(self):
        """Tool is named app_list."""
        tool = make_app_list_tool()
        self.assertEqual(tool["name"], "app_list")

    def test_tool_input_schema_no_required_params(self):
        """Tool accepts no parameters."""
        tool = make_app_list_tool()
        schema = tool["input_schema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], [])

    def test_tool_handler_callable(self):
        """Handler is callable."""
        tool = make_app_list_tool()
        self.assertTrue(callable(tool["handler"]))

    def test_tool_handler_returns_correct_type(self):
        """Handler returns AppListResult typed dict."""
        tool = make_app_list_tool(mode="dry_run")
        result = tool["handler"]()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("apps", result)
        self.assertIn("count", result)


if __name__ == "__main__":
    unittest.main()
