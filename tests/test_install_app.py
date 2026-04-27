from jarvis.tools.install_app import make_install_app_tool


def test_install_app_dry_run_builds_plan():
    tool = make_install_app_tool(mode="dry_run")

    out = tool.handler(app="spotify")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["app"] == "spotify"
    assert out["plan"]["brew_cask"] == "spotify"


def test_install_app_rejects_non_allowlisted_app():
    tool = make_install_app_tool(mode="dry_run")

    out = tool.handler(app="random sketchy app")

    assert out["ok"] is False
    assert "allowlist" in out["error"]


def test_install_app_live_rejects_non_macos(monkeypatch):
    monkeypatch.setattr("jarvis.tools.install_app.platform.system", lambda: "Linux")
    tool = make_install_app_tool(mode="live")

    out = tool.handler(app="spotify")

    assert out["ok"] is False
    assert "macOS" in out["error"]


def test_install_app_live_auto_uses_brew_when_available(monkeypatch):
    calls = []

    def _fake_run(argv, timeout=120):
        calls.append(argv)
        if argv[:2] == ["brew", "--version"]:
            return True, "Homebrew 4.0"
        if argv[:3] == ["brew", "install", "--cask"]:
            return True, "installed"
        return False, "unexpected"

    monkeypatch.setattr("jarvis.tools.install_app.platform.system", lambda: "Darwin")
    monkeypatch.setattr("jarvis.tools.install_app._run_command", _fake_run)

    tool = make_install_app_tool(mode="live")
    out = tool.handler(app="spotify", method="auto")

    assert out["ok"] is True
    assert out["method"] == "brew"
    assert any(cmd[:2] == ["brew", "--version"] for cmd in calls)
    assert any(cmd[:3] == ["brew", "install", "--cask"] for cmd in calls)


def test_install_app_live_auto_falls_back_to_url(monkeypatch):
    calls = []

    def _fake_run(argv, timeout=120):
        calls.append(argv)
        if argv[:2] == ["brew", "--version"]:
            return False, "required executable not found"
        if argv and argv[0] == "open":
            return True, "opened"
        return False, "unexpected"

    monkeypatch.setattr("jarvis.tools.install_app.platform.system", lambda: "Darwin")
    monkeypatch.setattr("jarvis.tools.install_app._run_command", _fake_run)

    tool = make_install_app_tool(mode="live")
    out = tool.handler(app="spotify", method="auto")

    assert out["ok"] is True
    assert out["method"] == "url"
    assert out["fallback_from"] == "brew"
    assert any(cmd and cmd[0] == "open" for cmd in calls)


def test_install_app_live_queues_approval_when_callbacks_present():
    approvals = {}

    def _request(kind, payload):
        assert kind == "install_app"
        approvals["payload"] = payload
        approvals["kind"] = kind
        return "approval-1"

    def _get(_approval_id):
        return {"correlation_id": "corr-1"}

    tool = make_install_app_tool(mode="live", request_approval=_request, get_approval=_get)
    out = tool.handler(app="spotify", method="auto")

    assert out["status"] == "pending_approval"
    assert out["kind"] == "install_app"
    assert out["approval_id"] == "approval-1"
    assert out["correlation_id"] == "corr-1"
    assert approvals["payload"]["app"] == "spotify"
