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


def test_desktop_control_minimize_window_reports_no_front_window(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_control, "_run_command", lambda _argv: (True, "no-window"))

    out = tool.handler(action="minimize_window")

    assert out == {
        "ok": False,
        "action": "minimize_window",
        "error": "no front window to minimize",
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


def test_desktop_control_dry_run_minimize_window():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="minimize_window")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["action"] == "minimize_window"


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


def test_desktop_control_dry_run_open_chrome_url():
    tool = make_desktop_control_tool(mode="dry_run")

    out = tool.handler(action="open_chrome_url", url="https://example.com")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["action"] == "open_chrome_url"
    assert out["url"] == "https://example.com"


def test_desktop_control_open_chrome_url_uses_google_chrome(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    captured = {}

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")

    def _fake_run_command(argv):
        captured["argv"] = argv
        return True, "ok"

    monkeypatch.setattr(desktop_control, "_run_command", _fake_run_command)

    out = tool.handler(action="open_chrome_url", url="https://example.com")

    assert out == {
        "ok": True,
        "action": "open_chrome_url",
        "detail": "ok",
        "url": "https://example.com",
    }
    assert captured["argv"] == ["open", "-a", "Google Chrome", "https://example.com"]


def test_desktop_control_minimize_window_minimizes_front_window(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(desktop_control, "_run_command", lambda _argv: (True, "Safari"))

    out = tool.handler(action="minimize_window")

    assert out == {
        "ok": True,
        "action": "minimize_window",
        "detail": "Safari",
    }


def test_desktop_control_windows_open_app_uses_subprocess(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Windows")

    launched = {"argv": None}

    class _DummyProcess:
        pass

    def _fake_popen(argv):
        launched["argv"] = argv
        return _DummyProcess()

    monkeypatch.setattr(desktop_control.subprocess, "Popen", _fake_popen)

    out = tool.handler(action="open_app", app="notepad")

    assert out == {
        "ok": True,
        "action": "open_app",
        "detail": "launched",
        "app": "notepad",
    }
    assert launched["argv"] == ["notepad"]


def test_desktop_control_windows_keystroke_uses_pyautogui_hotkey(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Windows")

    class _FakePyAuto:
        def __init__(self):
            self.keys = None

        def hotkey(self, *keys):
            self.keys = keys

    fake = _FakePyAuto()
    monkeypatch.setattr(desktop_control, "_load_pyautogui", lambda: (fake, ""))

    out = tool.handler(action="keystroke", key_combo="ctrl+n")

    assert out["ok"] is True
    assert out["action"] == "keystroke"
    assert fake.keys == ("ctrl", "n")


def test_desktop_control_windows_type_text_uses_pyautogui_write(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Windows")

    class _FakePyAuto:
        def __init__(self):
            self.sent = None

        def write(self, text, interval=0.0):
            self.sent = (text, interval)

    fake = _FakePyAuto()
    monkeypatch.setattr(desktop_control, "_load_pyautogui", lambda: (fake, ""))

    out = tool.handler(action="type_text", text="hello")

    assert out["ok"] is True
    assert out["action"] == "type_text"
    assert fake.sent == ("hello", 0.02)


def test_desktop_control_windows_active_window(monkeypatch):
    tool = make_desktop_control_tool(mode="live")

    monkeypatch.setattr(desktop_control.platform, "system", lambda: "Windows")

    class _Window:
        title = "Inbox - Outlook"

    class _FakePyAuto:
        def getActiveWindow(self):
            return _Window()

    monkeypatch.setattr(desktop_control, "_load_pyautogui", lambda: (_FakePyAuto(), ""))

    out = tool.handler(action="active_window")

    assert out == {
        "ok": True,
        "action": "active_window",
        "app": "Inbox - Outlook",
        "window_title": "Inbox - Outlook",
        "detail": "Inbox - Outlook",
    }
