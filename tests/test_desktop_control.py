import jarvis.tools.desktop_control as desktop_control
from jarvis.tools.desktop_control import make_desktop_control_tool


def test_desktop_control_dry_run_active_window():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="active_window")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["action"] == "active_window"


def test_desktop_control_active_window_parses_frontmost_window(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_control, "_run_command", lambda _argv: (True, "Safari\nGitHub"))

    out = tool.handler(action="active_window")

    assert out == {
        "ok": True,
        "action": "active_window",
        "app": "Safari",
        "window_title": "GitHub",
        "detail": "Safari\nGitHub",
    }


def test_desktop_control_focus_app_requires_name():
    tool = make_desktop_control_tool(mode="live")

    out = tool.handler(action="focus_app", app="")

    assert out["ok"] is False
    assert out["error"] == "app is required for focus_app"


def test_desktop_control_close_window_reports_no_front_window(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_control, "_run_command", lambda _argv: (True, "no-window"))

    out = tool.handler(action="close_window")

    assert out == {
        "ok": False,
        "action": "close_window",
        "error": "no front window to close",
    }


def test_desktop_control_focus_app_activates_named_app(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_control, "_run_command", lambda _argv: (True, "ok"))

    out = tool.handler(action="focus_app", app="Safari")

    assert out == {
        "ok": True,
        "action": "focus_app",
        "detail": "ok",
        "app": "Safari",
    }


def test_desktop_control_dry_run_screenshot():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="screenshot")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["action"] == "screenshot"


def test_desktop_control_screenshot_returns_base64_payload(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        desktop_control,
        "_capture_screenshot_png",
        lambda: b"fake-png-bytes",
    )

    out = tool.handler(action="screenshot")

    assert out == {
        "ok": True,
        "action": "screenshot",
        "mime_type": "image/png",
        "image_base64": "ZmFrZS1wbmctYnl0ZXM=",
        "byte_count": 14,
    }


def test_desktop_control_dry_run_open_app():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="open_app", app="Safari")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["action"] == "open_app"
    assert out["app"] == "Safari"


def test_desktop_control_rejects_bad_action():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="explode")

    assert out["ok"] is False
    assert "unsupported action" in out["error"]


def test_desktop_control_open_url_requires_scheme():
    tool = make_desktop_control_tool(mode="live")

    out = tool.handler(action="open_url", url="example.com")

    assert out["ok"] is False
    assert "must start with" in out["error"]
