from pathlib import Path
import json

from jarvis.tools.user_preferences import make_user_preferences_tool


def test_user_preferences_get_returns_empty_by_default(tmp_path: Path) -> None:
    tool = make_user_preferences_tool(tmp_path / "preferences.json")

    out = tool.handler(action="get")

    assert out == {"ok": True, "action": "get", "data": {}}


def test_user_preferences_update_persists_data(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    tool = make_user_preferences_tool(path)

    update_out = tool.handler(
        action="update",
        patch={"profile": {"preferred_name": "Nick"}, "contact": {"email": "nick@example.com"}},
    )
    read_out = make_user_preferences_tool(path).handler(action="get")

    assert update_out["ok"] is True
    assert update_out["data"]["profile"]["preferred_name"] == "Nick"
    assert read_out["data"]["contact"]["email"] == "nick@example.com"


def test_user_preferences_update_rejects_unknown_section(tmp_path: Path) -> None:
    tool = make_user_preferences_tool(tmp_path / "preferences.json")

    out = tool.handler(action="update", patch={"unknown": {"x": 1}})

    assert out["ok"] is False
    assert "unknown preference section" in out["error"]


def test_user_preferences_reset_clears_data(tmp_path: Path) -> None:
    tool = make_user_preferences_tool(tmp_path / "preferences.json")
    tool.handler(action="update", patch={"profile": {"preferred_name": "Nick"}})

    out = tool.handler(action="reset")

    assert out == {"ok": True, "action": "reset", "data": {}}

def test_user_preferences_tool_persists_encrypted_manifest_when_secret_set(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    tool = make_user_preferences_tool(path, manifest_secret="manifest-secret")

    out = tool.handler(action="update", patch={"profile": {"preferred_name": "Nick"}})

    assert out["ok"] is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "ciphertext" in payload
    assert "profile" not in payload


def test_user_preferences_store_contact_address_action(tmp_path: Path) -> None:
    tool = make_user_preferences_tool(tmp_path / "preferences.json")

    out = tool.handler(
        action="store_contact_address",
        patch={
            "contact": {"email": "user@example.com", "phone": "+14155552671"},
            "address": {"city": "New York", "country": "US"},
        },
    )

    assert out["ok"] is True
    assert out["action"] == "store_contact_address"
    assert out["data"]["contact"]["email"] == "user@example.com"
    assert out["data"]["address"]["country"] == "US"
