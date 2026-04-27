"""Shared trade review artifact generation for CLI and API surfaces."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .config import Config
from .tools.trade import (
    build_trade_performance_report,
    build_trade_replay_report,
    daily_drawdown_limit_for_equity,
)


def _trade_review_paths(review_date: str, output_file: str | None = None) -> tuple[Path, Path, Path, Path]:
    reviews_dir = Path(__file__).resolve().parent.parent / "docs" / "reviews"
    artifacts_dir = reviews_dir / "artifacts"
    markdown_path = (
        Path(output_file).expanduser()
        if output_file
        else (reviews_dir / f"paper-performance-review-{review_date}.md")
    )
    audit_path = artifacts_dir / f"paper-audit-{review_date}.jsonl"
    replay_path = artifacts_dir / f"paper-trade-replay-{review_date}.json"
    performance_path = artifacts_dir / f"paper-trade-performance-{review_date}.json"
    return markdown_path, audit_path, replay_path, performance_path


def _extract_review_metadata(review_markdown: str, performance_path: Path) -> tuple[str, str, str, int | None]:
    decision_value = "unknown"
    reviewer = ""
    strategy_version = ""
    for line in review_markdown.splitlines():
        if line.startswith("- Decision:"):
            decision_value = line.split(":", 1)[1].strip() or "unknown"
            continue
        if line.startswith("- Reviewer:"):
            reviewer = line.split(":", 1)[1].strip()
            continue
        if line.startswith("- Strategy/system version:"):
            strategy_version = line.split(":", 1)[1].strip()

    trade_count: int | None = None
    try:
        if performance_path.exists():
            performance_payload = json.loads(performance_path.read_text(encoding="utf-8"))
            raw_trade_count = performance_payload.get("trade_count")
            if isinstance(raw_trade_count, int):
                trade_count = raw_trade_count
    except (OSError, json.JSONDecodeError):
        trade_count = None

    return decision_value, reviewer, strategy_version, trade_count


def load_latest_trade_review_artifact() -> dict[str, Any] | None:
    reviews_dir = Path(__file__).resolve().parent.parent / "docs" / "reviews"
    candidates = sorted(
        reviews_dir.glob("paper-performance-review-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None

    markdown_path = candidates[0]
    review_markdown = markdown_path.read_text(encoding="utf-8")
    review_date = markdown_path.stem.removeprefix("paper-performance-review-")
    _, audit_path, replay_path, performance_path = _trade_review_paths(review_date)

    decision_value, reviewer, strategy_version, trade_count = _extract_review_metadata(
        review_markdown,
        performance_path,
    )

    return {
        "ok": True,
        "review_id": f"paper-review-{review_date}",
        "review_markdown": str(markdown_path),
        "review_markdown_content": review_markdown,
        "audit_export": str(audit_path),
        "trade_replay_report": str(replay_path),
        "trade_performance_report": str(performance_path),
        "auto_decision": decision_value,
        "reviewer": reviewer,
        "strategy_version": strategy_version,
        "trade_count": trade_count,
    }


def load_trade_review_artifact(review_id: str) -> dict[str, Any] | None:
    review_date = review_id.removeprefix("paper-review-").strip()
    if not review_date:
        return None

    markdown_path, audit_path, replay_path, performance_path = _trade_review_paths(review_date)
    if not markdown_path.exists():
        return None

    review_markdown = markdown_path.read_text(encoding="utf-8")
    decision_value, reviewer, strategy_version, trade_count = _extract_review_metadata(
        review_markdown,
        performance_path,
    )

    return {
        "ok": True,
        "review_id": review_id,
        "review_markdown": str(markdown_path),
        "review_markdown_content": review_markdown,
        "audit_export": str(audit_path),
        "trade_replay_report": str(replay_path),
        "trade_performance_report": str(performance_path),
        "auto_decision": decision_value,
        "reviewer": reviewer,
        "strategy_version": strategy_version,
        "trade_count": trade_count,
    }


def list_recent_trade_review_artifacts(limit: int = 5) -> list[dict[str, Any]]:
    reviews_dir = Path(__file__).resolve().parent.parent / "docs" / "reviews"
    candidates = sorted(
        reviews_dir.glob("paper-performance-review-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[: max(1, limit)]

    items: list[dict[str, Any]] = []
    for markdown_path in candidates:
        review_date = markdown_path.stem.removeprefix("paper-performance-review-")
        review_markdown = markdown_path.read_text(encoding="utf-8")
        _, _, _, performance_path = _trade_review_paths(review_date)
        decision_value, reviewer, strategy_version, trade_count = _extract_review_metadata(
            review_markdown,
            performance_path,
        )
        items.append(
            {
                "review_id": f"paper-review-{review_date}",
                "review_date": review_date,
                "review_markdown": str(markdown_path),
                "auto_decision": decision_value,
                "reviewer": reviewer,
                "strategy_version": strategy_version,
                "trade_count": trade_count,
            }
        )
    return items


def generate_trade_review_artifact(
    config: Config,
    *,
    output_file: str | None = None,
    reviewer: str = "",
    strategy_version: str = "",
) -> dict[str, Any]:
    config.audit_db.parent.mkdir(parents=True, exist_ok=True)
    config.trades_log.parent.mkdir(parents=True, exist_ok=True)

    review_date = time.strftime("%Y-%m-%d", time.gmtime())
    review_id = f"paper-review-{review_date}"
    reviews_dir = Path(__file__).resolve().parent.parent / "docs" / "reviews"
    artifacts_dir = reviews_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    markdown_path, audit_path, replay_path, performance_path = _trade_review_paths(
        review_date,
        output_file=output_file,
    )

    audit_log = AuditLog(config.audit_db)
    performance_report = build_trade_performance_report(
        config.trades_log,
        audit_log=audit_log,
        mode="paper",
        min_trading_days=config.trading_review_min_trading_days,
        min_trades=config.trading_review_min_trades,
    )
    replay_report = build_trade_replay_report(audit_log, limit=500)

    with audit_path.open("w", encoding="utf-8") as handle:
        audit_log.export_jsonl(handle)
    replay_path.write_text(
        json.dumps(replay_report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    performance_path.write_text(
        json.dumps(performance_report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    template_path = reviews_dir / "paper-performance-review-template.md"
    template_text = template_path.read_text(encoding="utf-8")

    profit_factor = performance_report["pnl"]["profit_factor"]
    avg_r_multiple = performance_report["pnl"]["average_per_trade"]
    policy_violations = performance_report["audit"]["policy_violation_count"]
    dispatch_failures = performance_report["audit"]["dispatch_failure_count"]
    latency_slippage = (
        int(performance_report["anomalies"]["latency_count"])
        + int(performance_report["anomalies"]["slippage_count"])
    )
    drawdown_limit = daily_drawdown_limit_for_equity(
        config.trading_account_equity,
        config.trading_daily_drawdown_kill_pct,
    )
    window_check_pass = bool(performance_report["meets_minimum_window"])
    policy_check_pass = policy_violations == 0
    dispatch_check_pass = dispatch_failures == 0
    drawdown_check_pass = float(performance_report["risk"]["max_drawdown"]) <= drawdown_limit
    win_rate_pass = float(performance_report["pnl"]["win_rate"]) >= config.trading_review_min_win_rate
    profit_factor_pass = profit_factor is not None and float(profit_factor) > config.trading_review_min_profit_factor
    avg_r_multiple_pass = float(avg_r_multiple) > config.trading_review_min_avg_r_multiple
    anomalies_pass = latency_slippage <= config.trading_review_max_anomalies
    auto_ready_for_unlock = all(
        [
            window_check_pass,
            win_rate_pass,
            profit_factor_pass,
            avg_r_multiple_pass,
            anomalies_pass,
            policy_check_pass,
            dispatch_check_pass,
            drawdown_check_pass,
        ]
    )
    decision_value = "ready for manual sign-off" if auto_ready_for_unlock else "defer"
    failed_conditions: list[str] = []
    if not window_check_pass:
        failed_conditions.append("review_window_below_minimum")
    if not win_rate_pass:
        failed_conditions.append("win_rate_below_minimum")
    if not profit_factor_pass:
        failed_conditions.append("profit_factor_below_minimum")
    if not avg_r_multiple_pass:
        failed_conditions.append("avg_r_multiple_below_minimum")
    if not anomalies_pass:
        failed_conditions.append("anomaly_budget_exceeded")
    if not policy_check_pass:
        failed_conditions.append("policy_bypass_detected")
    if not dispatch_check_pass:
        failed_conditions.append("dispatch_failures_detected")
    if not drawdown_check_pass:
        failed_conditions.append("drawdown_guardrail_exceeded")
    conditions_value = "none" if not failed_conditions else ", ".join(failed_conditions)

    def metric_row(label: str, value: str, threshold: str, passed: bool) -> str:
        return f"| {label} | {value} | {threshold} | {'PASS' if passed else 'FAIL'} |"

    window = performance_report.get("window", {})
    review_markdown = template_text
    replacements = {
        "- Review ID:": f"- Review ID: {review_id}",
        "- Review date:": f"- Review date: {review_date}",
        "- Reviewer:": f"- Reviewer: {reviewer}",
        "- Strategy/system version:": f"- Strategy/system version: {strategy_version}",
        "- Start date/time:": f"- Start date/time: {window.get('start') or ''}",
        "- End date/time:": f"- End date/time: {window.get('end') or ''}",
        "- Trading days in window:": f"- Trading days in window: {performance_report['trading_days']}",
        "- Total paper trades:": f"- Total paper trades: {performance_report['trade_count']}",
        "- Data sources:": (
            f"- Data sources:\n"
            f"  - Audit export path: {audit_path}\n"
            f"  - Trade replay report path: {replay_path}\n"
            f"  - Trade performance report path: {performance_path}"
        ),
        "| Win rate |  |  |  |": metric_row(
            "Win rate",
            f"{performance_report['pnl']['win_rate']:.4f}",
            f"> {config.trading_review_min_win_rate:.4f}",
            win_rate_pass,
        ),
        "| Profit factor |  |  |  |": metric_row(
            "Profit factor",
            "n/a" if profit_factor is None else f"{float(profit_factor):.2f}",
            f"> {config.trading_review_min_profit_factor:.2f}",
            profit_factor_pass,
        ),
        "| Max drawdown |  |  |  |": metric_row(
            "Max drawdown",
            f"{float(performance_report['risk']['max_drawdown']):.2f}",
            f"<= {drawdown_limit:.2f}",
            drawdown_check_pass,
        ),
        "| Avg R multiple |  |  |  |": metric_row(
            "Avg R multiple",
            f"{float(avg_r_multiple):.2f}",
            f"> {config.trading_review_min_avg_r_multiple:.2f} (proxy)",
            avg_r_multiple_pass,
        ),
        "| Slippage/latency anomalies |  |  |  |": metric_row(
            "Slippage/latency anomalies",
            str(latency_slippage),
            f"<= {config.trading_review_max_anomalies}",
            anomalies_pass,
        ),
        "| Policy violations |  | 0 |  |": metric_row(
            "Policy violations",
            str(policy_violations),
            "0",
            policy_check_pass,
        ),
        "- [ ] Review window >= 20 trading days OR >= 100 paper trades (whichever is later).": (
            f"- [{'x' if window_check_pass else ' '}] Review window >= {config.trading_review_min_trading_days} "
            f"trading days OR >= {config.trading_review_min_trades} paper trades (whichever is later)."
        ),
        "- [ ] No unresolved policy bypass attempts.": f"- [{'x' if policy_check_pass else ' '}] No unresolved policy bypass attempts.",
        "- [ ] No unexplained trade dispatch failures.": f"- [{'x' if dispatch_check_pass else ' '}] No unexplained trade dispatch failures.",
        "- [ ] Drawdown stayed within configured daily and overall guardrails.": f"- [{'x' if drawdown_check_pass else ' '}] Drawdown stayed within configured daily and overall guardrails.",
        "- Notes\n-": (
            f"- Notes\n"
            f"- Auto-generated readiness: {'ready_for_manual_signoff' if auto_ready_for_unlock else 'needs_operator_review'}\n"
            f"- Dispatch failures: {dispatch_failures}\n"
            f"- Daily drawdown limit used for guardrail check: {drawdown_limit:.2f}"
        ),
        "- Decision: approve live unlock / defer": f"- Decision: {decision_value}",
        "- Conditions (if any):\n-": f"- Conditions (if any):\n- {conditions_value}",
    }
    for old, new in replacements.items():
        review_markdown = review_markdown.replace(old, new)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(review_markdown, encoding="utf-8")

    return {
        "ok": True,
        "review_id": review_id,
        "review_markdown": str(markdown_path),
        "review_markdown_content": review_markdown,
        "audit_export": str(audit_path),
        "trade_replay_report": str(replay_path),
        "trade_performance_report": str(performance_path),
        "trade_count": performance_report["trade_count"],
        "trading_days": performance_report["trading_days"],
        "meets_minimum_window": performance_report["meets_minimum_window"],
        "auto_checks": {
            "review_window": window_check_pass,
            "win_rate": win_rate_pass,
            "profit_factor": profit_factor_pass,
            "avg_r_multiple": avg_r_multiple_pass,
            "anomalies": anomalies_pass,
            "policy_bypass": policy_check_pass,
            "dispatch_failures": dispatch_check_pass,
            "drawdown_guardrail": drawdown_check_pass,
            "ready_for_manual_signoff": auto_ready_for_unlock,
        },
        "auto_decision": decision_value,
        "auto_conditions": failed_conditions,
    }
