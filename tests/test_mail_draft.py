import json

from jarvis.tools.mail_draft import make_mail_draft_tool


def test_mail_draft_saves_draft(tmp_path):
    drafts = tmp_path / "mail-drafts.jsonl"
    tool = make_mail_draft_tool(drafts)

    result = tool.handler(
        to="user@example.com",
        subject="Hello",
        body="Draft body",
    )

    assert result["status"] == "draft_saved"
    assert result["path"] == str(drafts)

    lines = drafts.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["to"] == "user@example.com"
    assert payload["subject"] == "Hello"
    assert payload["body"] == "Draft body"


def test_mail_draft_requires_fields(tmp_path):
    drafts = tmp_path / "mail-drafts.jsonl"
    tool = make_mail_draft_tool(drafts)

    result = tool.handler(to="", subject="x", body="y")

    assert "error" in result
    assert "required" in result["error"]
