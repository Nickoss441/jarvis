from jarvis.approval import ApprovalStore
import time


def test_approval_lifecycle(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.db")

    approval_id = store.request("message_send", {"body": "hello"})

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0]["id"] == approval_id

    assert store.approve(approval_id, reason="looks good")

    approved = store.list_approved()
    assert len(approved) == 1
    assert approved[0]["id"] == approval_id
    assert approved[0]["decision_reason"] == "looks good"

    assert store.mark_dispatched(
        approval_id,
        success=True,
        result={"status": "dry_run_sent"},
    )

    updated = store.get(approval_id)
    assert updated is not None
    assert updated["status"] == "processed"
    assert updated["dispatch_result"]["status"] == "dry_run_sent"


def test_reject_pending_approval(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.db")

    approval_id = store.request("message_send", {"body": "x"})

    assert store.reject(approval_id, reason="not needed")
    row = store.get(approval_id)
    assert row is not None
    assert row["status"] == "rejected"


def test_expire_pending_auto_denies_stale_items(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.db")

    stale_ts = time.time() - 3600
    fresh_ts = time.time()
    stale_id = store.request("message_send", {"body": "old"}, created_ts=stale_ts)
    fresh_id = store.request("message_send", {"body": "new"}, created_ts=fresh_ts)

    expired_count = store.expire_pending(ttl_seconds=300)

    assert expired_count == 1
    stale = store.get(stale_id)
    fresh = store.get(fresh_id)
    assert stale is not None
    assert stale["status"] == "rejected"
    assert "expired" in stale["decision_reason"]
    assert fresh is not None
    assert fresh["status"] == "pending"
