"""Tests for deterministic event automation rules."""
from jarvis.config import Config
from jarvis.event_automation import EventAutomation
from jarvis.event_bus import EventBus, Event
from jarvis.approval import ApprovalStore


def _make_config(tmp_path):
    return Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        approval_db=tmp_path / "approvals.db",
        event_bus_db=tmp_path / "events.db",
        event_alert_channel="slack",
        event_alert_recipient="#ops",
    )


def test_event_automation_creates_approval_for_github_webhook(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.processed == 1
    assert summary.approvals_created == 1
    assert summary.failures == 0

    # Event should be marked processed
    assert bus.count(processed=False) == 0
    assert bus.count(processed=True) == 1

    # Approval should exist
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0]["kind"] == "message_send"
    assert pending[0]["payload"]["channel"] == "slack"
    assert pending[0]["payload"]["recipient"] == "#ops"
    assert "GitHub webhook" in pending[0]["payload"]["subject"]


def test_event_automation_marks_unmatched_events_as_processed(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(Event(kind="rss_article", source="rss_demo", payload={"title": "x"}))

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.processed == 1
    assert summary.approvals_created == 0
    assert summary.skipped == 1
    assert summary.failures == 0
    assert bus.count(processed=False) == 0


def test_event_automation_filesystem_event_creates_alert(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="filesystem_new_file",
            source="filesystem",
            payload={
                "name": "invoice.pdf",
                "path": "/tmp/invoice.pdf",
                "size_bytes": 12345,
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert "New file detected" in pending[0]["payload"]["subject"]


def test_event_automation_idempotency_prevents_duplicate_alerts(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    payload = {
        "event_type": "github.push",
        "path": "/github/push",
        "payload": {"repo": "jarvis", "action": "push"},
    }

    bus.emit(Event(kind="webhook_github", source="webhook_secure", payload=payload))
    bus.emit(Event(kind="webhook_github", source="webhook_secure", payload=payload))

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.processed == 2
    assert summary.approvals_created == 1
    assert summary.duplicates == 1
    assert summary.failures == 0

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1


def test_event_automation_chaos_duplicate_burst_creates_single_approval(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    payload = {
        "event_type": "github.push",
        "path": "/github/push",
        "payload": {"repo": "jarvis", "action": "push"},
    }

    for _ in range(20):
        bus.emit(Event(kind="webhook_github", source="webhook_secure", payload=payload))

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=50)

    assert summary.processed == 20
    assert summary.approvals_created == 1
    assert summary.duplicates == 19
    assert summary.failures == 0

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1


def test_event_automation_throttles_by_kind_per_hour(tmp_path):
    config = _make_config(tmp_path)
    config.event_alerts_max_per_hour_by_kind = {"webhook_github": 1}
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push1"},
            },
        )
    )
    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push2"},
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.processed == 2
    assert summary.approvals_created == 1
    assert summary.throttled == 1
    assert summary.failures == 0

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1


def test_event_automation_uses_event_id_as_default_correlation_id(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    event_id = bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    assert summary.items[0]["correlation_id"] == event_id

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0]["correlation_id"] == event_id


def test_event_automation_uses_payload_correlation_id_when_provided(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            payload={
                "correlation_id": "corr-from-source",
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    assert summary.items[0]["correlation_id"] == "corr-from-source"

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0]["correlation_id"] == "corr-from-source"


def test_event_automation_prefers_top_level_correlation_id_over_payload(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="webhook_github",
            source="webhook_secure",
            correlation_id="corr-top-level",
            payload={
                "correlation_id": "corr-stale-payload",
                "event_type": "github.push",
                "path": "/github/push",
                "payload": {"repo": "jarvis", "action": "push"},
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    assert summary.items[0]["correlation_id"] == "corr-top-level"

    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0]["correlation_id"] == "corr-top-level"


def test_event_automation_list_recent_actions_includes_correlation_id(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-rss", "title": "x"},
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)
    assert summary.processed == 1

    actions = automation.list_recent_actions(limit=10)
    assert actions
    assert actions[0]["correlation_id"] == "corr-rss"


def test_event_automation_list_recent_actions_can_filter_by_correlation_id(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-a", "title": "a"},
        )
    )
    bus.emit(
        Event(
            kind="rss_article",
            source="rss_demo",
            payload={"correlation_id": "corr-b", "title": "b"},
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)
    assert summary.processed == 2

    actions = automation.list_recent_actions(limit=10, correlation_id="corr-a")
    assert actions
    assert all(item["correlation_id"] == "corr-a" for item in actions)


def test_event_automation_vision_frame_creates_alert(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "rayban_meta",
                "frame_id": "frame-123",
                "labels": ["door", "person"],
                "text": "hello",
                "frame_accepted": True,
                "frame_size_bytes": 1024,
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    assert "Vision frame alert" in pending[0]["payload"]["subject"]
    assert "rayban_meta" in pending[0]["payload"]["body"]


def test_event_automation_vision_frame_uses_embedded_analysis(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "rayban_meta",
                "frame_id": "frame-xyz",
                "labels": ["person"],
                "frame_accepted": True,
                "frame_size_bytes": 2048,
                "vision_analysis": {
                    "face_count": 2,
                    "colors": [
                        {"name": "blue", "pct": 55.5},
                        {"name": "gray", "pct": 25.0},
                    ],
                    "faces": [
                        {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.95},
                        {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "confidence": 0.9},
                    ],
                },
                "vision_faces": [
                    {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.95},
                    {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "confidence": 0.9},
                ],
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=2" in body
    assert "dominant_colors=blue:55.5%, gray:25.0%" in body


def test_event_automation_vision_frame_analyzes_base64_payload(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    def _fake_analyze(_image_b64, **_kwargs):
        return {
            "ok": True,
            "face_count": 1,
            "colors": [{"name": "red", "pct": 80.0}],
            "faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.9}],
            "capabilities": {"pil": True, "vision": True},
        }

    monkeypatch.setattr("jarvis.event_automation.analyze_frame_b64", _fake_analyze)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "iphone",
                "frame_id": "frame-b64",
                "labels": [],
                "frame_accepted": True,
                "frame_size_bytes": 111,
                "image_base64": "aGVsbG8=",
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=1" in body
    assert "dominant_colors=red:80.0%" in body


def test_event_automation_vision_frame_gates_low_face_confidence(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "iphone",
                "frame_id": "frame-low-conf",
                "labels": [],
                "frame_accepted": True,
                "frame_size_bytes": 2048,
                "vision_analysis": {
                    "face_count": 1,
                    "colors": [{"name": "blue", "pct": 90.0}],
                    "faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.5}],
                },
                "vision_faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.5}],
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=" not in body
    assert "dominant_colors=blue:90.0%" in body


def test_event_automation_vision_frame_gates_low_color_coverage(tmp_path):
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "iphone",
                "frame_id": "frame-low-coverage",
                "labels": [],
                "frame_accepted": True,
                "frame_size_bytes": 2048,
                "vision_analysis": {
                    "face_count": 2,
                    "colors": [{"name": "gray", "pct": 40.0}],
                    "faces": [
                        {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.9},
                        {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "confidence": 0.85},
                    ],
                },
                "vision_faces": [
                    {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.9},
                    {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "confidence": 0.85},
                ],
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=2" in body
    assert "dominant_colors=" not in body


def test_event_automation_vision_frame_confidence_gates_respect_config(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    config.vision_min_face_confidence = 0.5
    config.vision_min_color_coverage = 0.5
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "iphone",
                "frame_id": "frame-relaxed",
                "labels": [],
                "frame_accepted": True,
                "frame_size_bytes": 2048,
                "vision_analysis": {
                    "face_count": 1,
                    "colors": [{"name": "red", "pct": 55.0}],
                    "faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.6}],
                },
                "vision_faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.6}],
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=1" in body
    assert "dominant_colors=red:55.0%" in body


def test_event_automation_vision_frame_includes_landmarks(tmp_path):
    """Landmarks should be included in enrichment when face detection passes gates."""
    config = _make_config(tmp_path)
    bus = EventBus(config.event_bus_db)

    bus.emit(
        Event(
            kind="vision_frame",
            source="vision_iphone",
            payload={
                "device": "iphone",
                "frame_id": "frame-landmarks",
                "labels": [],
                "frame_accepted": True,
                "frame_size_bytes": 2048,
                "vision_analysis": {
                    "face_count": 1,
                    "colors": [{"name": "blue", "pct": 85.0}],
                    "faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.95}],
                    "landmarks": [
                        {
                            "landmarks": {
                                "left_eye": {"x": 0.15, "y": 0.25},
                                "right_eye": {"x": 0.25, "y": 0.25},
                                "nose": {"x": 0.2, "y": 0.3},
                            },
                            "features": {
                                "gaze": "center",
                                "head_pose": {"tilt": "straight", "nod": "level"},
                            },
                            "face_id": 0,
                        }
                    ],
                },
                "vision_faces": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4, "confidence": 0.95}],
            },
        )
    )

    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=10)

    assert summary.approvals_created == 1
    store = ApprovalStore(config.approval_db)
    pending = store.list_pending(limit=10)
    assert len(pending) == 1
    body = pending[0]["payload"]["body"]
    assert "face_count=1" in body
    # Landmarks should be included in the alert
    assert "landmarks=" in body
    assert "gaze=center" in body
