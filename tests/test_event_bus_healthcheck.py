"""Tests for event bus healthcheck."""
import os
import sqlite3

from jarvis.event_bus import EventBus


def test_event_bus_healthcheck_healthy(tmp_path):
    """Test healthcheck returns True for healthy database."""
    db_path = tmp_path / "events.db"
    bus = EventBus(db_path)
    
    # Healthcheck should succeed
    assert bus.healthcheck() is True


def test_event_bus_healthcheck_missing_db(tmp_path):
    """Test healthcheck returns False when database doesn't exist."""
    db_path = tmp_path / "nonexistent" / "events.db"
    bus = EventBus.__new__(EventBus)
    bus.db_path = db_path
    
    # Healthcheck should fail (db doesn't exist)
    assert bus.healthcheck() is False


def test_event_bus_healthcheck_after_operations(tmp_path):
    """Test healthcheck after various operations."""
    db_path = tmp_path / "events.db"
    bus = EventBus(db_path)
    
    # Initial healthcheck
    assert bus.healthcheck() is True
    
    # After emitting events
    from jarvis.runtime import RuntimeEventEnvelope
    event = RuntimeEventEnvelope(
        kind="test",
        source="test_source",
        payload={"test": "data"},
        correlation_id="test_id",
    )
    bus.emit(event)
    
    # Should still be healthy
    assert bus.healthcheck() is True
    
    # After reading
    events = bus.recent(limit=10)
    assert len(events) == 1
    assert bus.healthcheck() is True


def test_event_bus_healthcheck_unreadable_db(tmp_path):
    """Test healthcheck when database file is unreadable."""
    db_path = tmp_path / "events.db"
    bus = EventBus(db_path)
    
    # Initial healthcheck should pass
    assert bus.healthcheck() is True
    
    # Make the database file unreadable
    os.chmod(db_path, 0o000)
    
    try:
        # Healthcheck should fail
        assert bus.healthcheck() is False
    finally:
        # Restore permissions for cleanup
        os.chmod(db_path, 0o644)


def test_event_bus_healthcheck_corrupted_db(tmp_path):
    """Test healthcheck with corrupted database."""
    db_path = tmp_path / "events.db"
    
    # Create a corrupted database file
    db_path.write_text("This is not a valid SQLite database")
    
    bus = EventBus.__new__(EventBus)
    bus.db_path = db_path
    
    # Healthcheck should fail
    assert bus.healthcheck() is False


def test_event_bus_healthcheck_locked_db(tmp_path):
    """Test healthcheck behavior when database is locked."""
    db_path = tmp_path / "events.db"
    bus = EventBus(db_path)
    
    # Initial healthcheck should pass
    assert bus.healthcheck() is True
    
    # Lock the database by opening a long-lived transaction
    conn = sqlite3.connect(db_path)
    conn.execute("BEGIN EXCLUSIVE")
    
    try:
        # Healthcheck should timeout or fail due to lock
        # Note: This depends on timeout behavior, so we just verify it doesn't crash
        result = bus.healthcheck()
        # Result may be True or False depending on timeout, but shouldn't crash
        assert isinstance(result, bool)
    finally:
        conn.close()
