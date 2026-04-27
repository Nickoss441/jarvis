from jarvis.tools.calendar_read import make_calendar_read_tool


def test_calendar_read_returns_empty_when_source_missing(tmp_path, monkeypatch):
    # Force non-macOS path for deterministic legacy behavior.
    monkeypatch.setattr("jarvis.tools.calendar_read.platform.system", lambda: "Linux")

    tool = make_calendar_read_tool(tmp_path / "missing.ics")

    result = tool.handler()

    assert result["status"] == "ok"
    assert result["count"] == 0
    assert result["source"] == "none"


def test_calendar_read_parses_basic_ics_event(tmp_path):
    ics = tmp_path / "calendar.ics"
    ics.write_text(
        "\n".join(
            [
                "BEGIN:VCALENDAR",
                "BEGIN:VEVENT",
                "DTSTART:20260425T120000Z",
                "DTEND:20260425T123000Z",
                "SUMMARY:Lunch",
                "LOCATION:Office",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        ),
        encoding="utf-8",
    )
    tool = make_calendar_read_tool(ics)

    result = tool.handler(max_events=5)

    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["events"][0]["summary"] == "Lunch"
    assert result["events"][0]["location"] == "Office"


def test_calendar_read_uses_apple_calendar_fallback_on_macos(tmp_path, monkeypatch):
    class _Completed:
        returncode = 0
        stdout = "Mon Apr 27 10:00:00 2026\tMon Apr 27 10:30:00 2026\tStandup\tOffice\n"
        stderr = ""

    monkeypatch.setattr("jarvis.tools.calendar_read.platform.system", lambda: "Darwin")
    monkeypatch.setattr("jarvis.tools.calendar_read.subprocess.run", lambda *args, **kwargs: _Completed())

    tool = make_calendar_read_tool(tmp_path / "missing.ics")
    result = tool.handler(max_events=5)

    assert result["status"] == "ok"
    assert result["source"] == "apple_calendar"
    assert result["count"] == 1
    assert result["events"][0]["summary"] == "Standup"
