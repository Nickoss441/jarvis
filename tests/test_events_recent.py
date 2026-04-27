from jarvis.event_bus import Event, EventBus
from jarvis.tools.events_recent import make_events_recent_tool


def test_events_recent_returns_most_recent_first(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    bus.emit(Event(kind="calendar_event", source="calendar", payload={"summary": "one"}, timestamp=1.0))
    bus.emit(Event(kind="rss_article", source="rss", payload={"title": "two"}, timestamp=2.0))

    tool = make_events_recent_tool(bus)
    result = tool.handler(limit=10)

    assert result["count"] == 2
    assert result["events"][0]["kind"] == "rss_article"
    assert result["events"][1]["kind"] == "calendar_event"


def test_events_recent_can_filter_unprocessed_only(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    processed_id = bus.emit(Event(kind="webhook_event", source="webhook", payload={"id": 1}, timestamp=1.0))
    bus.emit(Event(kind="webhook_event", source="webhook", payload={"id": 2}, timestamp=2.0))
    assert bus.mark_processed(processed_id, notes="done")

    tool = make_events_recent_tool(bus)
    result = tool.handler(limit=10, unprocessed_only=True)

    assert result["count"] == 1
    assert result["events"][0]["payload"]["id"] == 2
    assert result["events"][0]["processed"] is False


def test_events_recent_can_filter_by_kind(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    bus.emit(Event(kind="vision_frame", source="vision", payload={"frame": "a"}, timestamp=1.0))
    bus.emit(Event(kind="filesystem_new_file", source="dropzone", payload={"path": "x"}, timestamp=2.0))

    tool = make_events_recent_tool(bus)
    result = tool.handler(limit=10, kind="vision_frame")

    assert result["count"] == 1
    assert result["events"][0]["kind"] == "vision_frame"


def test_events_recent_clamps_limit_range(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    bus.emit(Event(kind="calendar_event", source="calendar", payload={}, timestamp=1.0))

    tool = make_events_recent_tool(bus)
    low = tool.handler(limit=0)
    high = tool.handler(limit=9999)

    assert low["limit"] == 1
    assert high["limit"] == 200
