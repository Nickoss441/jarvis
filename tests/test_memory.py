from pathlib import Path

from jarvis.memory import Conversation, UserPreferencesStore


def test_conversation_persists_messages_to_disk(tmp_path: Path) -> None:
    store = tmp_path / "conversation.json"
    conversation = Conversation(storage_path=store)

    conversation.add_user("hello")
    conversation.add_assistant([{"type": "text", "text": "hi"}])
    conversation.add_tool_results([{"type": "tool_result", "content": "ok"}])

    restored = Conversation(storage_path=store)

    assert restored.messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
        {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    ]


def test_conversation_reset_clears_persisted_messages(tmp_path: Path) -> None:
    store = tmp_path / "conversation.json"
    conversation = Conversation(storage_path=store)

    conversation.add_user("hello")
    assert store.exists()

    conversation.reset()

    restored = Conversation(storage_path=store)
    assert restored.messages == []


def test_conversation_ignores_invalid_persisted_payload(tmp_path: Path) -> None:
    store = tmp_path / "conversation.json"
    store.write_text('{"bad": true}', encoding="utf-8")

    conversation = Conversation(storage_path=store)

    assert conversation.messages == []


def test_user_preferences_store_persists_nested_schema(tmp_path: Path) -> None:
    store = tmp_path / "preferences.json"
    prefs = UserPreferencesStore(storage_path=store)

    prefs.update(
        {
            "profile": {"preferred_name": "Nick", "timezone": "America/New_York"},
            "contact": {"email": "user@example.com", "phone": "+14155550123"},
            "address": {"city": "New York", "country": "US"},
        }
    )

    restored = UserPreferencesStore(storage_path=store)

    assert restored.data["profile"]["preferred_name"] == "Nick"
    assert restored.data["contact"]["phone"] == "+14155550123"
    assert restored.data["address"]["country"] == "US"


def test_user_preferences_store_merges_partial_updates(tmp_path: Path) -> None:
    store = tmp_path / "preferences.json"
    prefs = UserPreferencesStore(storage_path=store)

    prefs.update({"profile": {"preferred_name": "Nick"}})
    prefs.update({"profile": {"timezone": "UTC"}})

    assert prefs.data["profile"] == {
        "preferred_name": "Nick",
        "timezone": "UTC",
    }


def test_user_preferences_store_rejects_unknown_top_level_keys(tmp_path: Path) -> None:
    prefs = UserPreferencesStore(storage_path=tmp_path / "preferences.json")

    try:
        prefs.update({"unknown": {"value": True}})
    except ValueError as exc:
        assert "unknown preference section" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown preference section")