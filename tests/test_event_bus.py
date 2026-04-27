"""Tests for event bus and monitors."""
import hashlib
import hmac
import json
import time
import urllib.request
from pathlib import Path

from jarvis.event_bus import Event, EventBus
from jarvis.monitors import (
    Monitor,
    CalendarMonitor,
    RSSMonitor,
    FilesystemMonitor,
    VisionIngestMonitor,
    WebhookMonitor,
)


def test_event_creation():
    """Test Event dataclass."""
    event = Event(
        kind="calendar_event",
        source="calendar",
        payload={"title": "Team standup", "time": "2026-04-25T10:00:00Z"},
    )

    assert event.kind == "calendar_event"
    assert event.source == "calendar"
    assert event.payload["title"] == "Team standup"
    assert not event.processed


def test_event_to_from_dict():
    """Test Event serialization."""
    event = Event(
        kind="rss_article",
        source="rss_tech_news",
        payload={"title": "New AI breakthrough", "url": "https://example.com/1"},
    )

    data = event.to_dict()
    assert data["kind"] == "rss_article"
    assert data["payload"]["title"] == "New AI breakthrough"

    restored = Event.from_dict(data)
    assert restored.kind == event.kind
    assert restored.payload == event.payload


def test_event_promotes_payload_correlation_id_to_envelope():
    event = Event(
        kind="rss_article",
        source="rss_tech_news",
        payload={"correlation_id": "corr-rss", "title": "New AI breakthrough"},
    )

    assert event.correlation_id == "corr-rss"


def test_event_bus_emit(tmp_path):
    """Test emitting events to the bus."""
    bus = EventBus(tmp_path / "events.db")

    event1 = Event(
        kind="calendar_event",
        source="calendar",
        payload={"title": "Lunch meeting"},
    )
    event_id1 = bus.emit(event1)
    assert event_id1 == event1.id

    event2 = Event(
        kind="rss_article",
        source="rss_tech_news",
        payload={"title": "AI in 2026"},
    )
    event_id2 = bus.emit(event2)
    assert event_id2 == event2.id
    assert event_id1 != event_id2


def test_event_bus_persists_top_level_correlation_id(tmp_path):
    bus = EventBus(tmp_path / "events.db")

    event = Event(
        kind="webhook_github",
        source="webhook_secure",
        correlation_id="corr-top-level",
        payload={"event_type": "github.push"},
    )

    bus.emit(event)

    stored = bus.get(event.id)
    assert stored is not None
    assert stored.correlation_id == "corr-top-level"


def test_event_bus_list_unprocessed(tmp_path):
    """Test retrieving unprocessed events."""
    bus = EventBus(tmp_path / "events.db")

    # Emit 3 unprocessed events
    for i in range(3):
        bus.emit(
            Event(
                kind="calendar_event",
                source="calendar",
                payload={"num": i},
            )
        )

    unprocessed = bus.list_unprocessed(limit=10)
    assert len(unprocessed) == 3
    assert all(not e.processed for e in unprocessed)


def test_event_bus_mark_processed(tmp_path):
    """Test marking events as processed."""
    bus = EventBus(tmp_path / "events.db")

    event = Event(
        kind="calendar_event",
        source="calendar",
        payload={"title": "Tomorrow's standup"},
    )
    event_id = bus.emit(event)

    # Should be unprocessed initially
    unprocessed = bus.list_unprocessed()
    assert len(unprocessed) == 1

    # Mark as processed
    ok = bus.mark_processed(event_id, notes="Sent reminder")
    assert ok

    # Should no longer appear in unprocessed
    unprocessed = bus.list_unprocessed()
    assert len(unprocessed) == 0

    # Verify processed flag and notes
    retrieved = bus.get(event_id)
    assert retrieved.processed
    assert retrieved.processed_at is not None
    assert retrieved.notes == "Sent reminder"


def test_event_bus_filter_by_kind(tmp_path):
    """Test filtering events by kind."""
    bus = EventBus(tmp_path / "events.db")

    # Emit calendar and RSS events
    bus.emit(Event(kind="calendar_event", source="calendar", payload={}))
    bus.emit(Event(kind="calendar_event", source="calendar", payload={}))
    bus.emit(Event(kind="rss_article", source="rss_news", payload={}))

    # Filter by kind
    calendar_events = bus.list_unprocessed(kind="calendar_event")
    assert len(calendar_events) == 2

    rss_events = bus.list_unprocessed(kind="rss_article")
    assert len(rss_events) == 1


def test_event_bus_recent(tmp_path):
    """Test retrieving recent events (newest first)."""
    bus = EventBus(tmp_path / "events.db")

    # Emit 3 events with slight delays
    ids = []
    for i in range(3):
        event = Event(
            kind="calendar_event",
            source="calendar",
            payload={"num": i},
        )
        eid = bus.emit(event)
        ids.append(eid)
        time.sleep(0.01)  # Ensure timestamps differ

    recent = bus.recent(limit=10)
    assert len(recent) == 3
    # Should be newest first (reverse order of emission)
    assert recent[0].payload["num"] == 2
    assert recent[1].payload["num"] == 1
    assert recent[2].payload["num"] == 0


def test_event_bus_count(tmp_path):
    """Test counting events."""
    bus = EventBus(tmp_path / "events.db")

    # Emit events
    event1 = Event(kind="calendar_event", source="calendar", payload={})
    bus.emit(event1)

    event2 = Event(kind="calendar_event", source="calendar", payload={})
    event_id2 = bus.emit(event2)

    # Count all
    assert bus.count() == 2

    # Count unprocessed
    assert bus.count(processed=False) == 2
    assert bus.count(processed=True) == 0

    # Mark one as processed
    bus.mark_processed(event_id2)
    assert bus.count(processed=False) == 1
    assert bus.count(processed=True) == 1

    # Count by kind
    assert bus.count(kind="calendar_event") == 2


def test_monitor_emit_event(tmp_path):
    """Test custom Monitor emitting events."""
    bus = EventBus(tmp_path / "events.db")

    class TestMonitor(Monitor):
        def run(self) -> int:
            self.emit_event(
                kind="test_event",
                payload={"data": "test"},
            )
            return 1

    monitor = TestMonitor(bus, source="test_source")
    events_emitted = monitor.run()
    assert events_emitted == 1

    unprocessed = bus.list_unprocessed()
    assert len(unprocessed) == 1
    assert unprocessed[0].kind == "test_event"
    assert unprocessed[0].source == "test_source"
    assert unprocessed[0].correlation_id == unprocessed[0].id


def test_calendar_monitor_stub(tmp_path):
    """Test CalendarMonitor basic instantiation."""
    bus = EventBus(tmp_path / "events.db")
    monitor = CalendarMonitor(bus, str(tmp_path / "calendar.ics"))

    # Stub should return 0 events
    assert monitor.run() == 0
    assert bus.count() == 0


def test_calendar_monitor_emits_new_ics_events_after_bootstrap(tmp_path):
        """Calendar monitor should baseline first and emit only new VEVENTs later."""
        bus = EventBus(tmp_path / "events.db")
        ics_path = tmp_path / "calendar.ics"
        ics_path.write_text(
                """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-1
SUMMARY:First event
DTSTART:20260425T100000Z
END:VEVENT
END:VCALENDAR
"""
        )

        monitor = CalendarMonitor(bus, str(ics_path))
        assert monitor.run() == 0  # baseline

        ics_path.write_text(
                """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event-1
SUMMARY:First event
DTSTART:20260425T100000Z
END:VEVENT
BEGIN:VEVENT
UID:event-2
SUMMARY:Second event
DTSTART:20260425T130000Z
END:VEVENT
END:VCALENDAR
"""
        )

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="calendar_event")
        assert len(events) == 1
        assert events[0].payload["uid"] == "event-2"
        assert events[0].payload["title"] == "Second event"


def test_rss_monitor_emits_new_items_after_bootstrap(tmp_path):
        """RSS monitor should baseline first and emit only unseen items."""
        bus = EventBus(tmp_path / "events.db")
        feed_path = tmp_path / "feed.xml"
        feed_path.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
    <channel>
        <title>Demo Feed</title>
        <item>
            <guid>a1</guid>
            <title>Item One</title>
            <link>https://example.com/a1</link>
        </item>
    </channel>
</rss>
"""
        )

        monitor = RSSMonitor(bus, f"file://{feed_path}", "demo")
        assert monitor.run() == 0  # baseline

        feed_path.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
    <channel>
        <title>Demo Feed</title>
        <item>
            <guid>a1</guid>
            <title>Item One</title>
            <link>https://example.com/a1</link>
        </item>
        <item>
            <guid>a2</guid>
            <title>Item Two</title>
            <link>https://example.com/a2</link>
        </item>
    </channel>
</rss>
"""
        )

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="rss_article")
        assert len(events) == 1
        assert events[0].payload["id"] == "a2"
        assert events[0].payload["title"] == "Item Two"


def test_filesystem_monitor_emits_new_files_after_bootstrap(tmp_path):
    """Filesystem monitor should baseline existing files and emit newly created ones."""
    bus = EventBus(tmp_path / "events.db")
    watch_dir = tmp_path / "dropzone"
    watch_dir.mkdir()

    existing = watch_dir / "existing.txt"
    existing.write_text("already here")

    monitor = FilesystemMonitor(bus, str(watch_dir))
    assert monitor.run() == 0  # baseline

    new_file = watch_dir / "new.txt"
    new_file.write_text("new file")

    assert monitor.run() == 1
    events = bus.list_unprocessed(limit=10, kind="filesystem_new_file")
    assert len(events) == 1
    assert events[0].payload["name"] == "new.txt"


def test_webhook_monitor_ingest_then_run_emits_event(tmp_path):
    """Webhook monitor should emit queued webhook payloads."""
    bus = EventBus(tmp_path / "events.db")
    monitor = WebhookMonitor(bus, source_name="test")

    monitor.ingest(
        payload={"action": "opened", "issue": 123},
        path="/github",
        headers={"X-GitHub-Event": "issues"},
    )

    assert monitor.run() == 1
    events = bus.list_unprocessed(limit=10, kind="webhook_event")
    assert len(events) == 1
    payload = events[0].payload
    assert payload["event_type"] == "issues"
    assert payload["path"] == "/github"
    assert payload["payload"]["action"] == "opened"


    def test_webhook_monitor_delayed_processing_still_emits_payload(tmp_path):
        """Queued webhooks should survive delayed processing windows."""
        bus = EventBus(tmp_path / "events.db")
        monitor = WebhookMonitor(bus, source_name="delay")

        monitor.ingest(
            payload={"repo": "jarvis", "action": "push"},
            path="/github/push",
            headers={"X-Event-Type": "github.push"},
        )
        time.sleep(0.05)

        emitted = monitor.run()

        assert emitted == 1
        events = bus.list_unprocessed(limit=10, kind="webhook_event")
        assert len(events) == 1
        assert events[0].payload["payload"]["repo"] == "jarvis"
        assert events[0].payload["received_at"] <= time.time()


def test_webhook_monitor_http_server_accepts_post(tmp_path):
    """Webhook monitor HTTP server should accept JSON POST and queue events."""
    bus = EventBus(tmp_path / "events.db")
    monitor = WebhookMonitor(bus, source_name="http", host="127.0.0.1", port=0)

    host, port = monitor.start_server()
    try:
        req = urllib.request.Request(
            url=f"http://{host}:{port}/hook",
            data=json.dumps({"ok": True, "n": 7}).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Event-Type": "ifttt.trigger",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 202

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="webhook_event")
        assert len(events) == 1
        payload = events[0].payload
        assert payload["event_type"] == "ifttt.trigger"
        assert payload["path"] == "/hook"
        assert payload["payload"]["ok"] is True
    finally:
        monitor.stop_server()


def test_webhook_monitor_path_routing_sets_event_kind(tmp_path):
    """Webhook monitor should map request paths to configured event kinds."""
    bus = EventBus(tmp_path / "events.db")
    monitor = WebhookMonitor(
        bus,
        source_name="routed",
        path_kind_map={
            "/github": "webhook_github",
            "/ifttt": "webhook_ifttt",
        },
    )

    monitor.ingest(payload={"x": 1}, path="/github/push")
    assert monitor.run() == 1

    github_events = bus.list_unprocessed(limit=10, kind="webhook_github")
    assert len(github_events) == 1
    assert github_events[0].payload["path"] == "/github/push"


def test_webhook_monitor_http_server_rejects_invalid_signature(tmp_path):
    """Webhook HTTP endpoint should reject requests with missing/invalid signatures."""
    bus = EventBus(tmp_path / "events.db")
    monitor = WebhookMonitor(
        bus,
        source_name="secure",
        host="127.0.0.1",
        port=0,
        signing_secret="topsecret",
    )

    host, port = monitor.start_server()
    try:
        req = urllib.request.Request(
            url=f"http://{host}:{port}/secure",
            data=json.dumps({"ok": True}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            assert False, "expected HTTPError 401"
        except urllib.error.HTTPError as err:
            assert err.code == 401

        assert monitor.run() == 0
        assert bus.count(kind="webhook_event") == 0
    finally:
        monitor.stop_server()


def test_webhook_monitor_http_server_accepts_valid_signature(tmp_path):
    """Webhook HTTP endpoint should accept correctly signed requests."""
    bus = EventBus(tmp_path / "events.db")
    secret = "topsecret"
    monitor = WebhookMonitor(
        bus,
        source_name="secure",
        host="127.0.0.1",
        port=0,
        signing_secret=secret,
    )

    host, port = monitor.start_server()
    try:
        body = json.dumps({"ok": True, "kind": "signed"}).encode("utf-8")
        signature = "sha256=" + hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        req = urllib.request.Request(
            url=f"http://{host}:{port}/secure",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Jarvis-Signature": signature,
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 202

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="webhook_event")
        assert len(events) == 1
        assert events[0].payload["payload"]["kind"] == "signed"
    finally:
        monitor.stop_server()


def test_vision_ingest_monitor_emits_vision_frame_event(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    monitor = VisionIngestMonitor(bus, source_name="iphone", max_frame_bytes=2000000)

    monitor.ingest(
        payload={
            "frame_id": "f-1",
            "device": "rayban_meta",
            "labels": ["person", "car"],
            "text": "STOP",
            "image_base64": "aGVsbG8=",
        },
        path="/vision/frame",
        headers={"X-Event-Type": "vision.frame"},
    )

    assert monitor.run() == 1
    events = bus.list_unprocessed(limit=10, kind="vision_frame")
    assert len(events) == 1
    payload = events[0].payload
    assert payload["device"] == "rayban_meta"
    assert payload["frame_id"] == "f-1"
    assert payload["frame_accepted"] is True
    assert payload["has_frame"] is True
    assert payload["labels"] == ["person", "car"]
    assert isinstance(payload["vision_analysis"], dict)
    assert "face_count" in payload["vision_analysis"]
    assert "colors" in payload["vision_analysis"]
    assert "faces" in payload["vision_analysis"]
    assert "landmarks" in payload["vision_analysis"]


def test_vision_ingest_monitor_marks_oversized_frame_as_rejected(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    monitor = VisionIngestMonitor(bus, source_name="iphone", max_frame_bytes=5)

    monitor.ingest(payload={"image_base64": "aGVsbG8="}, path="/vision/frame")
    assert monitor.run() == 1

    events = bus.list_unprocessed(limit=10, kind="vision_frame")
    assert len(events) == 1
    payload = events[0].payload
    assert payload["frame_accepted"] is False
    assert payload["frame_size_bytes"] > payload["max_frame_bytes"]
    assert payload["vision_analysis"] == {}


def test_vision_ingest_monitor_http_server_accepts_multipart_image_upload(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    monitor = VisionIngestMonitor(bus, source_name="iphone", host="127.0.0.1", port=0)

    host, port = monitor.start_server()
    try:
        boundary = "----jarvisboundary"
        image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        body = (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"device\"\r\n\r\n"
            "rayban_meta\r\n"
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"labels\"\r\n\r\n"
            "person,door\r\n"
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"image\"; filename=\"frame.jpg\"\r\n"
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            url=f"http://{host}:{port}/frame",
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "X-Event-Type": "vision.frame",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 202

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="vision_frame")
        assert len(events) == 1
        payload = events[0].payload
        assert payload["device"] == "rayban_meta"
        assert payload["labels"] == ["person", "door"]
        assert payload["has_frame"] is True
        assert payload["frame_accepted"] is True
    finally:
        monitor.stop_server()


def test_vision_ingest_monitor_http_server_accepts_raw_image_upload(tmp_path):
    bus = EventBus(tmp_path / "events.db")
    monitor = VisionIngestMonitor(bus, source_name="iphone", host="127.0.0.1", port=0)

    host, port = monitor.start_server()
    try:
        raw = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        req = urllib.request.Request(
            url=f"http://{host}:{port}/frame",
            data=raw,
            method="POST",
            headers={
                "Content-Type": "image/png",
                "X-Device": "iphone_camera",
                "X-Frame-Id": "raw-1",
                "X-Labels": "document,desk",
                "X-Text": "desk view",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 202

        assert monitor.run() == 1
        events = bus.list_unprocessed(limit=10, kind="vision_frame")
        assert len(events) == 1
        payload = events[0].payload
        assert payload["device"] == "iphone_camera"
        assert payload["frame_id"] == "raw-1"
        assert payload["labels"] == ["document", "desk"]
        assert payload["text"] == "desk view"
        assert payload["has_frame"] is True
    finally:
        monitor.stop_server()
