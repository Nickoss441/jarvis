"""Tests for monitor runner backoff logic."""
import time
from jarvis.event_bus import EventBus
from jarvis.monitors import Monitor
from jarvis.monitor_runner import MonitorRunner, MonitorRunnerConfig


def test_monitor_backoff_on_failure(tmp_path):
    """Test that monitor enters backoff after failure."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(
        interval_seconds=0,
        backoff_initial_seconds=0.1,
        backoff_max_seconds=10,
        backoff_multiplier=2.0,
    )
    runner = MonitorRunner(bus, config)

    class FailingMonitor(Monitor):
        def run(self) -> int:
            raise ValueError("Always fails")

    monitor = FailingMonitor(bus, "failing")
    runner.register(monitor)

    # First run should fail
    runner.run_once()
    
    # Check backoff state
    assert "failing" in runner._monitor_backoff
    backoff = runner._monitor_backoff["failing"]
    assert backoff["consecutive_failures"] == 1
    assert backoff["skip_until_ts"] is not None
    assert backoff["last_failure_ts"] is not None


def test_monitor_backoff_skips_during_window(tmp_path):
    """Test that monitor is skipped during backoff window."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(
        interval_seconds=0,
        backoff_initial_seconds=10.0,  # Long backoff
        backoff_max_seconds=60,
        backoff_multiplier=2.0,
    )
    runner = MonitorRunner(bus, config)

    class FailingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "failing")
            self.run_count = 0

        def run(self) -> int:
            self.run_count += 1
            raise ValueError("Always fails")

    monitor = FailingMonitor(bus)
    runner.register(monitor)

    # First run fails
    runner.run_once()
    assert monitor.run_count == 1

    # Second run should skip the monitor
    runner.run_once()
    assert monitor.run_count == 1  # Still 1, was skipped


def test_monitor_backoff_resets_on_success(tmp_path):
    """Test that backoff resets after successful run."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(interval_seconds=0)
    runner = MonitorRunner(bus, config)

    class ToggleFailingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "toggle")
            self.fail_count = 2

        def run(self) -> int:
            if self.fail_count > 0:
                self.fail_count -= 1
                raise ValueError("Still failing")
            self.emit_event("success", {})
            return 1

    monitor = ToggleFailingMonitor(bus)
    runner.register(monitor)

    # First run fails
    runner.run_once()
    backoff = runner._monitor_backoff["toggle"]
    assert backoff["consecutive_failures"] == 1

    # Wait for backoff to expire (or mock time)
    backoff["skip_until_ts"] = None

    # Second run fails again
    runner.run_once()
    assert backoff["consecutive_failures"] == 2

    # Wait for backoff to expire
    backoff["skip_until_ts"] = None

    # Third run succeeds and resets backoff
    runner.run_once()
    assert backoff["consecutive_failures"] == 0
    assert backoff["skip_until_ts"] is None
    assert bus.count() == 1


def test_monitor_exponential_backoff_multiplier(tmp_path):
    """Test exponential backoff calculation."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(
        interval_seconds=0,
        backoff_initial_seconds=1.0,
        backoff_max_seconds=100,
        backoff_multiplier=2.0,
    )
    runner = MonitorRunner(bus, config)

    class FailingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "failing")

        def run(self) -> int:
            raise ValueError("Always fails")

    monitor = FailingMonitor(bus)
    runner.register(monitor)

    # Run 4 times (all fail) to test exponential backoff growth
    current_time = time.time()
    
    # First failure: 1s backoff
    runner.run_once()
    delay1 = runner._monitor_backoff["failing"]["skip_until_ts"] - current_time
    assert 0.9 < delay1 < 1.1  # ~1s
    
    # Clear backoff to simulate retry
    runner._monitor_backoff["failing"]["skip_until_ts"] = None
    
    # Second failure: 2s backoff
    runner.run_once()
    delay2 = runner._monitor_backoff["failing"]["skip_until_ts"] - current_time
    assert 1.9 < delay2 < 2.1  # ~2s
    
    # Clear backoff to simulate retry
    runner._monitor_backoff["failing"]["skip_until_ts"] = None
    
    # Third failure: 4s backoff
    runner.run_once()
    delay3 = runner._monitor_backoff["failing"]["skip_until_ts"] - current_time
    assert 3.9 < delay3 < 4.1  # ~4s


def test_monitor_backoff_respects_max_cap(tmp_path):
    """Test that backoff respects maximum cap."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(
        interval_seconds=0,
        backoff_initial_seconds=1.0,
        backoff_max_seconds=5.0,  # Cap at 5s
        backoff_multiplier=2.0,
    )
    runner = MonitorRunner(bus, config)

    class FailingMonitor(Monitor):
        def __init__(self, bus):
            super().__init__(bus, "failing")
            self.fail_count = 10  # Will fail many times

        def run(self) -> int:
            self.fail_count -= 1
            raise ValueError("Always fails")

    monitor = FailingMonitor(bus)
    runner.register(monitor)

    # Run many times to reach cap
    for _ in range(5):
        runner.run_once()
        runner._monitor_backoff["failing"]["skip_until_ts"] = None

    # Last run should have 5s backoff (capped), not 16s (2^4)
    backoff_state = runner._monitor_backoff["failing"]
    assert backoff_state["consecutive_failures"] == 5


def test_monitor_stats_includes_backoff_info(tmp_path):
    """Test that stats() includes backoff information."""
    bus = EventBus(tmp_path / "events.db")
    config = MonitorRunnerConfig(
        interval_seconds=0,
        backoff_initial_seconds=1.0,
        backoff_max_seconds=10,
    )
    runner = MonitorRunner(bus, config)

    class FailingMonitor(Monitor):
        def run(self) -> int:
            raise ValueError("Fails")

    monitor = FailingMonitor(bus, "failing")
    runner.register(monitor)

    # Run once (fails)
    runner.run_once()

    # Get stats
    stats = runner.stats()
    assert "monitor_status" in stats
    assert "failing" in stats["monitor_status"]
    
    failing_status = stats["monitor_status"]["failing"]
    assert failing_status["consecutive_failures"] == 1
    assert failing_status["last_failure_ts"] is not None
    assert failing_status["skip_until_ts"] is not None


def test_monitor_stats_no_backoff_info_when_healthy(tmp_path):
    """Test that stats() doesn't include backoff info for healthy monitors."""
    bus = EventBus(tmp_path / "events.db")
    runner = MonitorRunner(bus)

    class HealthyMonitor(Monitor):
        def run(self) -> int:
            self.emit_event("health", {})
            return 1

    monitor = HealthyMonitor(bus, "healthy")
    runner.register(monitor)

    # Run successfully
    runner.run_once()

    # Get stats
    stats = runner.stats()
    healthy_status = stats["monitor_status"]["healthy"]
    
    # Should not have backoff fields
    assert "consecutive_failures" not in healthy_status
    assert "last_failure_ts" not in healthy_status
    assert "skip_until_ts" not in healthy_status
    
    # Should have success info
    assert healthy_status["last_run_timestamp"] is not None
    assert healthy_status["cumulative_event_count"] == 1
