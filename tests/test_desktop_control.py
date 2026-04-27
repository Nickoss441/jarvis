from jarvis.tools.desktop_control import make_desktop_control_tool


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
