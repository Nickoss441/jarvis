"""Monitor runner for the perception layer.

Coordinates periodic execution of monitors and handles event processing.
"""
import logging
import math
import time
from pathlib import Path
from typing import TYPE_CHECKING, List
from dataclasses import dataclass, field

from .event_bus import EventBus
from .monitors import (
    CalendarMonitor,
    FilesystemMonitor,
    Monitor,
    RSSMonitor,
    VisionIngestMonitor,
    WebhookMonitor,
)

if TYPE_CHECKING:
    from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class MonitorRunnerConfig:
    """Configuration for monitor runner."""

    interval_seconds: int = 60  # Check interval between monitor runs
    max_events_per_run: int = 100  # Max events to emit per monitor run
    backoff_initial_seconds: int = 5  # Initial backoff delay for first failure
    backoff_max_seconds: int = 3600  # Max backoff cap (1 hour)
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier


class MonitorRunner:
    """Coordinates execution of perception monitors.

    Runs monitors periodically and collects their events into the event bus.
    """

    def __init__(self, event_bus: EventBus, config: MonitorRunnerConfig = None):
        """Initialize monitor runner.

        Args:
            event_bus: EventBus instance for emitting events
            config: MonitorRunnerConfig (uses defaults if not provided)
        """
        self.bus = event_bus
        self.config = config or MonitorRunnerConfig()
        self.monitors: List[Monitor] = []
        self._running = False
        self._monitor_stats: dict[str, dict] = {}  # Track last-run time and event count per monitor
        # Backoff state: source -> {consecutive_failures, last_failure_ts, skip_until_ts}
        self._monitor_backoff: dict[str, dict] = {}

    def register(self, monitor: Monitor) -> None:
        """Register a monitor to be run periodically.

        Args:
            monitor: Monitor instance
        """
        self.monitors.append(monitor)
        logger.info(f"Registered monitor: {monitor.source}")

    @staticmethod
    def is_stopped() -> bool:
        """Check if the stop sentinel file exists.

        Returns:
            True if stopped sentinel exists at D:/jarvis-data/stopped
        """
        sentinel = Path("D:/jarvis-data/stopped")
        return sentinel.exists()

    def run_once(self) -> int:
        """Run all monitors once and return total events emitted.

        Returns:
            Total number of events emitted across all monitors
        """
        total_events = 0
        current_time = time.time()

        for monitor in self.monitors:
            source = monitor.source
            
            # Initialize backoff state if needed
            if source not in self._monitor_backoff:
                self._monitor_backoff[source] = {
                    "consecutive_failures": 0,
                    "last_failure_ts": None,
                    "skip_until_ts": None,
                }
            
            backoff_state = self._monitor_backoff[source]
            
            # Skip this monitor if we're in backoff window
            if backoff_state["skip_until_ts"] is not None and current_time < backoff_state["skip_until_ts"]:
                logger.debug(
                    f"Monitor {source} in backoff (retry in {backoff_state['skip_until_ts'] - current_time:.1f}s)"
                )
                continue
            
            # Clear skip_until_ts if backoff window has passed
            if backoff_state["skip_until_ts"] is not None and current_time >= backoff_state["skip_until_ts"]:
                backoff_state["skip_until_ts"] = None
            
            try:
                events_emitted = monitor.run()
                total_events += events_emitted
                
                # Track stats per monitor
                if source not in self._monitor_stats:
                    self._monitor_stats[source] = {
                        "last_run_timestamp": None,
                        "cumulative_event_count": 0,
                    }
                self._monitor_stats[source]["last_run_timestamp"] = current_time
                self._monitor_stats[source]["cumulative_event_count"] += events_emitted
                
                # Reset backoff state on successful run
                backoff_state["consecutive_failures"] = 0
                backoff_state["skip_until_ts"] = None
                
                if events_emitted > 0:
                    logger.debug(
                        f"Monitor {source} emitted {events_emitted} events"
                    )
            except Exception as e:
                # Increment failure count and apply exponential backoff
                backoff_state["consecutive_failures"] += 1
                backoff_state["last_failure_ts"] = current_time
                
                # Calculate exponential backoff with cap
                backoff_delay = self.config.backoff_initial_seconds * (
                    self.config.backoff_multiplier ** (backoff_state["consecutive_failures"] - 1)
                )
                backoff_delay = min(backoff_delay, self.config.backoff_max_seconds)
                backoff_state["skip_until_ts"] = current_time + backoff_delay
                
                logger.error(
                    f"Monitor {source} failed ({backoff_state['consecutive_failures']} failures): {e}. "
                    f"Backing off for {backoff_delay:.1f}s",
                    exc_info=True
                )

        return total_events

    def run_loop(self, max_iterations: int = None) -> None:
        """Run monitors in a loop.

        Args:
            max_iterations: Max number of iterations (None for infinite)
        """
        self._running = True
        iteration = 0

        logger.info(
            f"Starting monitor runner with {len(self.monitors)} monitors "
            f"(interval={self.config.interval_seconds}s)"
        )

        while self._running and (max_iterations is None or iteration < max_iterations):
            try:
                # Check if system is stopped via sentinel file
                if self.is_stopped():
                    logger.info("Monitor runner paused (stop sentinel exists)")
                    time.sleep(self.config.interval_seconds)
                    iteration += 1
                    continue

                start = time.time()
                events = self.run_once()
                elapsed = time.time() - start

                if events > 0:
                    logger.info(
                        f"Run {iteration}: emitted {events} events in {elapsed:.2f}s"
                    )

                # Sleep remainder of interval
                sleep_time = self.config.interval_seconds - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

                iteration += 1
            except KeyboardInterrupt:
                logger.info("Monitor runner interrupted")
                break
            except Exception as e:
                logger.error(f"Monitor runner error: {e}", exc_info=True)
                time.sleep(self.config.interval_seconds)

        self._running = False
        logger.info(f"Monitor runner stopped after {iteration} iterations")

    def stop(self) -> None:
        """Stop the monitor runner."""
        self._running = False

    def stats(self) -> dict:
        """Get monitor and event bus statistics.

        Returns:
            Dict with monitor-specific stats and event counts
        """
        result = {
            "monitors": len(self.monitors),
            "total_events": self.bus.count(),
            "unprocessed_events": self.bus.count(processed=False),
            "processed_events": self.bus.count(processed=True),
            "monitor_status": {},
        }
        
        # Add per-monitor status with backoff info
        for monitor in self.monitors:
            source = monitor.source
            stats = self._monitor_stats.get(source, {})
            backoff = self._monitor_backoff.get(source, {})
            
            status_entry = {
                "last_run_timestamp": stats.get("last_run_timestamp"),
                "cumulative_event_count": stats.get("cumulative_event_count", 0),
            }
            
            # Add backoff info if monitor has failures
            if backoff.get("consecutive_failures", 0) > 0:
                status_entry["consecutive_failures"] = backoff.get("consecutive_failures", 0)
                status_entry["last_failure_ts"] = backoff.get("last_failure_ts")
                status_entry["skip_until_ts"] = backoff.get("skip_until_ts")
            
            result["monitor_status"][source] = status_entry
        
        return result


def register_configured_monitors(runner: MonitorRunner, config: "Config") -> None:
    """Register the default configured monitor set on a runner."""
    bus = runner.bus

    runner.register(CalendarMonitor(bus, str(config.calendar_ics)))
    runner.register(FilesystemMonitor(bus, str(config.dropzone_dir)))
    if config.rss_feed_url:
        runner.register(RSSMonitor(bus, config.rss_feed_url, source_name="default"))
    runner.register(
        VisionIngestMonitor(
            bus,
            source_name=config.vision_source_name,
            host=config.vision_host,
            port=config.vision_port,
            signing_secret=config.vision_secret,
            max_frame_bytes=config.vision_max_frame_bytes,
        )
    )
    runner.register(
        WebhookMonitor(
            bus,
            source_name=config.webhook_source_name,
            host=config.webhook_host,
            port=config.webhook_port,
            signing_secret=config.webhook_secret,
            path_kind_map=config.webhook_path_kind_map,
        )
    )
