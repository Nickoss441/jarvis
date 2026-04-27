"""Tests for the ApprovalEnvelope payload schema (action, reason, budget_impact,
ttl_seconds, risk_tier) — store persistence and service propagation."""
from __future__ import annotations

import pytest

from jarvis.approval import ApprovalEnvelope, ApprovalStore, RISK_TIERS, _DEFAULT_TTL_BY_TIER


# ── ApprovalEnvelope dataclass ────────────────────────────────────────────────

class TestApprovalEnvelopeDefaults:
    def test_defaults(self):
        env = ApprovalEnvelope()
        assert env.action == ""
        assert env.reason == ""
        assert env.budget_impact == 0.0
        assert env.ttl_seconds == _DEFAULT_TTL_BY_TIER["medium"]  # default tier applied
        assert env.risk_tier == "medium"

    def test_valid_risk_tier_accepted(self):
        for tier in RISK_TIERS:
            env = ApprovalEnvelope(risk_tier=tier)
            assert env.risk_tier == tier

    def test_invalid_risk_tier_falls_back_to_medium(self):
        env = ApprovalEnvelope(risk_tier="unknown_tier")
        assert env.risk_tier == "medium"

    def test_negative_budget_impact_normalised_to_zero(self):
        env = ApprovalEnvelope(budget_impact=-5.0)
        assert env.budget_impact == 0.0

    def test_negative_ttl_normalised_to_default(self):
        # Negative TTL is clamped to 0, which triggers the tier default
        env = ApprovalEnvelope(ttl_seconds=-1)
        assert env.ttl_seconds == _DEFAULT_TTL_BY_TIER["medium"]

    def test_ttl_default_by_tier_applied_when_zero(self):
        for tier, expected_ttl in _DEFAULT_TTL_BY_TIER.items():
            env = ApprovalEnvelope(risk_tier=tier, ttl_seconds=0)
            assert env.ttl_seconds == expected_ttl, f"tier={tier}"

    def test_explicit_ttl_not_overwritten(self):
        env = ApprovalEnvelope(risk_tier="high", ttl_seconds=999)
        assert env.ttl_seconds == 999


class TestApprovalEnvelopeSerialization:
    def test_to_dict_roundtrip(self):
        env = ApprovalEnvelope(
            action="send_payment",
            reason="pay invoice",
            budget_impact=42.5,
            ttl_seconds=600,
            risk_tier="high",
        )
        d = env.to_dict()
        assert d["action"] == "send_payment"
        assert d["reason"] == "pay invoice"
        assert d["budget_impact"] == 42.5
        assert d["ttl_seconds"] == 600
        assert d["risk_tier"] == "high"

    def test_from_dict_roundtrip(self):
        original = ApprovalEnvelope(
            action="place_trade",
            reason="market order",
            budget_impact=100.0,
            ttl_seconds=300,
            risk_tier="critical",
        )
        restored = ApprovalEnvelope.from_dict(original.to_dict())
        assert restored.action == original.action
        assert restored.reason == original.reason
        assert restored.budget_impact == original.budget_impact
        assert restored.ttl_seconds == original.ttl_seconds
        assert restored.risk_tier == original.risk_tier

    def test_from_dict_with_partial_data(self):
        env = ApprovalEnvelope.from_dict({"risk_tier": "low"})
        assert env.risk_tier == "low"
        assert env.action == ""
        assert env.budget_impact == 0.0

    def test_from_dict_with_empty_dict(self):
        env = ApprovalEnvelope.from_dict({})
        assert env.risk_tier == "medium"


# ── ApprovalStore persistence ─────────────────────────────────────────────────

class TestApprovalStoreEnvelope:
    def test_store_persists_envelope_fields(self, tmp_path):
        store = ApprovalStore(tmp_path / "approvals.db")
        env = ApprovalEnvelope(
            action="send_message",
            reason="user request",
            budget_impact=0.0,
            ttl_seconds=300,
            risk_tier="low",
        )
        approval_id = store.request("message_send", {"body": "hi"}, envelope=env)
        row = store.get(approval_id)
        assert row is not None
        assert row["action"] == "send_message"
        assert row["reason"] == "user request"
        assert row["budget_impact"] == 0.0
        assert row["ttl_seconds"] == 300
        assert row["risk_tier"] == "low"

    def test_list_pending_returns_envelope_fields(self, tmp_path):
        store = ApprovalStore(tmp_path / "approvals.db")
        env = ApprovalEnvelope(action="trade", risk_tier="critical")
        store.request("trade", {"symbol": "BTC"}, envelope=env)
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0]["risk_tier"] == "critical"
        assert pending[0]["action"] == "trade"

    def test_no_envelope_defaults_to_medium_tier(self, tmp_path):
        store = ApprovalStore(tmp_path / "approvals.db")
        approval_id = store.request("message_send", {"body": "hi"})
        row = store.get(approval_id)
        assert row is not None
        assert row["risk_tier"] == "medium"
        assert row["action"] == ""
        assert row["budget_impact"] == 0.0

    def test_high_budget_impact_persisted(self, tmp_path):
        store = ApprovalStore(tmp_path / "approvals.db")
        env = ApprovalEnvelope(budget_impact=9999.99, risk_tier="high")
        approval_id = store.request("payment", {"amount": 9999.99}, envelope=env)
        row = store.get(approval_id)
        assert row is not None
        assert abs(row["budget_impact"] - 9999.99) < 0.01

    def test_db_migration_adds_columns_to_existing_db(self, tmp_path):
        """A DB created without envelope columns should be migrated on open."""
        import sqlite3
        db_path = tmp_path / "legacy.db"
        # Create old-style DB with only original columns
        with sqlite3.connect(db_path) as con:
            con.execute(
                """CREATE TABLE approvals (
                    id TEXT PRIMARY KEY, ts REAL, kind TEXT, payload TEXT,
                    status TEXT, decision_ts REAL, decision_reason TEXT,
                    dispatch_ts REAL, dispatch_result TEXT, correlation_id TEXT
                )"""
            )
        # Opening via ApprovalStore should migrate it
        store = ApprovalStore(db_path)
        env = ApprovalEnvelope(action="migrated", risk_tier="low")
        approval_id = store.request("test", {"x": 1}, envelope=env)
        row = store.get(approval_id)
        assert row is not None
        assert row["action"] == "migrated"
        assert row["risk_tier"] == "low"


# ── ApprovalService propagation ───────────────────────────────────────────────

class TestApprovalServiceEnvelope:
    def _make_service(self, tmp_path):
        from jarvis.approval_service import ApprovalService
        from jarvis.config import Config

        cfg = Config(
            anthropic_api_key="test-key",
            model="claude-sonnet-4-6",
            notes_dir=str(tmp_path / "notes"),
            user_name="Test",
            approval_db=str(tmp_path / "approvals.db"),
            audit_db=str(tmp_path / "audit.db"),
        )
        svc = ApprovalService(config=cfg)
        return svc, svc.store

    def test_service_passes_envelope_to_store(self, tmp_path):
        svc, store = self._make_service(tmp_path)
        from jarvis.approval import ApprovalEnvelope
        env = ApprovalEnvelope(action="call_phone", risk_tier="high", budget_impact=0.0)
        approval_id = svc.request(
            "call_phone", {"number": "+15555550100"}, envelope=env
        )
        row = store.get(approval_id)
        assert row is not None
        assert row["risk_tier"] == "high"
        assert row["action"] == "call_phone"

    def test_service_without_envelope_uses_defaults(self, tmp_path):
        svc, store = self._make_service(tmp_path)
        approval_id = svc.request("message_send", {"body": "hi"})
        row = store.get(approval_id)
        assert row is not None
        assert row["risk_tier"] == "medium"
        assert row["action"] == ""

    def test_service_envelope_in_audit_log(self, tmp_path):
        from jarvis.approval_service import ApprovalService
        from jarvis.approval import ApprovalEnvelope
        from jarvis.config import Config

        cfg = Config(
            anthropic_api_key="test-key",
            model="claude-sonnet-4-6",
            notes_dir=str(tmp_path / "notes"),
            user_name="Test",
            approval_db=str(tmp_path / "approvals.db"),
            audit_db=str(tmp_path / "audit.db"),
        )
        svc = ApprovalService(config=cfg)
        env = ApprovalEnvelope(action="trade_btc", risk_tier="critical", reason="bot signal")
        svc.request("trade", {"symbol": "BTC"}, envelope=env)

        entries = svc.audit.recent(limit=10)
        assert len(entries) >= 1
        last = entries[0]
        assert last["kind"] == "approval_requested"
        assert last["payload"].get("risk_tier") == "critical"
        assert last["payload"].get("action") == "trade_btc"
        assert last["payload"].get("reason") == "bot signal"
