import json
import hmac
import hashlib
import threading
import urllib.parse
import urllib.error
import urllib.request
import types

from jarvis.approval_api import create_approval_api_server
from jarvis.approval_service import ApprovalService
from jarvis.config import Config
from jarvis.event_bus import EventBus
from jarvis.tools.payments import dispatch_payment


def _cfg(tmp_path):
    return Config(
        anthropic_api_key="test-key",
        model="claude-sonnet-4-6",
        notes_dir=tmp_path / "notes",
        audit_db=tmp_path / "audit.db",
        user_name="Nick",
        approval_db=tmp_path / "approvals.db",
        message_outbox=tmp_path / "outbox.jsonl",
        event_bus_db=tmp_path / "event-bus.db",
        payments_ledger=tmp_path / "payments-ledger.jsonl",
        payments_budget_db=tmp_path / "payments-budget.db",
        approvals_api_host="127.0.0.1",
        approvals_api_port=0,
    )


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as r:  # noqa: S310
        return json.loads(r.read().decode("utf-8"))


def _get_json_with_status(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url) as r:  # noqa: S310
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _get_text(url: str) -> str:
    with urllib.request.urlopen(url) as r:  # noqa: S310
        return r.read().decode("utf-8")


def _get_raw(url: str) -> tuple[int, str, str, str]:
    with urllib.request.urlopen(url) as r:  # noqa: S310
        return (
            r.status,
            r.headers.get("Content-Type", ""),
            r.headers.get("Content-Disposition", ""),
            r.read().decode("utf-8"),
        )


def _post_json(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:  # noqa: S310
        return r.status, json.loads(r.read().decode("utf-8"))


def _post_json_with_status(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:  # noqa: S310
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post_json_with_headers(url: str, body: dict, headers: dict[str, str]) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers=request_headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as r:  # noqa: S310
        return r.status, json.loads(r.read().decode("utf-8"))


def _post_json_with_headers_and_status(url: str, body: dict, headers: dict[str, str]) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:  # noqa: S310
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post_form_with_status(url: str, form: dict[str, str]) -> tuple[int, dict]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:  # noqa: S310
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post_form_raw(url: str, form: dict[str, str]) -> tuple[int, str, str]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:  # noqa: S310
        return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8")


def _sign(secret: str, body: dict) -> str:
    raw = json.dumps(body).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, digestmod=hashlib.sha256).hexdigest()


def test_approval_api_pending_and_approve_flow(tmp_path):
    cfg = _cfg(tmp_path)
    service = ApprovalService(cfg)
    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        pending = _get_json(f"http://{host}:{port}/approvals/pending")
        assert len(pending["items"]) >= 1
        assert any(item["id"] == approval_id for item in pending["items"])

        status, approved = _post_json(
            f"http://{host}:{port}/approvals/{approval_id}/approve",
            {"reason": "ok"},
        )
        assert status == 200
        assert approved["status"] == "approved"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_serves_web_ui_root(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.trading_review_min_trading_days = 30
    cfg.trading_review_min_trades = 150
    cfg.trading_review_min_win_rate = 0.55
    cfg.trading_review_min_profit_factor = 1.25
    cfg.trading_review_min_avg_r_multiple = 0.15
    cfg.trading_review_max_anomalies = 2
    cfg.trading_account_equity = 250000.0
    cfg.trading_daily_drawdown_kill_pct = 4.5

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        html = _get_text(f"http://{host}:{port}/")
        assert "Jarvis Approval Queue" in html
        assert "Refresh Pending" in html
        assert "/approvals/pending" in html
        assert "Chat with Jarvis" in html
        assert "/chat/inbound" in html
        assert "/chat/history" in html
        assert "Send Message" in html
        assert "Load History" in html
        assert "chatTranscript" in html
        assert "Ctrl+Enter" in html
        assert "Trade Review Policy" in html
        assert "Generate Review Artifact" in html
        assert "Download Selected Review" in html
        assert "Performance JSON" in html
        assert "Replay JSON" in html
        assert "Audit JSONL" in html
        assert "Latest Review Preview" in html
        assert "Recent Reviews" in html
        assert "loadLatestTradeReviewArtifact()" in html
        assert "loadTradeReviewHistory()" in html
        assert "downloadTradeReviewArtifact()" in html
        assert "downloadTradeReviewSupportingArtifact('trade_performance_report')" in html
        assert "Min trading days: 30" in html
        assert "Min paper trades: 150" in html
        assert "Min win rate: 0.5500" in html
        assert "Min profit factor: 1.25" in html
        assert "Min avg R multiple: 0.15" in html
        assert "Max anomalies: 2" in html
        assert "Daily drawdown guardrail: 11250.00" in html
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_serves_react_hud_viewport_and_assets(tmp_path):
    cfg = _cfg(tmp_path)

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        viewport_html = _get_text(f"http://{host}:{port}/hud/react")
        app_js = _get_text(f"http://{host}:{port}/hud/react/app.js")
        styles_css = _get_text(f"http://{host}:{port}/hud/react/styles.css")

        assert "Jarvis React HUD" in viewport_html
        assert "/hud/react/app.js" in viewport_html
        assert "/hud/react/styles.css" in viewport_html

        assert "createRoot" in app_js
        assert "HudViewport" in app_js
        assert "THREE.Scene" in app_js
        assert "GlobeLayer" in app_js
        assert "GLOBE_MARKERS" in app_js
        assert "Hormuz" in app_js
        assert "Kabul" in app_js
        assert "Raycaster" in app_js
        assert "SlidePanel" in app_js
        assert "onMarkerSelect" in app_js
        assert "No critical alerts" in app_js

        assert ".hud-shell" in styles_css
        assert ".globe-frame" in styles_css
        assert ".hud-footnotes" in styles_css
        assert ".hud-slide-panel" in styles_css
        assert ".hud-slide-panel.is-open" in styles_css
        assert "radial-gradient" in styles_css
        assert "@media (max-width: 760px)" in styles_css
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_dispatch_endpoint(tmp_path):
    cfg = _cfg(tmp_path)
    service = ApprovalService(cfg)
    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )
    assert service.approve(approval_id)

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, dispatched = _post_json(
            f"http://{host}:{port}/approvals/dispatch",
            {"limit": 10},
        )
        assert status == 200
        assert dispatched["failures"] == 0
        assert len(dispatched["items"]) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_trade_review_artifact_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    expected = {
        "ok": True,
        "review_markdown": str(tmp_path / "review.md"),
        "review_markdown_content": "# Review\n\n- Decision: defer\n",
        "trade_performance_report": str(tmp_path / "performance.json"),
        "auto_decision": "defer",
        "auto_conditions": ["review_window_below_minimum"],
    }

    def fake_generate_trade_review_artifact(config, *, output_file=None, reviewer="", strategy_version=""):
        assert config is cfg
        assert output_file == str(tmp_path / "custom-review.md")
        assert reviewer == "Ops"
        assert strategy_version == "v1.2.3"
        return expected

    monkeypatch.setattr(
        "jarvis.approval_api.generate_trade_review_artifact",
        fake_generate_trade_review_artifact,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json(
            f"http://{host}:{port}/trade/review-artifact",
            {
                "reviewer": "Ops",
                "strategy_version": "v1.2.3",
                "output": str(tmp_path / "custom-review.md"),
            },
        )
        assert status == 200
        assert payload == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_latest_trade_review_artifact_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    expected = {
        "ok": True,
        "review_markdown": str(tmp_path / "review.md"),
        "review_markdown_content": "# Review\n\n- Decision: ready for manual sign-off\n",
        "trade_performance_report": str(tmp_path / "performance.json"),
        "auto_decision": "ready for manual sign-off",
    }

    monkeypatch.setattr(
        "jarvis.approval_api.load_latest_trade_review_artifact",
        lambda: expected,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(f"http://{host}:{port}/trade/review-artifact/latest")
        assert status == 200
        assert payload == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_latest_trade_review_artifact_endpoint_404_when_missing(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(
        "jarvis.approval_api.load_latest_trade_review_artifact",
        lambda: None,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(f"http://{host}:{port}/trade/review-artifact/latest")
        assert status == 404
        assert payload["error"] == "trade review artifact not found"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_trade_review_item_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    expected = {
        "ok": True,
        "review_id": "paper-review-2026-04-27",
        "review_markdown": str(tmp_path / "review.md"),
        "review_markdown_content": "# Review\n\n- Decision: defer\n",
        "trade_performance_report": str(tmp_path / "performance.json"),
        "auto_decision": "defer",
    }

    def fake_load_trade_review_artifact(review_id):
        assert review_id == "paper-review-2026-04-27"
        return expected

    monkeypatch.setattr(
        "jarvis.approval_api.load_trade_review_artifact",
        fake_load_trade_review_artifact,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(
            f"http://{host}:{port}/trade/review-artifact/item?review_id=paper-review-2026-04-27"
        )
        assert status == 200
        assert payload == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_trade_review_download_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    expected = {
        "ok": True,
        "review_id": "paper-review-2026-04-27",
        "review_markdown": str(tmp_path / "review.md"),
        "review_markdown_content": "# Review\n\n- Decision: defer\n",
        "trade_performance_report": str(tmp_path / "performance.json"),
        "auto_decision": "defer",
    }

    monkeypatch.setattr(
        "jarvis.approval_api.load_trade_review_artifact",
        lambda review_id: expected if review_id == "paper-review-2026-04-27" else None,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, content_type, disposition, body = _get_raw(
            f"http://{host}:{port}/trade/review-artifact/download?review_id=paper-review-2026-04-27"
        )
        assert status == 200
        assert content_type.startswith("text/markdown")
        assert 'filename="review.md"' in disposition
        assert body == expected["review_markdown_content"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_trade_review_supporting_artifact_download_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    performance_path = tmp_path / "performance.json"
    performance_path.write_text('{"ok": true}\n', encoding="utf-8")
    expected = {
        "ok": True,
        "review_id": "paper-review-2026-04-27",
        "trade_performance_report": str(performance_path),
    }

    monkeypatch.setattr(
        "jarvis.approval_api.load_trade_review_artifact",
        lambda review_id: expected if review_id == "paper-review-2026-04-27" else None,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, content_type, disposition, body = _get_raw(
            f"http://{host}:{port}/trade/review-artifact/download-artifact?review_id=paper-review-2026-04-27&kind=trade_performance_report"
        )
        assert status == 200
        assert content_type.startswith("application/json")
        assert 'filename="performance.json"' in disposition
        assert body == '{"ok": true}\n'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_trade_review_history_endpoint(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    expected = [
        {
            "review_id": "paper-review-2026-04-27",
            "review_date": "2026-04-27",
            "review_markdown": str(tmp_path / "review-1.md"),
            "auto_decision": "defer",
        },
        {
            "review_id": "paper-review-2026-04-26",
            "review_date": "2026-04-26",
            "review_markdown": str(tmp_path / "review-2.md"),
            "auto_decision": "ready for manual sign-off",
        },
    ]

    def fake_list_recent_trade_review_artifacts(limit=5):
        assert limit == 5
        return expected

    monkeypatch.setattr(
        "jarvis.approval_api.list_recent_trade_review_artifacts",
        fake_list_recent_trade_review_artifacts,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(f"http://{host}:{port}/trade/review-artifact/history?limit=5")
        assert status == 200
        assert payload == {"items": expected}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_health_endpoint_reports_event_bus_and_monitors(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(f"http://{host}:{port}/health")

        assert status == 200
        assert payload["status"] == "ok"
        assert payload["event_bus"]["healthy"] is True
        assert payload["event_bus"]["db_path"] == str(cfg.event_bus_db)
        assert payload["monitors"]["configured"] == 4
        assert "calendar" in payload["monitors"]["sources"]
        assert "filesystem" in payload["monitors"]["sources"]
        assert payload["chat"]["configured"] is True
        assert payload["chat"]["accounts"] >= 1
        assert payload["ai"]["provider"] == "anthropic"
        assert payload["ai"]["ready"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_health_endpoint_returns_503_when_event_bus_unhealthy(
    tmp_path,
    monkeypatch,
):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = ""
    cfg.chat_auth_token = ""
    monkeypatch.setattr("jarvis.approval_api.EventBus.healthcheck", lambda self: False)

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(f"http://{host}:{port}/health")

        assert status == 503
        assert payload["status"] == "degraded"
        assert payload["event_bus"]["healthy"] is False
        assert payload["monitors"]["configured"] == 4
        assert payload["chat"]["configured"] is False
        assert payload["chat"]["accounts"] == 0
        assert payload["ai"]["provider"] == "anthropic"
        assert payload["ai"]["ready"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_edit_endpoint_updates_pending_item(tmp_path):
    cfg = _cfg(tmp_path)
    service = ApprovalService(cfg)
    approval_id = service.request(
        "message_send",
        {
            "channel": "email",
            "recipient": "user@example.com",
            "subject": "Hi",
            "body": "hello",
        },
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, edited = _post_json(
            f"http://{host}:{port}/approvals/{approval_id}/edit",
            {
                "payload": {
                    "channel": "email",
                    "recipient": "user@example.com",
                    "subject": "Updated",
                    "body": "edited body",
                },
                "action": "send_updated_email",
                "reason": "user corrected content",
                "budget_impact": 0.0,
                "ttl_seconds": 300,
                "risk_tier": "high",
            },
        )
        assert status == 200
        assert edited["status"] == "edited"

        pending = _get_json(f"http://{host}:{port}/approvals/pending")
        updated = next(item for item in pending["items"] if item["id"] == approval_id)
        assert updated["payload"]["subject"] == "Updated"
        assert updated["payload"]["body"] == "edited body"
        assert updated["action"] == "send_updated_email"
        assert updated["reason"] == "user corrected content"
        assert updated["risk_tier"] == "high"
        assert updated["ttl_seconds"] == 300
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_edit_endpoint_rejects_non_object_payload(tmp_path):
    cfg = _cfg(tmp_path)
    service = ApprovalService(cfg)
    approval_id = service.request("message_send", {"body": "hello"})

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_status(
            f"http://{host}:{port}/approvals/{approval_id}/edit",
            {"payload": ["not", "an", "object"]},
        )
        assert status == 400
        assert payload["error"] == "payload must be an object"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_edit_endpoint_404_for_missing_item(tmp_path):
    cfg = _cfg(tmp_path)

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_status(
            f"http://{host}:{port}/approvals/missing-id/edit",
            {"payload": {"body": "x"}},
        )
        assert status == 404
        assert payload["error"] == "approval not found or not pending"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_approval_api_edit_endpoint_rejects_invalid_numeric_values(tmp_path):
    cfg = _cfg(tmp_path)
    service = ApprovalService(cfg)
    approval_id = service.request("message_send", {"body": "hello"})

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_status(
            f"http://{host}:{port}/approvals/{approval_id}/edit",
            {"budget_impact": "not-a-number", "ttl_seconds": 10},
        )
        assert status == 400
        assert "invalid edit envelope values" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_inbound_accepts_authorized_message_and_emits_event(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "chat-secret",
                "source": "ios_shortcuts",
                "text": "book me a dentist appointment next week",
            },
        )
        assert status == 202
        assert payload["status"] == "accepted"
        assert payload["event_id"]

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="chat_message")
        assert len(events) >= 1
        latest = events[0]
        assert latest.payload["account_id"] == "nick"
        assert "appointment" in latest.payload["text"].lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_inbound_returns_reply_when_chat_brain_available(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    fake_brain = types.SimpleNamespace(turn=lambda _text: "Got it. I can help with that.")
    monkeypatch.setattr("jarvis.approval_api.build_brain_from_config", lambda _cfg: fake_brain)

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "chat-secret",
                "source": "ios_shortcuts",
                "text": "hey jarvis help me plan tomorrow",
            },
        )
        assert status == 202
        assert payload["status"] == "accepted"
        assert payload.get("reply") == "Got it. I can help with that."
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_inbound_rejects_invalid_token(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_status(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "wrong-token",
                "source": "ios_shortcuts",
                "text": "book dinner",
            },
        )
        assert status == 401
        assert payload["error"] == "unauthorized"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_history_returns_account_messages(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_accounts = {
        "nick": "chat-secret",
        "jane": "jane-secret",
    }

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status_a, _ = _post_json(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "chat-secret",
                "source": "ios_shortcuts",
                "text": "first from nick",
            },
        )
        assert status_a == 202

        status_b, _ = _post_json(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "jane",
                "token": "jane-secret",
                "source": "ios_shortcuts",
                "text": "hello from jane",
            },
        )
        assert status_b == 202

        status_c, _ = _post_json(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "chat-secret",
                "source": "ios_shortcuts",
                "text": "second from nick",
            },
        )
        assert status_c == 202

        hist_status, hist = _get_json_with_status(
            f"http://{host}:{port}/chat/history?account_id=nick&token=chat-secret&limit=10"
        )
        assert hist_status == 200
        assert len(hist["items"]) >= 2
        texts = [item["text"] for item in hist["items"]]
        assert "first from nick" in texts
        assert "second from nick" in texts
        assert "hello from jane" not in texts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_history_rejects_invalid_token(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _get_json_with_status(
            f"http://{host}:{port}/chat/history?account_id=nick&token=wrong&limit=10"
        )
        assert status == 401
        assert payload["error"] == "unauthorized"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_twilio_accepts_form_payload_and_emits_event(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/chat/twilio?account_id=nick&token=chat-secret&response_format=json",
            {
                "From": "+15551234567",
                "To": "+15557654321",
                "Body": "schedule dentist tomorrow",
                "MessageSid": "SM123",
            },
        )
        assert status == 200
        assert payload["status"] == "accepted"
        assert payload["event_id"]

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="chat_message")
        assert len(events) >= 1
        latest = events[0]
        assert latest.payload["account_id"] == "nick"
        assert latest.payload["sender"] == "+15551234567"
        assert latest.payload["text"] == "schedule dentist tomorrow"
        assert latest.payload["sms_command"]["recognized"] is False
        assert latest.source == "chat_twilio_sms"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_twilio_rejects_invalid_auth(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/chat/twilio?account_id=nick&token=wrong&response_format=json",
            {
                "From": "+15551234567",
                "Body": "hello",
            },
        )
        assert status == 401
        assert payload["error"] == "unauthorized"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_twilio_returns_twiml_by_default(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, content_type, body = _post_form_raw(
            f"http://{host}:{port}/chat/twilio?account_id=nick&token=chat-secret",
            {
                "From": "+15551234567",
                "To": "+15557654321",
                "Body": "hello from twilio",
                "MessageSid": "SMTwiML1",
            },
        )
        assert status == 200
        assert "application/xml" in content_type
        assert "<Response>" in body
        assert "<Message>" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_twilio_parses_command_and_returns_it_in_json_response(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = "nick"
    cfg.chat_auth_token = "chat-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/chat/twilio?account_id=nick&token=chat-secret&response_format=json",
            {
                "From": "+15551234567",
                "To": "+15557654321",
                "Body": "approve approval-123 looks good",
                "MessageSid": "SM-CMD-1",
            },
        )
        assert status == 200
        assert payload["status"] == "accepted"
        assert payload["sms_command"]["recognized"] is True
        assert payload["sms_command"]["intent"] == "approve"
        assert payload["sms_command"]["approval_id"] == "approval-123"

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="chat_message")
        assert len(events) >= 1
        latest = events[0]
        assert latest.payload["sms_command"]["recognized"] is True
        assert latest.payload["sms_command"]["intent"] == "approve"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_twilio_webhook_bridge_returns_503_when_not_configured(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.twilio_webhook_token = ""

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/webhooks/twilio?token=anything",
            {"MessageSid": "SM123", "Body": "hello"},
        )
        assert status == 503
        assert "not configured" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_twilio_webhook_bridge_rejects_invalid_token(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.twilio_webhook_token = "bridge-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/webhooks/twilio?token=wrong",
            {"MessageSid": "SM123", "Body": "hello"},
        )
        assert status == 401
        assert payload["error"] == "unauthorized"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_twilio_webhook_bridge_accepts_sms_payload_and_emits_event(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.twilio_webhook_token = "bridge-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/webhooks/twilio?token=bridge-secret",
            {
                "AccountSid": "AC123",
                "MessageSid": "SM123",
                "From": "+15551234567",
                "To": "+15557654321",
                "Body": "ping from twilio",
                "SmsStatus": "received",
            },
        )
        assert status == 200
        assert payload["status"] == "accepted"
        assert payload["event_id"]

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="twilio_webhook")
        assert len(events) >= 1
        latest = events[0]
        assert latest.source == "twilio_webhook_bridge"
        assert latest.payload["event_type"] == "sms"
        assert latest.payload["message_sid"] == "SM123"
        assert latest.payload["from"] == "+15551234567"
        assert latest.payload["body"] == "ping from twilio"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_twilio_webhook_bridge_accepts_voice_payload_and_emits_event(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.twilio_webhook_token = "bridge-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_form_with_status(
            f"http://{host}:{port}/webhooks/twilio?token=bridge-secret",
            {
                "AccountSid": "AC123",
                "CallSid": "CA123",
                "From": "+15551234567",
                "To": "+15557654321",
                "CallStatus": "completed",
                "RecordingSid": "RE123",
                "RecordingUrl": "https://api.twilio.test/recordings/RE123",
            },
        )
        assert status == 200
        assert payload["status"] == "accepted"
        assert payload["event_id"]

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="twilio_webhook")
        assert len(events) >= 1
        latest = events[0]
        assert latest.source == "twilio_webhook_bridge"
        assert latest.payload["event_type"] == "voice_call"
        assert latest.payload["call_sid"] == "CA123"
        assert latest.payload["call_status"] == "completed"
        assert latest.payload["recording_sid"] == "RE123"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_chat_inbound_returns_503_when_not_configured(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.chat_account_id = ""
    cfg.chat_auth_token = ""
    cfg.chat_accounts = {}

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_status(
            f"http://{host}:{port}/chat/inbound",
            {
                "account_id": "nick",
                "token": "chat-secret",
                "text": "book dinner reservation",
            },
        )
        assert status == 503
        assert "not configured" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_payments_reconcile_returns_503_when_not_configured(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.payments_webhook_secret = ""

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_headers_and_status(
            f"http://{host}:{port}/payments/reconcile",
            {
                "provider": "stripe",
                "event_id": "evt_1",
                "amount": 12.5,
                "currency": "USD",
                "external_txid": "tx_1",
            },
            {"X-Jarvis-Signature": "bad"},
        )
        assert status == 503
        assert "not configured" in payload["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_payments_reconcile_rejects_invalid_signature(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.payments_webhook_secret = "reconcile-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        status, payload = _post_json_with_headers_and_status(
            f"http://{host}:{port}/payments/reconcile",
            {
                "provider": "stripe",
                "event_id": "evt_2",
                "amount": 12.5,
                "currency": "USD",
                "external_txid": "tx_2",
            },
            {"X-Jarvis-Signature": "wrong"},
        )
        assert status == 401
        assert payload["error"] == "invalid signature"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_payments_reconcile_accepts_signed_unexpected_charge(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.payments_webhook_secret = "reconcile-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    body = {
        "provider": "stripe",
        "event_id": "evt_unexpected",
        "amount": 22.0,
        "currency": "USD",
        "merchant": "Cafe",
        "external_txid": "ch_unexpected",
    }
    signature = _sign(cfg.payments_webhook_secret, body)

    try:
        status, payload = _post_json_with_headers(
            f"http://{host}:{port}/payments/reconcile",
            body,
            {"X-Jarvis-Signature": signature},
        )
        assert status == 202
        assert payload["status"] == "unexpected"
        assert payload["matched"] is False
        assert payload["alert_approval_id"]

        pending = ApprovalService(cfg).list_pending(limit=20)
        alert = next(item for item in pending if item["id"] == payload["alert_approval_id"])
        assert alert["kind"] == "message_send"
        assert alert["risk_tier"] == "high"
        assert alert["payload"]["metadata"]["event_id"] == "evt_unexpected"

        events = EventBus(cfg.event_bus_db).recent(limit=5, kind="payment_reconciliation")
        assert len(events) >= 1
        latest = events[0]
        assert latest.payload["event_id"] == "evt_unexpected"
        assert latest.payload["status"] == "unexpected"
        assert latest.payload["alert_approval_id"] == payload["alert_approval_id"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_payments_reconcile_marks_matching_transaction(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.payments_webhook_secret = "reconcile-secret"

    dispatch_payment(
        mode="dry_run",
        ledger_path=cfg.payments_ledger,
        payload={
            "amount": 35.0,
            "currency": "USD",
            "recipient": "vendor@example.com",
            "merchant": "Vendor",
            "external_txid": "ch_match_me",
        },
        budget_db_path=cfg.payments_budget_db,
    )

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    body = {
        "provider": "stripe",
        "event_id": "evt_matched",
        "amount": 35.0,
        "currency": "USD",
        "merchant": "Vendor",
        "external_txid": "ch_match_me",
    }
    signature = _sign(cfg.payments_webhook_secret, body)

    try:
        status, payload = _post_json_with_headers(
            f"http://{host}:{port}/payments/reconcile",
            body,
            {"X-Jarvis-Signature": signature},
        )
        assert status == 202
        assert payload["status"] == "matched"
        assert payload["matched"] is True
        assert payload["alert_approval_id"] == ""

        pending = ApprovalService(cfg).list_pending(limit=20)
        assert all(item["kind"] != "message_send" for item in pending)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_payments_reconcile_rejects_duplicate_event_id(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.payments_webhook_secret = "reconcile-secret"

    server = create_approval_api_server(cfg, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    body = {
        "provider": "stripe",
        "event_id": "evt_duplicate",
        "amount": 15.0,
        "currency": "USD",
        "external_txid": "ch_dup",
    }
    signature = _sign(cfg.payments_webhook_secret, body)

    try:
        first_status, _first_payload = _post_json_with_headers(
            f"http://{host}:{port}/payments/reconcile",
            body,
            {"X-Jarvis-Signature": signature},
        )
        assert first_status == 202

        second_status, second_payload = _post_json_with_headers_and_status(
            f"http://{host}:{port}/payments/reconcile",
            body,
            {"X-Jarvis-Signature": signature},
        )
        assert second_status == 409
        assert second_payload["error"] == "duplicate reconciliation event"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
