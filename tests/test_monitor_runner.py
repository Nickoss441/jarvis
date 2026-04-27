"""Tests for monitor runner."""
from pathlib import Path

from jarvis.event_bus import EventBus, Event
from jarvis.monitors import Monitor
from jarvis.monitor_runner import MonitorRunner, MonitorRunnerConfig


def test_monitor_runner_register(tmp_path):
    """Test registering monitors."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus)

    class TestMonitor(Monitor):
        def run(self) -> int:
            return 0

    monitor1 = TestMonitor(bus, "test1")
    monitor2 = TestMonitor(bus, "test2")

    runner.register(monitor1)
    runner.register(monitor2)

    assert len(runner.monitors) == 2


def test_monitor_runner_run_once(tmp_path):
    """Test running all monitors once."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus)

    class CountingMonitor(Monitor):
        def __init__(self, bus, source, count):
            super().__init__(bus, source)
            self.count = count

        def run(self) -> int:
            for i in range(self.count):
                self.emit_event("test_event", {"num": i})
            return self.count

    runner.register(CountingMonitor(bus, "monitor1", 3))
    runner.register(CountingMonitor(bus, "monitor2", 2))

    events = runner.run_once()
    assert events == 5
    assert bus.count() == 5


def test_monitor_runner_run_loop(tmp_path):
    """Test monitor runner loop."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus, MonitorRunnerConfig(interval_seconds=0))

    class TestMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "test")
            self.runs = 0

        def run(self) -> int:
            self.runs += 1
            self.emit_event("test", {})
            return 1

    monitor = TestMonitor(bus)
    runner.register(monitor)

    # Run 3 iterations
    runner.run_loop(max_iterations=3)

    assert monitor.runs == 3
    assert bus.count() == 3
    assert not runner._running


def test_monitor_runner_stats(tmp_path):
    """Test runner statistics."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus)

    # Emit some events
    bus.emit(Event(kind="event1", source="test", payload={}))
    bus.emit(Event(kind="event2", source="test", payload={}))
    bus.emit(Event(kind="event3", source="test", payload={}))

    stats = runner.stats()
    assert stats["total_events"] == 3
    assert stats["unprocessed_events"] == 3
    assert stats["processed_events"] == 0
    assert stats["monitors"] == 0
    assert "monitor_status" in stats
    assert stats["monitor_status"] == {}


def test_monitor_runner_error_handling(tmp_path):
    """Test that runner continues on monitor error."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus, MonitorRunnerConfig(interval_seconds=0))

    class FailingMonitor(Monitor):
        def run(self) -> int:
            raise ValueError("Monitor error")

    class SuccessMonitor(Monitor):
        def run(self) -> int:
            self.emit_event("success", {})
            return 1

    runner.register(FailingMonitor(bus, "failing"))
    runner.register(SuccessMonitor(bus, "success"))

    # Run once - should not crash
    events = runner.run_once()
    # Only the success monitor emits
    assert events == 1
    assert bus.count() == 1


def test_monitor_runner_is_stopped_returns_false_when_no_sentinel(tmp_path, monkeypatch):
    """Test is_stopped() returns False when sentinel doesn't exist."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    
    assert MonitorRunner.is_stopped() is False


def test_monitor_runner_is_stopped_returns_true_when_sentinel_exists(tmp_path, monkeypatch):
    """Test is_stopped() returns True when sentinel file exists."""
    sentinel_dir = tmp_path / ".jarvis"
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    (sentinel_dir / "stopped").write_text("123", encoding="utf-8")
    
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    
    assert MonitorRunner.is_stopped() is True


def test_monitor_runner_skips_execution_when_stopped(tmp_path, monkeypatch):
    """Test that monitor runner skips execution when sentinel exists."""
    # Create sentinel
    sentinel_dir = tmp_path / ".jarvis"
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    (sentinel_dir / "stopped").write_text("123", encoding="utf-8")
    
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus, MonitorRunnerConfig(interval_seconds=0))

    class CountingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "test")
            self.run_count = 0

        def run(self) -> int:
            self.run_count += 1
            self.emit_event("test", {})
            return 1

    monitor = CountingMonitor(bus)
    runner.register(monitor)

    # Run 2 iterations with sentinel file present
    runner.run_loop(max_iterations=2)

    # Monitor should not run at all when stopped
    assert monitor.run_count == 0
    assert bus.count() == 0


def test_monitor_runner_resumes_execution_after_sentinel_removed(tmp_path, monkeypatch):
    """Test that monitor runner resumes after sentinel file is removed."""
    sentinel_dir = tmp_path / ".jarvis"
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    sentinel = sentinel_dir / "stopped"
    
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus, MonitorRunnerConfig(interval_seconds=0))

    class CountingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "test")
            self.run_count = 0

        def run(self) -> int:
            self.run_count += 1
            self.emit_event("test", {})
            return 1

    monitor = CountingMonitor(bus)
    runner.register(monitor)
    
    # Write sentinel file for first iteration
    sentinel.write_text("123", encoding="utf-8")

    # Run with custom logic to remove sentinel after first iteration
    runner._running = True
    iteration = 0
    max_iterations = 3
    
    while runner._running and iteration < max_iterations:
        if iteration == 1:
            # Remove sentinel file after first skipped iteration
            sentinel.unlink()
        
        if MonitorRunner.is_stopped():
            iteration += 1
            continue
        
        runner.run_once()
        iteration += 1
    
    runner._running = False
    
    # Monitor should run in iterations 2 and 3 (after sentinel removed)
    assert monitor.run_count == 2
    assert bus.count() == 2
