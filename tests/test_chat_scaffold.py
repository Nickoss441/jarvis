from jarvis.perception.chat import build_chat_registry, extract_command
from jarvis.perception.chat.bot import BotChatAdapter
from jarvis.perception.chat.shortcuts import ShortcutsChatAdapter


def test_shortcuts_adapter_parses_payload():
    adapter = ShortcutsChatAdapter()

    out = adapter.parse_payload(
        {
            "sender": "nick",
            "channel": "ios",
            "text": "send a reminder",
            "shortcut_name": "Jarvis Inbound",
            "conversation_id": "abc-123",
        }
    )

    assert out["kind"] == "chat_message"
    assert out["source"] == "ios_shortcuts"
    assert out["sender"] == "nick"
    assert out["channel"] == "ios"
    assert out["text"] == "send a reminder"
    assert out["metadata"]["shortcut_name"] == "Jarvis Inbound"


def test_shortcuts_adapter_rejects_missing_text():
    adapter = ShortcutsChatAdapter()

    out = adapter.parse_payload({"sender": "nick"})

    assert out["error"] == "missing message text"


def test_bot_adapter_parses_payload():
    adapter = BotChatAdapter()

    out = adapter.parse_payload(
        {
            "user": "nick",
            "chat_id": "ops",
            "body": "hello from bot",
            "message_id": "m1",
            "thread_id": "t1",
        }
    )

    assert out["kind"] == "chat_message"
    assert out["source"] == "bot"
    assert out["sender"] == "nick"
    assert out["channel"] == "ops"
    assert out["text"] == "hello from bot"
    assert out["metadata"]["message_id"] == "m1"


def test_bot_adapter_rejects_missing_text():
    adapter = BotChatAdapter()

    out = adapter.parse_payload({"user": "nick"})

    assert out["error"] == "missing message text"


def test_extract_command_from_slash_text():
    out = extract_command("/pay 42 usd")

    assert out["command"] == "pay"
    assert out["args"] == ["42", "usd"]


def test_extract_command_returns_empty_for_plain_text():
    out = extract_command("hello world")

    assert out["command"] == ""
    assert out["args"] == []


def test_chat_registry_routes_shortcuts_and_bot():
    reg = build_chat_registry()

    shortcuts = reg.parse("ios_shortcuts", {"text": "hello", "sender": "nick"})
    web_ui = reg.parse("web_ui", {"text": "hello from browser", "sender": "nick"})
    bot = reg.parse("bot", {"text": "hello", "user": "nick"})

    assert shortcuts["source"] == "ios_shortcuts"
    assert web_ui["source"] == "ios_shortcuts"
    assert bot["source"] == "bot"


def test_chat_registry_reports_unknown_source():
    reg = build_chat_registry()

    out = reg.parse("discord", {"text": "hello"})

    assert "unknown chat source" in out["error"]
