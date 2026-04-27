"""Module entrypoint for interactive REPL and utility commands."""
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.request
from statistics import median

from .approval_service import ApprovalService
from .approval_api import create_approval_api_server
from .audit import AuditLog
from .cli import repl
from .config import Config
from .trade_review import generate_trade_review_artifact
from .event_bus import EventBus
from .event_automation import EventAutomation
from .monitor_runner import MonitorRunner, register_configured_monitors
from .monitors import CalendarMonitor, FilesystemMonitor, RSSMonitor, VisionIngestMonitor, WebhookMonitor
from .vision_bridge import build_shortcut_guide, build_shortcut_template
from .vision_analyze import analyze_frame_b64
from .tools.trade import (
    analyze_trade_streaks,
    build_trade_performance_report,
    build_trade_replay_report,
    calculate_portfolio_metrics,
    check_market_hours,
    estimate_trade_value_at_risk,
    log_trade_journal_entry,
)
from .perception.voice import build_voice_adapter_stack
from .runtime import RuntimeEventEnvelope


def _audit_verify() -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    is_valid = AuditLog(config.audit_db).verify()
    if is_valid:
        print("Audit OK: hash chain is valid.")
        return 0

    print("Audit FAILED: hash chain is invalid.")
    return 2


def _audit_export() -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    log = AuditLog(config.audit_db)
    log.export_jsonl(sys.stdout)
    return 0


def _audit_stats() -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    stats = AuditLog(config.audit_db).stats()
    print(json.dumps(stats, sort_keys=True, indent=2))
    return 0


def _trade_replay_report(limit: int = 50) -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    report = build_trade_replay_report(AuditLog(config.audit_db), limit=limit)
    print(json.dumps(report, sort_keys=True))
    return 0


def _trade_performance_report(mode: str = "paper") -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)
    config.trades_log.parent.mkdir(parents=True, exist_ok=True)

    report = build_trade_performance_report(
        config.trades_log,
        audit_log=AuditLog(config.audit_db),
        mode=mode,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


def _trade_review_artifact(
    output_file: str | None = None,
    reviewer: str = "",
    strategy_version: str = "",
) -> int:
    config = Config.from_env()
    payload = generate_trade_review_artifact(
        config,
        output_file=output_file,
        reviewer=reviewer,
        strategy_version=strategy_version,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


def _trade_streaks(mode: str = "paper", limit: int = 100) -> int:
    config = Config.from_env()
    config.trades_log.parent.mkdir(parents=True, exist_ok=True)

    payload = analyze_trade_streaks(config.trades_log, mode=mode, limit=limit)
    print(json.dumps(payload, sort_keys=True))
    return 0


def _trade_portfolio_metrics(mode: str = "paper") -> int:
    config = Config.from_env()
    config.trades_log.parent.mkdir(parents=True, exist_ok=True)

    payload = calculate_portfolio_metrics(config.trades_log, mode=mode)
    print(json.dumps(payload, sort_keys=True))
    return 0


def _trade_market_hours(instrument: str, market: str = "US") -> int:
    payload = check_market_hours(instrument, market=market)
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload.get("error") is None else 1


def _trade_risk_estimate(
    *,
    position_size: float,
    entry_price: float,
    stop_loss_price: float,
    take_profit_price: float | None = None,
    confidence_level: float = 0.95,
) -> int:
    payload = estimate_trade_value_at_risk(
        position_size=position_size,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
        confidence_level=confidence_level,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload.get("ok") else 1


def _trade_journal(
    trade_id: str,
    *,
    setup: str = "",
    lessons: str = "",
    improvement: str = "",
) -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    payload = log_trade_journal_entry(
        AuditLog(config.audit_db),
        trade_id=trade_id,
        setup=setup,
        lessons=lessons,
        improvement=improvement,
    )
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload.get("ok") else 1


def _stop() -> int:
    """Write sentinel file to pause all monitors and gated operations."""
    sentinel = Path.home() / ".jarvis" / "stopped"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(str(int(time.time())), encoding="utf-8")
    print(f"Jarvis stopped. Sentinel file: {sentinel}")
    return 0


def _resume() -> int:
    """Remove sentinel file to resume monitors and gated operations."""
    sentinel = Path.home() / ".jarvis" / "stopped"
    if sentinel.exists():
        sentinel.unlink()
        print(f"Jarvis resumed. Removed sentinel file: {sentinel}")
        return 0
    print(f"Jarvis not stopped (no sentinel file at {sentinel})")
    return 0


def _audit_correlation(
    correlation_id: str,
    limit: int = 100,
    kind: str | None = None,
) -> int:
    config = Config.from_env()
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)

    rows = AuditLog(config.audit_db).by_correlation_id(
        correlation_id,
        limit=limit,
        kind=kind,
    )
    if not rows:
        print(
            json.dumps(
                {
                    "ok": True,
                    "correlation_id": correlation_id,
                    "kind": kind,
                    "count": 0,
                    "events": [],
                },
                sort_keys=True,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "ok": True,
                "correlation_id": correlation_id,
                "kind": kind,
                "count": len(rows),
                "events": rows,
            },
            sort_keys=True,
        )
    )
    return 0


def _approvals_list() -> int:
    config = Config.from_env()
    service = ApprovalService(config)
    rows = service.list_pending(limit=100)
    if not rows:
        print("No pending approvals.")
        return 0

    for row in rows:
        print(
            json.dumps(
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "status": row["status"],
                    "payload": row["payload"],
                },
                sort_keys=True,
            )
        )
    return 0


def _approvals_approve(approval_id: str, reason: str = "") -> int:
    config = Config.from_env()
    service = ApprovalService(config)
    ok = service.approve(approval_id, reason=reason)
    if not ok:
        print("Approval not found or not pending.")
        return 1
    print(f"Approved: {approval_id}")
    return 0


def _approvals_reject(approval_id: str, reason: str = "") -> int:
    config = Config.from_env()
    service = ApprovalService(config)
    ok = service.reject(approval_id, reason=reason)
    if not ok:
        print("Approval not found or not pending.")
        return 1
    print(f"Rejected: {approval_id}")
    return 0


def _approvals_dispatch() -> int:
    config = Config.from_env()
    service = ApprovalService(config)
    summary = service.dispatch(limit=100)

    if summary.skipped_reason == "max_per_run_zero":
        print("Dispatch max-per-run is 0, skipping dispatch.")
        return 0
    if summary.skipped_reason == "global_cooldown":
        print("Dispatch cooldown active, skipping dispatch.")
        return 0
    if summary.skipped_reason == "kind_cooldown":
        print("Per-kind dispatch cooldown active, skipping dispatch.")
        return 0
    if summary.skipped_reason == "tier_cooldown":
        print("Tier-based dispatch cooldown active, skipping dispatch.")
        return 0
    if summary.skipped_reason == "kind_or_tier_cooldown":
        print("Per-kind/tier dispatch cooldown active, skipping dispatch.")
        return 0
    if summary.skipped_reason == "none_approved":
        print("No approved items to dispatch.")
        return 0

    for item in summary.items:
        print(json.dumps(item, sort_keys=True))

    if summary.remaining > 0:
        print(f"Dispatch limit reached, {summary.remaining} approved item(s) remain queued.")
    if summary.skipped_by_kind_cooldown > 0:
        print(
            f"Per-kind cooldown skipped {summary.skipped_by_kind_cooldown} approved item(s)."
        )
    if summary.skipped_by_tier_cooldown > 0:
        print(
            f"Tier cooldown skipped {summary.skipped_by_tier_cooldown} approved item(s)."
        )

    return 0 if summary.failures == 0 else 2


def _approvals_api(host: str | None = None, port: int | None = None) -> int:
    config = Config.from_env()
    bind_host = host or config.approvals_api_host
    requested_port = config.approvals_api_port if port is None else port

    server = None
    active_port = requested_port
    for candidate_port in range(requested_port, requested_port + 10):
        try:
            server = create_approval_api_server(
                config=config,
                host=bind_host,
                port=candidate_port,
            )
            active_port = candidate_port
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise

    if server is None:
        print(
            "Could not start Approval API: "
            f"ports {requested_port}-{requested_port + 9} are in use."
        )
        return 1

    if active_port != requested_port:
        print(
            f"Requested port {requested_port} busy; "
            f"using http://{bind_host}:{active_port} instead."
        )

    print(f"Approval API listening on http://{bind_host}:{active_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _approvals_seed(count: int = 3) -> int:
    """Create demo pending approvals for testing/demos."""
    config = Config.from_env()
    service = ApprovalService(config)

    demo_payloads = [
        {
            "kind": "message_send",
            "payload": {
                "channel": "email",
                "recipient": "alice@example.com",
                "subject": "Project Update",
                "body": "Hi Alice, here's the latest project status...",
            },
        },
        {
            "kind": "message_send",
            "payload": {
                "channel": "slack",
                "recipient": "#engineering",
                "body": "Team standup in 15 minutes in the usual room.",
            },
        },
        {
            "kind": "message_send",
            "payload": {
                "channel": "sms",
                "recipient": "+14155552671",
                "body": "Your appointment reminder: tomorrow at 2pm",
            },
        },
    ]

    created_ids = []
    for i in range(min(count, len(demo_payloads))):
        item = demo_payloads[i]
        approval_id = service.request(item["kind"], item["payload"])
        created_ids.append(approval_id)
        print(f"Created approval {i + 1}/{min(count, len(demo_payloads))}: {approval_id}")

    if count > len(demo_payloads):
        print(f"\nNote: only {len(demo_payloads)} demo payloads available.")

    print(f"\nOpen web UI to review and approve:")
    print(f"  http://127.0.0.1:8083/")

    return 0


def _events_stats() -> int:
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)
    print(
        json.dumps(
            {
                "event_bus_db": str(config.event_bus_db),
                "total": bus.count(),
                "unprocessed": bus.count(processed=False),
                "processed": bus.count(processed=True),
                "calendar_event": bus.count(kind="calendar_event"),
                "rss_article": bus.count(kind="rss_article"),
                "filesystem_new_file": bus.count(kind="filesystem_new_file"),
                "vision_frame": bus.count(kind="vision_frame"),
            },
            sort_keys=True,
        )
    )
    return 0


def _monitors_status() -> int:
    """Show status of all monitors."""
    config = Config.from_env()
    config.event_bus_db.parent.mkdir(parents=True, exist_ok=True)

    bus = EventBus(config.event_bus_db)
    runner = MonitorRunner(bus)

    register_configured_monitors(runner, config)

    stats = runner.stats()
    print(json.dumps(stats, sort_keys=True, indent=2))
    return 0


def _events_list(limit: int = 20, unprocessed_only: bool = False) -> int:
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)

    if unprocessed_only:
        events = bus.list_unprocessed(limit=limit)
    else:
        events = bus.recent(limit=limit)

    if not events:
        print("No events found.")
        return 0

    for event in events:
        print(
            json.dumps(
                {
                    "id": event.id,
                    "kind": event.kind,
                    "source": event.source,
                    "processed": event.processed,
                    "payload": event.payload,
                },
                sort_keys=True,
            )
        )

    return 0


def _events_process(limit: int = 50) -> int:
    config = Config.from_env()
    automation = EventAutomation(config)
    summary = automation.process_unprocessed(limit=limit)

    print(
        json.dumps(
            {
                "processed": summary.processed,
                "approvals_created": summary.approvals_created,
                "skipped": summary.skipped,
                "duplicates": summary.duplicates,
                "throttled": summary.throttled,
                "failures": summary.failures,
                "items": summary.items,
            },
            sort_keys=True,
        )
    )

    return 0 if summary.failures == 0 else 2


def _events_actions(
    limit: int = 50,
    event_kind: str | None = None,
    correlation_id: str | None = None,
) -> int:
    config = Config.from_env()
    automation = EventAutomation(config)
    rows = automation.list_recent_actions(
        limit=limit,
        event_kind=event_kind,
        correlation_id=correlation_id,
    )

    if not rows:
        print("No automation actions found.")
        return 0

    for row in rows:
        print(json.dumps(row, sort_keys=True))

    return 0


def _events_prune_actions(days: int | None = None) -> int:
    config = Config.from_env()
    retention_days = config.event_actions_retention_days if days is None else max(1, days)
    automation = EventAutomation(config)
    deleted = automation.prune_actions(older_than_days=retention_days)

    print(
        json.dumps(
            {
                "deleted": deleted,
                "older_than_days": retention_days,
            },
            sort_keys=True,
        )
    )
    return 0


def _location_update(
    latitude: float,
    longitude: float,
    source: str = "manual",
    accuracy_m: float | None = None,
) -> int:
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)

    payload: dict[str, object] = {
        "latitude": float(latitude),
        "longitude": float(longitude),
    }
    if accuracy_m is not None:
        payload["accuracy_m"] = float(accuracy_m)

    event = RuntimeEventEnvelope(
        kind="location_update",
        source=source or "manual",
        payload=payload,
    )
    bus.emit(event)
    print(
        json.dumps(
            {
                "ok": True,
                "event_id": event.id,
                "kind": event.kind,
                "source": event.source,
                "payload": payload,
            },
            sort_keys=True,
        )
    )
    return 0


def _location_last() -> int:
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)
    rows = bus.recent(limit=1, kind="location_update")
    if not rows:
        print(json.dumps({"ok": False, "error": "no_location_data"}, sort_keys=True))
        return 1

    row = rows[0]
    print(
        json.dumps(
            {
                "ok": True,
                "id": row.id,
                "kind": row.kind,
                "source": row.source,
                "timestamp": row.timestamp,
                "payload": row.payload,
            },
            sort_keys=True,
        )
    )
    return 0


def _consume_flag_value(
    tokens: list[str],
    idx: int,
    flag: str,
    missing_error: str,
) -> tuple[str | None, int, str | None]:
    """Consume `--flag value` or `--flag=value` style tokens.

    Returns (value, next_index, error_code). If the token at `idx` does not
    match `flag`, returns (None, idx, None).
    """
    token = tokens[idx]
    if token == flag:
        if idx + 1 >= len(tokens):
            return None, idx + 1, missing_error
        return tokens[idx + 1], idx + 2, None

    prefix = f"{flag}="
    if token.startswith(prefix):
        value = token[len(prefix):]
        if not value:
            return None, idx + 1, missing_error
        return value, idx + 1, None

    return None, idx, None


def _parse_int_arg(
    raw_value: str,
    invalid_error: str,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> tuple[int | None, dict[str, object] | None]:
    """Parse integer argument with optional bounds and standard error payload."""
    try:
        parsed = int(raw_value)
    except ValueError:
        return None, {"ok": False, "error": invalid_error, "value": raw_value}

    if min_value is not None and parsed < min_value:
        return None, {"ok": False, "error": invalid_error, "value": raw_value}
    if max_value is not None and parsed > max_value:
        return None, {"ok": False, "error": invalid_error, "value": raw_value}

    return parsed, None


def _monitor_run_once() -> int:
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)
    runner = MonitorRunner(bus)

    runner.register(CalendarMonitor(bus, str(config.calendar_ics)))
    runner.register(FilesystemMonitor(bus, str(config.dropzone_dir)))
    if config.rss_feed_url:
        runner.register(RSSMonitor(bus, config.rss_feed_url, source_name="default"))

    emitted = runner.run_once()
    print(
        json.dumps(
            {
                "emitted": emitted,
                "monitors": len(runner.monitors),
                "event_bus_db": str(config.event_bus_db),
                "rss_enabled": bool(config.rss_feed_url),
            },
            sort_keys=True,
        )
    )
    return 0


def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (float(pct) / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def _voice_self_test(
    iterations: int = 10,
    max_roundtrip_ms: float = 100.0,
) -> int:
    """Run local voice round-trip benchmark and acceptance gate."""
    config = Config.from_env()
    stack = build_voice_adapter_stack(
        wake_word=config.voice_wake_word,
        stt_provider=config.voice_stt_provider,
        tts_provider=config.voice_tts_provider,
        tts_api_key=config.voice_tts_api_key,
        tts_voice_ids={
            "male": config.voice_tts_voice_id_male,
            "female": config.voice_tts_voice_id_female,
        },
        tts_default_voice=config.voice_tts_default_voice,
        tts_model=config.voice_tts_model,
        tts_fallback_provider=config.voice_tts_fallback_provider,
    )

    safe_iterations = max(1, min(int(iterations), 500))
    sample_audio = f"{config.voice_wake_word} what is on my calendar today".encode("utf-8")

    roundtrip_ms: list[float] = []
    failures: list[str] = []
    triggers = 0

    for _ in range(safe_iterations):
        start_ns = time.perf_counter_ns()

        triggered = bool(stack.wake_word.detect_trigger(sample_audio))
        if triggered:
            triggers += 1
        if not triggered:
            failures.append("wake_word_not_detected")
            continue

        stt_out = stack.stt.transcribe(sample_audio, language="en")
        if stt_out.get("error"):
            failures.append("stt_error")
            continue

        tts_out = stack.tts.synthesize(
            str(stt_out.get("text") or ""),
            voice=config.voice_tts_default_voice,
        )
        if tts_out.get("error"):
            failures.append("tts_error")
            continue

        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        roundtrip_ms.append(float(elapsed_ms))

    success_count = len(roundtrip_ms)
    success_rate = success_count / float(safe_iterations)
    p50 = _percentile(roundtrip_ms, 50)
    p95 = _percentile(roundtrip_ms, 95)

    ok = (
        not failures
        and success_count == safe_iterations
        and p95 <= float(max_roundtrip_ms)
    )

    result = {
        "ok": ok,
        "iterations": safe_iterations,
        "max_roundtrip_ms": float(max_roundtrip_ms),
        "success_count": success_count,
        "success_rate": round(success_rate, 4),
        "wake_word_triggers": triggers,
        "latency_ms": {
            "p50": round(p50, 3),
            "p95": round(p95, 3),
            "mean": round((sum(roundtrip_ms) / success_count) if success_count else 0.0, 3),
            "median": round(median(roundtrip_ms), 3) if roundtrip_ms else 0.0,
        },
        "providers": {
            "wake_word": getattr(stack.wake_word, "provider", "unknown"),
            "stt": getattr(stack.stt, "provider", "unknown"),
            "tts": getattr(stack.tts, "provider", "unknown"),
        },
        "failures": failures,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if ok else 2


def _webhook_listen(
    source_name: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> int:
    """Run a local webhook HTTP listener and drain events into EventBus."""
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)

    monitor = WebhookMonitor(
        bus,
        source_name=source_name or config.webhook_source_name,
        host=host or config.webhook_host,
        port=config.webhook_port if port is None else port,
        signing_secret=config.webhook_secret,
        path_kind_map=config.webhook_path_kind_map,
    )

    bound_host, bound_port = monitor.start_server()
    print(
        f"Webhook listener running at http://{bound_host}:{bound_port} "
        f"(source={monitor.source}). Press Ctrl+C to stop."
    )

    try:
        while True:
            emitted = monitor.run()
            if emitted:
                print(f"Emitted {emitted} webhook event(s) to EventBus.")
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_server()

    print("Webhook listener stopped.")
    return 0


def _vision_listen(
    source_name: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> int:
    """Run a local HTTP listener for vision/camera frames."""
    config = Config.from_env()
    bus = EventBus(config.event_bus_db)

    monitor = VisionIngestMonitor(
        bus,
        source_name=source_name or config.vision_source_name,
        host=host or config.vision_host,
        port=config.vision_port if port is None else port,
        signing_secret=config.vision_secret,
        max_frame_bytes=config.vision_max_frame_bytes,
    )

    bound_host, bound_port = monitor.start_server()
    print(
        f"Vision listener running at http://{bound_host}:{bound_port} "
        f"(source={monitor.source}). Press Ctrl+C to stop."
    )

    try:
        while True:
            emitted = monitor.run()
            if emitted:
                print(f"Emitted {emitted} vision event(s) to EventBus.")
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_server()

    print("Vision listener stopped.")
    return 0


def _vision_shortcut_template(url: str | None = None) -> int:
    """Print JSON template for an iPhone Shortcut POST request."""
    config = Config.from_env()
    target_url = url or f"http://{config.vision_host}:{config.vision_port}/frame"
    template = build_shortcut_template(target_url, secret=config.vision_secret)
    print(json.dumps(template, sort_keys=True, indent=2))
    return 0


def _vision_shortcut_guide(url: str | None = None) -> int:
    """Print step-by-step guide for iPhone Shortcut vision uploads."""
    config = Config.from_env()
    target_url = url or f"http://{config.vision_host}:{config.vision_port}/frame"
    guide = build_shortcut_guide(target_url, signing_enabled=bool(config.vision_secret))
    print(json.dumps(guide, sort_keys=True, indent=2))
    return 0


def _hud_run(
    *,
    width: int = 720,
    height: int = 180,
    opacity: float = 0.82,
    duration_ms: int | None = None,
) -> int:
    from .hud import PyQtUnavailableError, TransparentHudConfig, run_transparent_hud

    config = TransparentHudConfig(
        width=width,
        height=height,
        opacity=opacity,
    )
    try:
        run_transparent_hud(config, duration_ms=duration_ms)
    except PyQtUnavailableError as exc:
        print(json.dumps({"ok": False, "error": "pyqt_unavailable", "message": str(exc)}, sort_keys=True))
        return 1

    print(json.dumps({"ok": True, "status": "hud_closed"}, sort_keys=True))
    return 0


def _vision_self_test_summary(
    input_file: str,
    mode_filter: str | None = None,
    last: int | None = None,
    percentile_values: list[int] | None = None,
    strict: bool = False,
    max_invalid_lines: int | None = None,
    ema_alpha: float = 0.3,
    max_invalid_line_rate_delta: float | None = None,
    max_invalid_line_rate_ema: float | None = None,
) -> int:
    """Summarize vision self-test JSONL history artifacts."""
    path = Path(input_file).expanduser()
    if not path.exists():
        print(json.dumps({"ok": False, "error": "input_file_not_found", "path": str(path)}, sort_keys=True))
        return 1

    all_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    normalized_mode = (mode_filter or "").strip().lower() or None
    allowed_modes = {"json", "multipart", "binary", "all"}
    if normalized_mode and normalized_mode not in allowed_modes:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_mode_filter",
                    "mode": normalized_mode,
                    "allowed": sorted(allowed_modes),
                },
                sort_keys=True,
            )
        )
        return 1

    if last is not None and last <= 0:
        print(json.dumps({"ok": False, "error": "invalid_last_value", "value": last}, sort_keys=True))
        return 1

    if max_invalid_lines is not None and max_invalid_lines < 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_max_invalid_lines_value",
                    "value": max_invalid_lines,
                },
                sort_keys=True,
            )
        )
        return 1

    if ema_alpha <= 0.0 or ema_alpha > 1.0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_ema_alpha_value",
                    "value": ema_alpha,
                },
                sort_keys=True,
            )
        )
        return 1

    if max_invalid_line_rate_delta is not None and max_invalid_line_rate_delta < 0.0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_max_invalid_line_rate_delta_value",
                    "value": max_invalid_line_rate_delta,
                },
                sort_keys=True,
            )
        )
        return 1

    if max_invalid_line_rate_ema is not None and (max_invalid_line_rate_ema < 0.0 or max_invalid_line_rate_ema > 1.0):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_max_invalid_line_rate_ema_value",
                    "value": max_invalid_line_rate_ema,
                },
                sort_keys=True,
            )
        )
        return 1

    lines = all_lines[-last:] if last is not None else list(all_lines)
    scanned_lines = len(lines)

    def _invalid_line_rate(invalid_count: int, scanned_count: int) -> float:
        if scanned_count <= 0:
            return 0.0
        return round(invalid_count / scanned_count, 4)

    def _line_is_valid_json_dict(line: str) -> bool:
        try:
            value = json.loads(line)
            return isinstance(value, dict)
        except Exception:
            return False

    def _invalid_line_rate_for_window(window_lines: list[str]) -> float:
        if not window_lines:
            return 0.0
        invalid_count = sum(1 for line in window_lines if not _line_is_valid_json_dict(line))
        return _invalid_line_rate(invalid_count, len(window_lines))

    def _invalid_line_rate_ema(window_lines: list[str], alpha: float) -> float:
        if not window_lines:
            return 0.0
        ema = 1.0 if not _line_is_valid_json_dict(window_lines[0]) else 0.0
        for line in window_lines[1:]:
            point = 1.0 if not _line_is_valid_json_dict(line) else 0.0
            ema = alpha * point + (1.0 - alpha) * ema
        return round(ema, 4)

    previous_window_rate: float | None = None
    invalid_line_rate_delta: float | None = None
    if last is not None and scanned_lines > 0:
        prev_end = len(all_lines) - scanned_lines
        if prev_end > 0:
            prev_start = max(0, prev_end - scanned_lines)
            previous_window = all_lines[prev_start:prev_end]
            if previous_window:
                previous_window_rate = _invalid_line_rate_for_window(previous_window)

    active_percentiles = percentile_values or [50, 95]
    invalid = [value for value in active_percentiles if value < 0 or value > 100]
    if invalid:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_percentiles_value",
                    "value": active_percentiles,
                },
                sort_keys=True,
            )
        )
        return 1

    active_percentiles = sorted(set(active_percentiles))

    def _avg(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _percentile(values: list[float], pct: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return round(ordered[0], 2)
        rank = (pct / 100.0) * (len(ordered) - 1)
        low = int(rank)
        high = min(low + 1, len(ordered) - 1)
        fraction = rank - low
        interpolated = ordered[low] + (ordered[high] - ordered[low]) * fraction
        return round(interpolated, 2)

    def _timing_percentiles(values: list[float]) -> dict[str, float | None]:
        output: dict[str, float | None] = {}
        for pct in active_percentiles:
            output[f"p{pct}"] = _percentile(values, float(pct))
        return output

    if not lines:
        print(
            json.dumps(
                {
                    "ok": True,
                    "path": str(path),
                    "mode_filter": normalized_mode,
                    "last": last,
                    "percentiles": active_percentiles,
                    "ema_alpha": ema_alpha,
                    "scanned_lines": 0,
                    "total_runs": 0,
                    "pass_count": 0,
                    "fail_count": 0,
                    "invalid_lines": 0,
                    "invalid_line_rate": 0.0,
                    "invalid_line_rate_ema": 0.0,
                    "invalid_line_rate_previous_window": previous_window_rate,
                    "invalid_line_rate_delta": invalid_line_rate_delta,
                    "mode_counts": {},
                    "timing_averages_ms": {
                        "http_post": None,
                        "drain_monitor_queue": None,
                        "process_automation": None,
                    },
                    "timing_percentiles_ms": {
                        "http_post": _timing_percentiles([]),
                        "drain_monitor_queue": _timing_percentiles([]),
                        "process_automation": _timing_percentiles([]),
                    },
                },
                sort_keys=True,
            )
        )
        return 0

    parsed: list[dict[str, object]] = []
    invalid_lines = 0
    for line in lines:
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                parsed.append(row)
            else:
                invalid_lines += 1
        except Exception:
            invalid_lines += 1

    current_invalid_rate = _invalid_line_rate(invalid_lines, scanned_lines)
    if previous_window_rate is not None:
        invalid_line_rate_delta = round(current_invalid_rate - previous_window_rate, 4)

    current_ema = _invalid_line_rate_ema(lines, ema_alpha)

    if max_invalid_line_rate_delta is not None and invalid_line_rate_delta is not None and invalid_line_rate_delta > max_invalid_line_rate_delta:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_line_rate_delta_exceeded",
                    "path": str(path),
                    "scanned_lines": scanned_lines,
                    "invalid_lines": invalid_lines,
                    "invalid_line_rate": current_invalid_rate,
                    "invalid_line_rate_ema": current_ema,
                    "invalid_line_rate_previous_window": previous_window_rate,
                    "invalid_line_rate_delta": invalid_line_rate_delta,
                    "max_invalid_line_rate_delta": max_invalid_line_rate_delta,
                    "ema_alpha": ema_alpha,
                },
                sort_keys=True,
            )
        )
        return 2

    if max_invalid_line_rate_ema is not None and current_ema > max_invalid_line_rate_ema:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_line_rate_ema_exceeded",
                    "path": str(path),
                    "scanned_lines": scanned_lines,
                    "invalid_lines": invalid_lines,
                    "invalid_line_rate": current_invalid_rate,
                    "invalid_line_rate_ema": current_ema,
                    "invalid_line_rate_previous_window": previous_window_rate,
                    "invalid_line_rate_delta": invalid_line_rate_delta,
                    "max_invalid_line_rate_ema": max_invalid_line_rate_ema,
                    "ema_alpha": ema_alpha,
                },
                sort_keys=True,
            )
        )
        return 2

    effective_max_invalid = 0 if strict else max_invalid_lines
    if effective_max_invalid is not None and invalid_lines > effective_max_invalid:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_history_lines",
                    "path": str(path),
                    "scanned_lines": scanned_lines,
                    "invalid_lines": invalid_lines,
                    "invalid_line_rate": current_invalid_rate,
                    "invalid_line_rate_ema": current_ema,
                    "invalid_line_rate_previous_window": previous_window_rate,
                    "invalid_line_rate_delta": invalid_line_rate_delta,
                    "ema_alpha": ema_alpha,
                    "strict": strict,
                    "max_invalid_lines": effective_max_invalid,
                },
                sort_keys=True,
            )
        )
        return 2

    mode_counts: dict[str, int] = {}
    pass_count = 0
    fail_count = 0
    timings_http_post: list[float] = []
    timings_drain: list[float] = []
    timings_process: list[float] = []

    def _collect_timings(report_obj: object) -> None:
        if not isinstance(report_obj, dict):
            return
        timings = report_obj.get("timings_ms")
        if not isinstance(timings, dict):
            return
        for key, bucket in [
            ("http_post", timings_http_post),
            ("drain_monitor_queue", timings_drain),
            ("process_automation", timings_process),
        ]:
            value = timings.get(key)
            if isinstance(value, (int, float)):
                bucket.append(float(value))

    for row in parsed:
        mode = str(row.get("mode") or "unknown")
        if normalized_mode and mode != normalized_mode:
            continue

        is_ok = row.get("ok") is True
        if is_ok:
            pass_count += 1
        else:
            fail_count += 1

        mode_counts[mode] = mode_counts.get(mode, 0) + 1

        if mode == "all":
            results = row.get("results")
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        _collect_timings(item.get("report"))
        _collect_timings(row.get("report"))

    summary = {
        "ok": True,
        "path": str(path),
        "mode_filter": normalized_mode,
        "last": last,
        "percentiles": active_percentiles,
        "ema_alpha": ema_alpha,
        "scanned_lines": scanned_lines,
        "total_runs": pass_count + fail_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "invalid_lines": invalid_lines,
        "invalid_line_rate": current_invalid_rate,
        "invalid_line_rate_ema": current_ema,
        "invalid_line_rate_previous_window": previous_window_rate,
        "invalid_line_rate_delta": invalid_line_rate_delta,
        "mode_counts": mode_counts,
        "timing_averages_ms": {
            "http_post": _avg(timings_http_post),
            "drain_monitor_queue": _avg(timings_drain),
            "process_automation": _avg(timings_process),
        },
        "timing_percentiles_ms": {
            "http_post": _timing_percentiles(timings_http_post),
            "drain_monitor_queue": _timing_percentiles(timings_drain),
            "process_automation": _timing_percentiles(timings_process),
        },
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


def _vision_self_test(
    mode: str = "json",
    with_secret: bool = False,
    report: bool = False,
    fail_fast: bool = False,
    max_modes: int | None = None,
    selected_modes: list[str] | None = None,
    output_file: str | None = None,
    output_format: str = "json",
) -> int:
    """Run a local end-to-end self-test for the vision ingestion pipeline."""
    config = Config.from_env()
    active_secret = config.vision_secret
    if with_secret and not active_secret:
        active_secret = secrets.token_hex(16)

    selected_mode = (mode or "json").strip().lower()
    normalized_output_format = (output_format or "json").strip().lower()
    allowed_modes = {"json", "multipart", "binary", "all"}
    allowed_individual = ["json", "multipart", "binary"]
    allowed_output_formats = {"json", "jsonl"}

    if selected_mode not in allowed_modes:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_mode",
                    "mode": selected_mode,
                    "allowed": sorted(allowed_modes),
                },
                sort_keys=True,
            )
        )
        return 1

    if normalized_output_format not in allowed_output_formats:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "invalid_output_format",
                    "value": normalized_output_format,
                    "allowed": sorted(allowed_output_formats),
                },
                sort_keys=True,
            )
        )
        return 1

    def _run_single(single_mode: str) -> tuple[int, dict[str, object]]:
        local_bus = EventBus(config.event_bus_db)
        local_monitor = VisionIngestMonitor(
            local_bus,
            source_name=config.vision_source_name,
            host=config.vision_host,
            port=0,
            signing_secret=active_secret,
            max_frame_bytes=config.vision_max_frame_bytes,
        )
        local_automation = EventAutomation(config)

        try:
            host, port = local_monitor.start_server()
            url = f"http://{host}:{port}/frame"

            frame_id = f"self-test-{single_mode}-{int(time.time() * 1000)}"
            payload = {
                "device": "vision_self_test",
                "stream": "camera",
                "frame_id": frame_id,
                "labels": ["self_test", "jarvis"],
                "text": "vision pipeline self-test",
                "image_base64": "aGVsbG8=",
            }

            headers: dict[str, str]
            body: bytes
            if single_mode == "json":
                body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                headers = {
                    "Content-Type": "application/json",
                    "X-Event-Type": "vision.frame",
                }
            elif single_mode == "multipart":
                boundary = "----JarvisVisionSelfTestBoundary"
                image_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
                body = (
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"device\"\r\n\r\n"
                    "vision_self_test\r\n"
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"stream\"\r\n\r\n"
                    "camera\r\n"
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"frame_id\"\r\n\r\n"
                    f"{frame_id}\r\n"
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"labels\"\r\n\r\n"
                    "self_test,jarvis\r\n"
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"text\"\r\n\r\n"
                    "vision pipeline self-test\r\n"
                    f"--{boundary}\r\n"
                    "Content-Disposition: form-data; name=\"image\"; filename=\"frame.jpg\"\r\n"
                    "Content-Type: image/jpeg\r\n\r\n"
                ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
                headers = {
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "X-Event-Type": "vision.frame",
                }
            else:
                body = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                headers = {
                    "Content-Type": "image/png",
                    "X-Device": "vision_self_test",
                    "X-Frame-Id": frame_id,
                    "X-Labels": "self_test,jarvis",
                    "X-Text": "vision pipeline self-test",
                }

            if active_secret:
                digest = hmac.new(
                    active_secret.encode("utf-8"),
                    body,
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Jarvis-Signature"] = f"sha256={digest}"

            request = urllib.request.Request(
                url=url,
                data=body,
                method="POST",
                headers=headers,
            )
            t_post_start = time.perf_counter()
            with urllib.request.urlopen(request, timeout=10) as response:
                accepted = response.status == 202
            t_post_ms = round((time.perf_counter() - t_post_start) * 1000, 2)

            t_drain_start = time.perf_counter()
            emitted = local_monitor.run()
            t_drain_ms = round((time.perf_counter() - t_drain_start) * 1000, 2)

            t_process_start = time.perf_counter()
            summary = local_automation.process_unprocessed(limit=20)
            t_process_ms = round((time.perf_counter() - t_process_start) * 1000, 2)

            result: dict[str, object] = {
                "ok": accepted and emitted >= 1 and summary.processed >= 1,
                "mode": single_mode,
                "signing_enabled": bool(active_secret),
                "ephemeral_secret_used": bool(with_secret and not config.vision_secret),
                "listener_url": url,
                "http_accepted": accepted,
                "emitted": emitted,
                "processed": summary.processed,
                "approvals_created": summary.approvals_created,
                "failures": summary.failures,
            }

            if report:
                result["report"] = {
                    "frame_id": frame_id,
                    "timings_ms": {
                        "http_post": t_post_ms,
                        "drain_monitor_queue": t_drain_ms,
                        "process_automation": t_process_ms,
                    },
                    "items": summary.items,
                }

            status = 0 if accepted and emitted >= 1 and summary.failures == 0 else 2
            return status, result
        except Exception as exc:
            return 2, {"ok": False, "mode": single_mode, "error": str(exc)}
        finally:
            local_monitor.stop_server()

    if selected_mode == "all":
        available_modes = allowed_individual
        if selected_modes is not None:
            available_modes = selected_modes
        modes_to_run = available_modes if max_modes is None else available_modes[:max_modes]
        results: list[dict[str, object]] = []
        statuses: list[int] = []
        for single_mode in modes_to_run:
            status, result = _run_single(single_mode)
            statuses.append(status)
            results.append(result)
            if fail_fast and status != 0:
                break

        aggregate: dict[str, object] = {
            "ok": all(item.get("ok") is True for item in results),
            "mode": "all",
            "signing_enabled": bool(active_secret),
            "ephemeral_secret_used": bool(with_secret and not config.vision_secret),
            "fail_fast": fail_fast,
            "max_modes_requested": max_modes,
            "modes_requested": selected_modes,
            "results": results,
        }
        if report:
            total_processed = sum(int(item.get("processed", 0)) for item in results)
            total_approvals = sum(int(item.get("approvals_created", 0)) for item in results)
            aggregate["report"] = {
                "total_processed": total_processed,
                "total_approvals_created": total_approvals,
                "modes_run": [item.get("mode") for item in results],
            }

        if output_file:
            path = Path(output_file).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            if normalized_output_format == "jsonl":
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(aggregate, sort_keys=True) + "\n")
            else:
                path.write_text(json.dumps(aggregate, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            aggregate["output_file"] = str(path)
            aggregate["output_format"] = normalized_output_format

        print(json.dumps(aggregate, sort_keys=True))
        return 0 if all(status == 0 for status in statuses) else 2

    status, result = _run_single(selected_mode)
    if output_file:
        path = Path(output_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        if normalized_output_format == "jsonl":
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(result, sort_keys=True) + "\n")
        else:
            path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        result["output_file"] = str(path)
        result["output_format"] = normalized_output_format
    print(json.dumps(result, sort_keys=True))
    return status


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        repl()
        return 0

    if args[0] == "audit-verify":
        return _audit_verify()

    if args[0] == "audit-export":
        return _audit_export()

    if args[0] == "audit-stats":
        return _audit_stats()

    if args[0] == "trade-replay-report":
        limit = 50
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            if token == "--limit":
                if idx + 1 >= len(tail):
                    print(json.dumps({"ok": False, "error": "missing_limit_value"}, sort_keys=True))
                    return 1
                value = tail[idx + 1]
                try:
                    limit = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_limit_value", "value": value}, sort_keys=True))
                    return 1
                idx += 2
                continue
            if token.startswith("--limit="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_limit_value"}, sort_keys=True))
                    return 1
                try:
                    limit = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_limit_value", "value": value}, sort_keys=True))
                    return 1
                idx += 1
                continue
            try:
                limit = int(token)
            except ValueError:
                print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
                return 1
            idx += 1

        return _trade_replay_report(limit=limit)

    if args[0] == "trade-performance-report":
        mode = "paper"
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            if token == "--mode":
                if idx + 1 >= len(tail):
                    print(json.dumps({"ok": False, "error": "missing_mode_value"}, sort_keys=True))
                    return 1
                mode = tail[idx + 1].strip().lower()
                idx += 2
                continue
            if token.startswith("--mode="):
                mode = token.split("=", 1)[1].strip().lower()
                if not mode:
                    print(json.dumps({"ok": False, "error": "missing_mode_value"}, sort_keys=True))
                    return 1
                idx += 1
                continue
            if token.startswith("--"):
                print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
                return 1
            if mode != "paper" and mode != token.strip().lower():
                print(
                    json.dumps(
                        {"ok": False, "error": "conflicting_mode_filters", "mode": mode, "new_mode": token},
                        sort_keys=True,
                    )
                )
                return 1
            mode = token.strip().lower()
            idx += 1

        if mode not in {"dry_run", "paper", "live"}:
            print(json.dumps({"ok": False, "error": "invalid_mode_value", "value": mode}, sort_keys=True))
            return 1

        return _trade_performance_report(mode=mode)

    if args[0] == "trade-streaks":
        mode = "paper"
        limit = 100
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--mode", "missing_mode_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                mode = (parsed_value or "").strip().lower()
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--limit", "missing_limit_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                parsed_limit, error_payload = _parse_int_arg(parsed_value or "", "invalid_limit_value", min_value=1, max_value=1000)
                if error_payload is not None:
                    print(json.dumps(error_payload, sort_keys=True))
                    return 1
                limit = parsed_limit or 100
                idx = next_idx
                continue

            if token.startswith("--"):
                print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
                return 1
            if mode != "paper" and mode != token.strip().lower():
                print(json.dumps({"ok": False, "error": "conflicting_mode_filters", "mode": mode, "new_mode": token}, sort_keys=True))
                return 1
            mode = token.strip().lower()
            idx += 1

        if mode not in {"dry_run", "paper", "live"}:
            print(json.dumps({"ok": False, "error": "invalid_mode_value", "value": mode}, sort_keys=True))
            return 1
        return _trade_streaks(mode=mode, limit=limit)

    if args[0] == "trade-portfolio-metrics":
        mode = "paper"
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--mode", "missing_mode_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                mode = (parsed_value or "").strip().lower()
                idx = next_idx
                continue
            if token.startswith("--"):
                print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
                return 1
            if mode != "paper" and mode != token.strip().lower():
                print(json.dumps({"ok": False, "error": "conflicting_mode_filters", "mode": mode, "new_mode": token}, sort_keys=True))
                return 1
            mode = token.strip().lower()
            idx += 1

        if mode not in {"dry_run", "paper", "live"}:
            print(json.dumps({"ok": False, "error": "invalid_mode_value", "value": mode}, sort_keys=True))
            return 1
        return _trade_portfolio_metrics(mode=mode)

    if args[0] == "trade-review-artifact":
        reviewer = ""
        strategy_version = ""
        output_file: str | None = None
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--reviewer", "missing_reviewer_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                reviewer = parsed_value or ""
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--strategy-version", "missing_strategy_version_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                strategy_version = parsed_value or ""
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--output", "missing_output_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                output_file = parsed_value
                idx = next_idx
                continue

            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1

        return _trade_review_artifact(
            output_file=output_file,
            reviewer=reviewer,
            strategy_version=strategy_version,
        )

    if args[0] == "trade-market-hours":
        if len(args) < 2:
            print(json.dumps({"ok": False, "error": "missing_instrument_value"}, sort_keys=True))
            return 1
        instrument = args[1]
        market = "US"
        tail = args[2:] if len(args) >= 3 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--market", "missing_market_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                market = parsed_value or "US"
                idx = next_idx
                continue
            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1
        return _trade_market_hours(instrument, market=market)

    if args[0] == "trade-risk-estimate":
        tail = args[1:] if len(args) >= 2 else []
        values: dict[str, float | None] = {
            "position_size": None,
            "entry_price": None,
            "stop_loss_price": None,
            "take_profit_price": None,
            "confidence_level": 0.95,
        }
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            matched = False
            for flag, key, missing_error in (
                ("--position-size", "position_size", "missing_position_size_value"),
                ("--entry-price", "entry_price", "missing_entry_price_value"),
                ("--stop-loss-price", "stop_loss_price", "missing_stop_loss_price_value"),
                ("--take-profit-price", "take_profit_price", "missing_take_profit_price_value"),
                ("--confidence-level", "confidence_level", "missing_confidence_level_value"),
            ):
                parsed_value, next_idx, err = _consume_flag_value(tail, idx, flag, missing_error)
                if err:
                    print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                    return 1
                if next_idx != idx:
                    try:
                        values[key] = float(parsed_value or "")
                    except ValueError:
                        print(json.dumps({"ok": False, "error": f"invalid_{key}_value", "value": parsed_value}, sort_keys=True))
                        return 1
                    idx = next_idx
                    matched = True
                    break
            if matched:
                continue
            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1

        for required_key in ("position_size", "entry_price", "stop_loss_price"):
            if values[required_key] is None:
                print(json.dumps({"ok": False, "error": f"missing_{required_key}_value"}, sort_keys=True))
                return 1

        return _trade_risk_estimate(
            position_size=float(values["position_size"]),
            entry_price=float(values["entry_price"]),
            stop_loss_price=float(values["stop_loss_price"]),
            take_profit_price=float(values["take_profit_price"]) if values["take_profit_price"] is not None else None,
            confidence_level=float(values["confidence_level"]),
        )

    if args[0] == "trade-journal":
        if len(args) < 2:
            print(json.dumps({"ok": False, "error": "missing_trade_id_value"}, sort_keys=True))
            return 1
        trade_id = args[1]
        setup = ""
        lessons = ""
        improvement = ""
        tail = args[2:] if len(args) >= 3 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--setup", "missing_setup_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                setup = parsed_value or ""
                idx = next_idx
                continue
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--lessons", "missing_lessons_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                lessons = parsed_value or ""
                idx = next_idx
                continue
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--improvement", "missing_improvement_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                improvement = parsed_value or ""
                idx = next_idx
                continue
            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1
        return _trade_journal(trade_id, setup=setup, lessons=lessons, improvement=improvement)

    if args[0] == "stop":
        return _stop()

    if args[0] == "resume":
        return _resume()

    if args[0] == "audit-correlation" and len(args) >= 2:
        correlation_id = args[1]
        positional_limit: int | None = None
        flag_limit: int | None = None
        flag_kind: str | None = None
        kind: str | None = None

        tail = args[2:] if len(args) >= 3 else []
        idx = 0
        while idx < len(tail):
            tok = tail[idx]
            if tok == "--limit":
                if idx + 1 >= len(tail):
                    print(
                        json.dumps(
                            {"ok": False, "error": "missing_limit_value"},
                            sort_keys=True,
                        )
                    )
                    return 1
                raw_limit = tail[idx + 1]
                parsed_limit, err = _parse_int_arg(
                    raw_limit,
                    "invalid_limit_value",
                )
                if err is not None:
                    print(
                        json.dumps(
                            err,
                            sort_keys=True,
                        )
                    )
                    return 1
                if flag_limit is not None and flag_limit != parsed_limit:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "conflicting_limit_filters",
                                "flag_limit": flag_limit,
                                "new_flag_limit": parsed_limit,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                flag_limit = parsed_limit
                idx += 2
                continue
            if tok.startswith("--limit="):
                raw_limit = tok.split("=", 1)[1]
                parsed_limit, err = _parse_int_arg(
                    raw_limit,
                    "invalid_limit_value",
                )
                if err is not None:
                    print(
                        json.dumps(
                            err,
                            sort_keys=True,
                        )
                    )
                    return 1
                if flag_limit is not None and flag_limit != parsed_limit:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "conflicting_limit_filters",
                                "flag_limit": flag_limit,
                                "new_flag_limit": parsed_limit,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                flag_limit = parsed_limit
                idx += 1
                continue

            parsed_kind, next_idx, kind_err = _consume_flag_value(
                tail,
                idx,
                "--kind",
                "missing_kind_value",
            )
            if kind_err:
                print(
                    json.dumps(
                        {"ok": False, "error": kind_err},
                        sort_keys=True,
                    )
                )
                return 1
            if next_idx != idx:
                if flag_kind is not None and flag_kind != parsed_kind:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "conflicting_kind_filters",
                                "flag_kind": flag_kind,
                                "new_flag_kind": parsed_kind,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                flag_kind = parsed_kind
                kind = parsed_kind
                idx = next_idx
                continue
            if tok.startswith("--"):
                print(
                    json.dumps(
                        {"ok": False, "error": "unknown_argument", "argument": tok},
                        sort_keys=True,
                    )
                )
                return 1
            if positional_limit is None:
                parsed_positional_limit, err = _parse_int_arg(
                    tok,
                    "invalid_limit_value",
                )
                if err is not None:
                    print(
                        json.dumps(
                            err,
                            sort_keys=True,
                        )
                    )
                    return 1
                positional_limit = parsed_positional_limit
                idx += 1
                continue

            print(
                json.dumps(
                    {"ok": False, "error": "unknown_argument", "argument": tok},
                    sort_keys=True,
                )
            )
            return 1

        if (
            positional_limit is not None
            and flag_limit is not None
            and positional_limit != flag_limit
        ):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "conflicting_limit_filters",
                        "positional_limit": positional_limit,
                        "flag_limit": flag_limit,
                    },
                    sort_keys=True,
                )
            )
            return 1

        limit = flag_limit if flag_limit is not None else positional_limit
        effective_limit = 100 if limit is None else limit

        return _audit_correlation(correlation_id, limit=effective_limit, kind=kind)

    if args[0] == "approvals-list":
        return _approvals_list()

    if args[0] == "approvals-approve" and len(args) >= 2:
        return _approvals_approve(args[1], " ".join(args[2:]).strip())

    if args[0] == "approvals-reject" and len(args) >= 2:
        return _approvals_reject(args[1], " ".join(args[2:]).strip())

    if args[0] == "approvals-dispatch":
        return _approvals_dispatch()

    if args[0] == "approvals-api":
        host = args[1] if len(args) >= 2 else None
        port = int(args[2]) if len(args) >= 3 else None
        return _approvals_api(host=host, port=port)

    if args[0] == "approvals-seed":
        count = int(args[1]) if len(args) >= 2 else 3
        return _approvals_seed(count=count)

    if args[0] == "events-stats":
        return _events_stats()

    if args[0] == "monitors-status":
        return _monitors_status()

    if args[0] == "events-list":
        if len(args) >= 2:
            limit, err = _parse_int_arg(
                args[1],
                "invalid_limit_value",
                min_value=1,
            )
            if err is not None:
                print(json.dumps(err, sort_keys=True))
                return 1
        else:
            limit = 20
        unprocessed_only = len(args) >= 3 and args[2] == "--unprocessed"
        return _events_list(limit=limit, unprocessed_only=unprocessed_only)

    if args[0] == "events-process":
        if len(args) >= 2:
            limit, err = _parse_int_arg(
                args[1],
                "invalid_limit_value",
                min_value=1,
            )
            if err is not None:
                print(json.dumps(err, sort_keys=True))
                return 1
        else:
            limit = 50
        return _events_process(limit=limit)

    if args[0] == "events-actions":
        if len(args) >= 2:
            limit, err = _parse_int_arg(
                args[1],
                "invalid_limit_value",
                min_value=1,
            )
            if err is not None:
                print(json.dumps(err, sort_keys=True))
                return 1
        else:
            limit = 50
        positional_event_kind: str | None = None
        kind_flag: str | None = None
        correlation_id: str | None = None

        tail = args[2:] if len(args) >= 3 else []
        idx = 0
        while idx < len(tail):
            tok = tail[idx]

            parsed_kind, next_idx, kind_err = _consume_flag_value(
                tail,
                idx,
                "--kind",
                "missing_kind_value",
            )
            if kind_err:
                print(
                    json.dumps(
                        {"ok": False, "error": kind_err},
                        sort_keys=True,
                    )
                )
                return 1
            if next_idx != idx:
                if kind_flag is not None and kind_flag != parsed_kind:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "conflicting_kind_filters",
                                "flag_kind": kind_flag,
                                "new_flag_kind": parsed_kind,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                kind_flag = parsed_kind
                idx = next_idx
                continue

            parsed_correlation_id, next_idx, corr_err = _consume_flag_value(
                tail,
                idx,
                "--correlation-id",
                "missing_correlation_id_value",
            )
            if corr_err:
                print(
                    json.dumps(
                        {"ok": False, "error": corr_err},
                        sort_keys=True,
                    )
                )
                return 1
            if next_idx != idx:
                if correlation_id is not None and correlation_id != parsed_correlation_id:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "conflicting_correlation_id_filters",
                                "correlation_id": correlation_id,
                                "new_correlation_id": parsed_correlation_id,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                correlation_id = parsed_correlation_id
                idx = next_idx
                continue
            if tok.startswith("--"):
                print(
                    json.dumps(
                        {"ok": False, "error": "unknown_argument", "argument": tok},
                        sort_keys=True,
                    )
                )
                return 1
            if positional_event_kind is None:
                positional_event_kind = tok
                idx += 1
                continue

            print(
                json.dumps(
                    {"ok": False, "error": "unknown_argument", "argument": tok},
                    sort_keys=True,
                )
            )
            return 1

        if kind_flag and positional_event_kind and kind_flag != positional_event_kind:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "conflicting_kind_filters",
                        "positional_kind": positional_event_kind,
                        "flag_kind": kind_flag,
                    },
                    sort_keys=True,
                )
            )
            return 1

        event_kind = kind_flag or positional_event_kind

        return _events_actions(
            limit=limit,
            event_kind=event_kind,
            correlation_id=correlation_id,
        )

    if args[0] == "events-prune-actions":
        days = int(args[1]) if len(args) >= 2 else None
        return _events_prune_actions(days=days)

    if args[0] == "location-update":
        if len(args) < 3:
            print(
                json.dumps(
                    {"ok": False, "error": "missing_latitude_longitude"},
                    sort_keys=True,
                )
            )
            return 1
        try:
            latitude = float(args[1])
            longitude = float(args[2])
        except ValueError:
            print(
                json.dumps(
                    {"ok": False, "error": "invalid_latitude_longitude"},
                    sort_keys=True,
                )
            )
            return 1

        source = "manual"
        accuracy_m: float | None = None
        tail = args[3:]
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_source, next_idx, src_err = _consume_flag_value(
                tail,
                idx,
                "--source",
                "missing_source_value",
            )
            if src_err:
                print(json.dumps({"ok": False, "error": src_err}, sort_keys=True))
                return 1
            if next_idx != idx:
                source = parsed_source or "manual"
                idx = next_idx
                continue

            parsed_accuracy, next_idx, acc_err = _consume_flag_value(
                tail,
                idx,
                "--accuracy-m",
                "missing_accuracy_m_value",
            )
            if acc_err:
                print(json.dumps({"ok": False, "error": acc_err}, sort_keys=True))
                return 1
            if next_idx != idx:
                try:
                    accuracy_m = float(parsed_accuracy or "")
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_accuracy_m_value",
                                "value": parsed_accuracy,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx = next_idx
                continue

            print(
                json.dumps(
                    {"ok": False, "error": "unknown_argument", "arg": token},
                    sort_keys=True,
                )
            )
            return 1

        if not (-90.0 <= latitude <= 90.0):
            print(json.dumps({"ok": False, "error": "invalid_latitude_range"}, sort_keys=True))
            return 1
        if not (-180.0 <= longitude <= 180.0):
            print(json.dumps({"ok": False, "error": "invalid_longitude_range"}, sort_keys=True))
            return 1
        if accuracy_m is not None and accuracy_m < 0:
            print(json.dumps({"ok": False, "error": "invalid_accuracy_m_value", "value": str(accuracy_m)}, sort_keys=True))
            return 1

        return _location_update(
            latitude=latitude,
            longitude=longitude,
            source=source,
            accuracy_m=accuracy_m,
        )

    if args[0] == "location-last":
        return _location_last()

    if args[0] == "monitor-run-once":
        return _monitor_run_once()

    if args[0] == "webhook-listen":
        source_name = args[1] if len(args) >= 2 else None
        host = args[2] if len(args) >= 3 else None
        port = int(args[3]) if len(args) >= 4 else None
        return _webhook_listen(source_name=source_name, host=host, port=port)

    if args[0] == "vision-listen":
        source_name = args[1] if len(args) >= 2 else None
        host = args[2] if len(args) >= 3 else None
        port = int(args[3]) if len(args) >= 4 else None
        return _vision_listen(source_name=source_name, host=host, port=port)

    if args[0] == "vision-shortcut-template":
        url = args[1] if len(args) >= 2 else None
        return _vision_shortcut_template(url=url)

    if args[0] == "vision-shortcut-guide":
        url = args[1] if len(args) >= 2 else None
        return _vision_shortcut_guide(url=url)

    if args[0] == "voice-self-test":
        iterations = 10
        max_roundtrip_ms = 100.0
        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            if token == "--iterations":
                if idx + 1 >= len(tail):
                    print(json.dumps({"ok": False, "error": "missing_iterations_value"}, sort_keys=True))
                    return 1
                value = tail[idx + 1]
                try:
                    iterations = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_iterations_value", "value": value}, sort_keys=True))
                    return 1
                idx += 2
                continue
            if token.startswith("--iterations="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_iterations_value"}, sort_keys=True))
                    return 1
                try:
                    iterations = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_iterations_value", "value": value}, sort_keys=True))
                    return 1
                idx += 1
                continue
            if token == "--max-roundtrip-ms":
                if idx + 1 >= len(tail):
                    print(json.dumps({"ok": False, "error": "missing_max_roundtrip_ms_value"}, sort_keys=True))
                    return 1
                value = tail[idx + 1]
                try:
                    max_roundtrip_ms = float(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_roundtrip_ms_value", "value": value}, sort_keys=True))
                    return 1
                idx += 2
                continue
            if token.startswith("--max-roundtrip-ms="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_roundtrip_ms_value"}, sort_keys=True))
                    return 1
                try:
                    max_roundtrip_ms = float(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_roundtrip_ms_value", "value": value}, sort_keys=True))
                    return 1
                idx += 1
                continue
            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1

        if iterations <= 0:
            print(json.dumps({"ok": False, "error": "invalid_iterations_value", "value": str(iterations)}, sort_keys=True))
            return 1
        if max_roundtrip_ms <= 0:
            print(json.dumps({"ok": False, "error": "invalid_max_roundtrip_ms_value", "value": str(max_roundtrip_ms)}, sort_keys=True))
            return 1

        return _voice_self_test(
            iterations=iterations,
            max_roundtrip_ms=max_roundtrip_ms,
        )

    if args[0] == "hud-run":
        width = 720
        height = 180
        opacity = 0.82
        duration_ms: int | None = None

        tail = args[1:] if len(args) >= 2 else []
        idx = 0
        while idx < len(tail):
            token = tail[idx]
            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--width", "missing_width_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                parsed_width, error_payload = _parse_int_arg(parsed_value or "", "invalid_width_value", min_value=200)
                if error_payload is not None:
                    print(json.dumps(error_payload, sort_keys=True))
                    return 1
                width = parsed_width or width
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--height", "missing_height_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                parsed_height, error_payload = _parse_int_arg(parsed_value or "", "invalid_height_value", min_value=80)
                if error_payload is not None:
                    print(json.dumps(error_payload, sort_keys=True))
                    return 1
                height = parsed_height or height
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--duration-ms", "missing_duration_ms_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                parsed_duration, error_payload = _parse_int_arg(parsed_value or "", "invalid_duration_ms_value", min_value=1)
                if error_payload is not None:
                    print(json.dumps(error_payload, sort_keys=True))
                    return 1
                duration_ms = parsed_duration
                idx = next_idx
                continue

            parsed_value, next_idx, err = _consume_flag_value(tail, idx, "--opacity", "missing_opacity_value")
            if err:
                print(json.dumps({"ok": False, "error": err}, sort_keys=True))
                return 1
            if next_idx != idx:
                try:
                    opacity = float(parsed_value or "")
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_opacity_value", "value": parsed_value}, sort_keys=True))
                    return 1
                idx = next_idx
                continue

            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1

        if opacity <= 0.0 or opacity > 1.0:
            print(json.dumps({"ok": False, "error": "invalid_opacity_value", "value": str(opacity)}, sort_keys=True))
            return 1

        return _hud_run(
            width=width,
            height=height,
            opacity=opacity,
            duration_ms=duration_ms,
        )

    if args[0] == "vision-analyze":
        if len(args) < 2:
            print(json.dumps({"ok": False, "error": "missing_image_arg"}, sort_keys=True))
            return 1
        source = args[1]
        no_faces = "--no-faces" in args
        no_colors = "--no-colors" in args
        no_landmarks = "--no-landmarks" in args
        max_colors = 5
        _idx = 2
        while _idx < len(args):
            tok = args[_idx]
            if tok.startswith("--max-colors="):
                value = tok.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_colors_value"}, sort_keys=True))
                    return 1
                try:
                    max_colors = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_colors_value", "value": value}, sort_keys=True))
                    return 1
                _idx += 1
                continue
            if tok == "--max-colors":
                if _idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_max_colors_value"}, sort_keys=True))
                    return 1
                try:
                    max_colors = int(args[_idx + 1])
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_colors_value", "value": args[_idx + 1]}, sort_keys=True))
                    return 1
                _idx += 2
                continue
            _idx += 1

        import base64 as _b64
        if source == "-":
            raw = sys.stdin.buffer.read()
            image_b64 = _b64.b64encode(raw).decode("ascii")
        elif len(source) > 260 or source.endswith(("==", "=")):
            image_b64 = source
        else:
            from pathlib import Path as _Path
            _p = _Path(source).expanduser()
            if not _p.exists():
                print(json.dumps({"ok": False, "error": "image_file_not_found", "path": str(_p)}, sort_keys=True))
                return 1
            image_b64 = _b64.b64encode(_p.read_bytes()).decode("ascii")

        _result = analyze_frame_b64(
            image_b64,
            detect_faces_flag=not no_faces,
            detect_colors_flag=not no_colors,
            detect_landmarks_flag=not no_landmarks,
            max_colors=max_colors,
        )
        print(json.dumps(_result, sort_keys=True))
        return 0 if _result.get("ok") else 1

    if args[0] == "vision-self-test-summary":
        if len(args) < 2:
            print(json.dumps({"ok": False, "error": "missing_input_file"}, sort_keys=True))
            return 1

        input_file = args[1]
        mode_filter: str | None = None
        last: int | None = None
        percentile_values: list[int] | None = None

        # --- env-var defaults (CLI flags take precedence) ---
        _env_strict = os.environ.get("JARVIS_SUMMARY_STRICT", "").strip().lower()
        strict = _env_strict in ("1", "true", "yes")

        _env_mil = os.environ.get("JARVIS_MAX_INVALID_LINES", "").strip()
        if _env_mil:
            try:
                max_invalid_lines: int | None = int(_env_mil)
            except ValueError:
                print(json.dumps({"ok": False, "error": "invalid_max_invalid_lines_value", "value": _env_mil, "source": "env"}, sort_keys=True))
                return 1
        else:
            max_invalid_lines = None

        _env_ea = os.environ.get("JARVIS_EMA_ALPHA", "").strip()
        if _env_ea:
            try:
                ema_alpha = float(_env_ea)
            except ValueError:
                print(json.dumps({"ok": False, "error": "invalid_ema_alpha_value", "value": _env_ea, "source": "env"}, sort_keys=True))
                return 1
        else:
            ema_alpha = 0.3

        _env_delta = os.environ.get("JARVIS_MAX_INVALID_LINE_RATE_DELTA", "").strip()
        if _env_delta:
            try:
                max_invalid_line_rate_delta: float | None = float(_env_delta)
            except ValueError:
                print(json.dumps({"ok": False, "error": "invalid_max_invalid_line_rate_delta_value", "value": _env_delta, "source": "env"}, sort_keys=True))
                return 1
        else:
            max_invalid_line_rate_delta = None

        _env_ema_gate = os.environ.get("JARVIS_MAX_INVALID_LINE_RATE_EMA", "").strip()
        if _env_ema_gate:
            try:
                max_invalid_line_rate_ema: float | None = float(_env_ema_gate)
            except ValueError:
                print(json.dumps({"ok": False, "error": "invalid_max_invalid_line_rate_ema_value", "value": _env_ema_gate, "source": "env"}, sort_keys=True))
                return 1
        else:
            max_invalid_line_rate_ema = None
        # --- end env-var defaults ---

        idx = 2
        while idx < len(args):
            token = args[idx]
            if token == "--mode":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_mode_filter_value"}, sort_keys=True))
                    return 1
                mode_filter = args[idx + 1]
                idx += 2
                continue

            if token.startswith("--mode="):
                mode_filter = token.split("=", 1)[1]
                if not mode_filter:
                    print(json.dumps({"ok": False, "error": "missing_mode_filter_value"}, sort_keys=True))
                    return 1
                idx += 1
                continue

            if token == "--last":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_last_value"}, sort_keys=True))
                    return 1
                try:
                    last = int(args[idx + 1])
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_last_value", "value": args[idx + 1]}, sort_keys=True))
                    return 1
                idx += 2
                continue

            if token.startswith("--last="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_last_value"}, sort_keys=True))
                    return 1
                try:
                    last = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_last_value", "value": value}, sort_keys=True))
                    return 1
                idx += 1
                continue

            if token == "--percentiles":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_percentiles_value"}, sort_keys=True))
                    return 1
                value = args[idx + 1]
                parts = [part.strip() for part in value.split(",") if part.strip()]
                if not parts:
                    print(json.dumps({"ok": False, "error": "invalid_percentiles_value", "value": value}, sort_keys=True))
                    return 1
                try:
                    percentile_values = [int(part) for part in parts]
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_percentiles_value", "value": value}, sort_keys=True))
                    return 1
                idx += 2
                continue

            if token.startswith("--percentiles="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_percentiles_value"}, sort_keys=True))
                    return 1
                parts = [part.strip() for part in value.split(",") if part.strip()]
                if not parts:
                    print(json.dumps({"ok": False, "error": "invalid_percentiles_value", "value": value}, sort_keys=True))
                    return 1
                try:
                    percentile_values = [int(part) for part in parts]
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_percentiles_value", "value": value}, sort_keys=True))
                    return 1
                idx += 1
                continue

            if token == "--strict":
                strict = True
                idx += 1
                continue

            if token == "--max-invalid-lines":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_lines_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_lines = int(args[idx + 1])
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_lines_value",
                                "value": args[idx + 1],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 2
                continue

            if token.startswith("--max-invalid-lines="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_lines_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_lines = int(value)
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_lines_value",
                                "value": value,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 1
                continue

            if token == "--ema-alpha":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_ema_alpha_value"}, sort_keys=True))
                    return 1
                try:
                    ema_alpha = float(args[idx + 1])
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_ema_alpha_value",
                                "value": args[idx + 1],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 2
                continue

            if token.startswith("--ema-alpha="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_ema_alpha_value"}, sort_keys=True))
                    return 1
                try:
                    ema_alpha = float(value)
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_ema_alpha_value",
                                "value": value,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 1
                continue

            if token == "--max-invalid-line-rate-delta":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_line_rate_delta_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_line_rate_delta = float(args[idx + 1])
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_line_rate_delta_value",
                                "value": args[idx + 1],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 2
                continue

            if token.startswith("--max-invalid-line-rate-delta="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_line_rate_delta_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_line_rate_delta = float(value)
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_line_rate_delta_value",
                                "value": value,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 1
                continue

            if token == "--max-invalid-line-rate-ema":
                if idx + 1 >= len(args):
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_line_rate_ema_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_line_rate_ema = float(args[idx + 1])
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_line_rate_ema_value",
                                "value": args[idx + 1],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 2
                continue

            if token.startswith("--max-invalid-line-rate-ema="):
                value = token.split("=", 1)[1]
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_invalid_line_rate_ema_value"}, sort_keys=True))
                    return 1
                try:
                    max_invalid_line_rate_ema = float(value)
                except ValueError:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_max_invalid_line_rate_ema_value",
                                "value": value,
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                idx += 1
                continue

            print(json.dumps({"ok": False, "error": "unknown_argument", "arg": token}, sort_keys=True))
            return 1

        return _vision_self_test_summary(
            input_file=input_file,
            mode_filter=mode_filter,
            last=last,
            percentile_values=percentile_values,
            strict=strict,
            max_invalid_lines=max_invalid_lines,
            ema_alpha=ema_alpha,
            max_invalid_line_rate_delta=max_invalid_line_rate_delta,
            max_invalid_line_rate_ema=max_invalid_line_rate_ema,
        )

    if args[0] == "vision-self-test":
        raw = args[1:]

        max_modes: int | None = None
        modes_requested: list[str] | None = None
        output_file: str | None = None
        output_format = "json"
        normalized: list[str] = []
        idx = 0
        while idx < len(raw):
            token = raw[idx]
            if token == "--max-modes":
                if idx + 1 >= len(raw):
                    print(json.dumps({"ok": False, "error": "missing_max_modes_value"}, sort_keys=True))
                    return 1
                value = raw[idx + 1]
                idx += 2
                try:
                    parsed = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_modes_value", "value": value}, sort_keys=True))
                    return 1
                if parsed <= 0:
                    print(json.dumps({"ok": False, "error": "invalid_max_modes_value", "value": value}, sort_keys=True))
                    return 1
                max_modes = min(parsed, 3)
                continue

            if token.startswith("--max-modes="):
                value = token.split("=", 1)[1]
                idx += 1
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_max_modes_value"}, sort_keys=True))
                    return 1
                try:
                    parsed = int(value)
                except ValueError:
                    print(json.dumps({"ok": False, "error": "invalid_max_modes_value", "value": value}, sort_keys=True))
                    return 1
                if parsed <= 0:
                    print(json.dumps({"ok": False, "error": "invalid_max_modes_value", "value": value}, sort_keys=True))
                    return 1
                max_modes = min(parsed, 3)
                continue

            if token == "--modes":
                if idx + 1 >= len(raw):
                    print(json.dumps({"ok": False, "error": "missing_modes_value"}, sort_keys=True))
                    return 1
                value = raw[idx + 1]
                idx += 2
                parts = [part.strip().lower() for part in value.split(",") if part.strip()]
                if not parts:
                    print(json.dumps({"ok": False, "error": "invalid_modes_value", "value": value}, sort_keys=True))
                    return 1
                invalid = [part for part in parts if part not in {"json", "multipart", "binary"}]
                if invalid:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_modes_value",
                                "value": value,
                                "invalid": invalid,
                                "allowed": ["json", "multipart", "binary"],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                # Deduplicate while preserving order.
                modes_requested = list(dict.fromkeys(parts))
                continue

            if token == "--output-file":
                if idx + 1 >= len(raw):
                    print(json.dumps({"ok": False, "error": "missing_output_file_value"}, sort_keys=True))
                    return 1
                output_file = raw[idx + 1]
                idx += 2
                continue

            if token.startswith("--output-file="):
                output_file = token.split("=", 1)[1]
                idx += 1
                if not output_file:
                    print(json.dumps({"ok": False, "error": "missing_output_file_value"}, sort_keys=True))
                    return 1
                continue

            if token == "--output-format":
                if idx + 1 >= len(raw):
                    print(json.dumps({"ok": False, "error": "missing_output_format_value"}, sort_keys=True))
                    return 1
                output_format = raw[idx + 1]
                idx += 2
                continue

            if token.startswith("--output-format="):
                output_format = token.split("=", 1)[1]
                idx += 1
                if not output_format:
                    print(json.dumps({"ok": False, "error": "missing_output_format_value"}, sort_keys=True))
                    return 1
                continue

            if token.startswith("--modes="):
                value = token.split("=", 1)[1]
                idx += 1
                if not value:
                    print(json.dumps({"ok": False, "error": "missing_modes_value"}, sort_keys=True))
                    return 1
                parts = [part.strip().lower() for part in value.split(",") if part.strip()]
                if not parts:
                    print(json.dumps({"ok": False, "error": "invalid_modes_value", "value": value}, sort_keys=True))
                    return 1
                invalid = [part for part in parts if part not in {"json", "multipart", "binary"}]
                if invalid:
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "error": "invalid_modes_value",
                                "value": value,
                                "invalid": invalid,
                                "allowed": ["json", "multipart", "binary"],
                            },
                            sort_keys=True,
                        )
                    )
                    return 1
                modes_requested = list(dict.fromkeys(parts))
                continue

            normalized.append(token)
            idx += 1

        raw = normalized
        with_secret = "--with-secret" in raw
        report = "--report" in raw
        fail_fast = "--fail-fast" in raw
        positional = [
            item
            for item in raw
            if item not in {"--with-secret", "--report", "--fail-fast"}
        ]
        mode = positional[0] if positional else "json"

        if mode != "all" and modes_requested is not None:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "modes_requires_all_mode",
                        "mode": mode,
                    },
                    sort_keys=True,
                )
            )
            return 1

        return _vision_self_test(
            mode=mode,
            with_secret=with_secret,
            report=report,
            fail_fast=fail_fast,
            max_modes=max_modes,
            selected_modes=modes_requested,
            output_file=output_file,
            output_format=output_format,
        )

    print(
        "Usage: python3 -m jarvis "
        "[audit-verify|audit-export|audit-stats|audit-correlation <correlation_id> [limit|--limit <n>] [--kind <event_kind>]|trade-replay-report [limit|--limit <n>]|trade-performance-report [paper|live|dry_run|--mode <mode>]|trade-streaks [paper|live|dry_run|--mode <mode>] [--limit <n>]|trade-portfolio-metrics [paper|live|dry_run|--mode <mode>]|trade-market-hours <instrument> [--market <US|CRYPTO>]|trade-risk-estimate --position-size <n> --entry-price <n> --stop-loss-price <n> [--take-profit-price <n>] [--confidence-level <n>]|trade-journal <trade_id> [--setup <text>] [--lessons <text>] [--improvement <text>]|approvals-list|approvals-approve <id> [reason]|"
        "approvals-reject <id> [reason]|approvals-dispatch|"
        "approvals-seed [count]|"
        "approvals-api [host] [port]|events-stats|"
        "events-list [limit] [--unprocessed]|events-process [limit]|"
        "events-actions [limit] [event_kind|--kind <event_kind>] [--correlation-id <id>]|"
        "events-prune-actions [days]|"
        "location-update <latitude> <longitude> [--source <name>] [--accuracy-m <meters>]|"
        "location-last|"
        "monitor-run-once|"
        "hud-run [--width N] [--height N] [--opacity X] [--duration-ms N]|"
        "webhook-listen [source] [host] [port]|"
        "voice-self-test [--iterations N] [--max-roundtrip-ms X]|"
        "vision-listen [source] [host] [port]|"
        "vision-shortcut-template [url]|"
        "vision-shortcut-guide [url]|"
        "vision-analyze <file|base64|-> [--no-faces] [--no-colors] [--no-landmarks] [--max-colors N]|"
        "vision-self-test [json|multipart|binary|all] [--with-secret] [--report] [--fail-fast] [--max-modes N] [--modes csv] [--output-file path.json] [--output-format json|jsonl]|"
        "vision-self-test-summary <input.jsonl> [--mode json|multipart|binary|all] [--last N] [--percentiles csv] [--strict] [--max-invalid-lines N] [--ema-alpha A] [--max-invalid-line-rate-delta X] [--max-invalid-line-rate-ema X]"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
