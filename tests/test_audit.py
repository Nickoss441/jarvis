"""Tests for the audit log. No API keys required."""
import io
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from jarvis.audit import AuditLog, redact_payload


def _fresh_log() -> AuditLog:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return AuditLog(Path(f.name))


def test_append_increments_id():
    log = _fresh_log()
    id1 = log.append("test", {"x": 1})
    id2 = log.append("test", {"x": 2})
    assert id2 == id1 + 1


def test_recent_returns_in_reverse_order():
    log = _fresh_log()
    log.append("a", {"n": 1})
    log.append("a", {"n": 2})
    log.append("b", {"n": 3})
    rows = log.recent(limit=10)
    assert [r["payload"]["n"] for r in rows] == [3, 2, 1]


def test_recent_filters_by_kind():
    log = _fresh_log()
    log.append("a", {"n": 1})
    log.append("b", {"n": 2})
    log.append("a", {"n": 3})
    rows = log.recent(kind="a")
    assert len(rows) == 2
    assert all(r["kind"] == "a" for r in rows)


def test_verify_clean_chain():
    log = _fresh_log()
    for i in range(5):
        log.append("test", {"i": i})
    assert log.verify() is True


def test_verify_detects_payload_tampering():
    log = _fresh_log()
    log.append("test", {"x": 1})
    log.append("test", {"x": 2})
    log.append("test", {"x": 3})

    with sqlite3.connect(log.db_path) as con:
        con.execute(
            "UPDATE events SET payload = ? WHERE id = 2",
            ('{"x": 999}',),
        )

    assert log.verify() is False


def test_verify_detects_deletion():
    log = _fresh_log()
    log.append("test", {"x": 1})
    log.append("test", {"x": 2})
    log.append("test", {"x": 3})

    with sqlite3.connect(log.db_path) as con:
        con.execute("DELETE FROM events WHERE id = 2")

    assert log.verify() is False


def test_redact_payload_top_level_key() -> None:
    redacted = redact_payload({"api_key": "abc123", "safe": "ok"})
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["safe"] == "ok"


def test_redact_payload_nested_key() -> None:
    redacted = redact_payload({"meta": {"secret": "shh", "name": "x"}})
    assert redacted["meta"]["secret"] == "[REDACTED]"
    assert redacted["meta"]["name"] == "x"


def test_redact_payload_list_of_dicts() -> None:
    redacted = redact_payload(
        {"items": [{"token": "t1"}, {"token": "t2"}, {"kind": "safe"}]}
    )
    assert redacted["items"][0]["token"] == "[REDACTED]"
    assert redacted["items"][1]["token"] == "[REDACTED]"
    assert redacted["items"][2]["kind"] == "safe"


def test_redact_payload_unknown_key_untouched() -> None:
    payload = {"note": "hello", "amount": 12}
    redacted = redact_payload(payload)
    assert redacted == payload


def test_redact_payload_none_value_redacted() -> None:
    redacted = redact_payload({"password": None})
    assert redacted["password"] == "[REDACTED]"


def test_redact_payload_already_redacted_idempotent() -> None:
    payload = {"token": "[REDACTED]", "nested": {"secret": "[REDACTED]"}}
    first = redact_payload(payload)
    second = redact_payload(first)
    assert first == second


def test_append_persists_redacted_payload() -> None:
    log = _fresh_log()
    log.append("tool", {"card_number": "4242424242424242", "safe": "ok"})
    row = log.recent(limit=1)[0]
    assert row["payload"]["card_number"] == "[REDACTED]"
    assert row["payload"]["safe"] == "ok"


def test_export_jsonl_roundtrip_parse_check() -> None:
    log = _fresh_log()
    log.append("alpha", {"n": 1})
    log.append("beta", {"n": 2})

    buf = io.StringIO()
    count = log.export_jsonl(buf)
    lines = [line for line in buf.getvalue().splitlines() if line.strip()]

    assert count == 2
    parsed = [json.loads(line) for line in lines]
    assert [row["kind"] for row in parsed] == ["alpha", "beta"]
    assert parsed[0]["payload"]["n"] == 1
    assert parsed[1]["payload"]["n"] == 2


def test_stats_returns_counts_timestamps_and_chain_length(monkeypatch) -> None:
    log = _fresh_log()
    ticks = iter([1000.0, 1005.0, 1010.0])
    monkeypatch.setattr("jarvis.audit.time.time", lambda: next(ticks))

    log.append("alpha", {"x": 1})
    log.append("alpha", {"x": 2})
    log.append("beta", {"x": 3})

    stats = log.stats()

    assert stats["kinds"] == {"alpha": 2, "beta": 1}
    assert stats["oldest_ts"] == 1000.0
    assert stats["newest_ts"] == 1010.0
    assert stats["chain_length"] == 3


def test_audit_verify_detects_tampered_payload() -> None:
    log = _fresh_log()
    log.append("test", {"x": 1})
    log.append("test", {"x": 2})
    log.append("test", {"x": 3})

    with sqlite3.connect(log.db_path) as con:
        con.execute(
            "UPDATE events SET payload = ? WHERE id = 2",
            ('{"x": 999}',),
        )

    assert log.verify() is False


def test_audit_verify_detects_tampered_hash() -> None:
    log = _fresh_log()
    log.append("test", {"x": 1})
    log.append("test", {"x": 2})
    log.append("test", {"x": 3})

    with sqlite3.connect(log.db_path) as con:
        con.execute(
            "UPDATE events SET prev_hash = ? WHERE id = 3",
            ("f" * 64,),
        )

    assert log.verify() is False


@pytest.mark.parametrize(
    "kind",
    [
        "approval_requested",
        "approval_approved",
        "approval_rejected",
        "approval_expired",
        "approval_dispatched",
    ],
)
def test_audit_verify_detects_tampering_for_approval_event_types(kind: str) -> None:
    log = _fresh_log()
    log.append(kind, {"approval_id": "appr-1", "correlation_id": "corr-1", "status": "ok"})

    with sqlite3.connect(log.db_path) as con:
        con.execute(
            "UPDATE events SET payload = ? WHERE id = 1",
            (json.dumps({"approval_id": "appr-1", "correlation_id": "corr-1", "status": "tampered"}),),
        )

    assert log.verify() is False
