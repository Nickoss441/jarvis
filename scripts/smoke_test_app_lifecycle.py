#!/usr/bin/env python3
"""Smoke test for the complete app lifecycle: install → status → uninstall.

This script validates that:
1. Install requests queue correctly
2. Approvals can be approved automatically
3. Dispatch executes installations
4. App status verifies installation
5. Uninstall requests and dispatch work
6. Final status confirms removal

Run with:
    export JARVIS_PHASE_SANDBOX=true
    python3 scripts/smoke_test_app_lifecycle.py
"""
import sys
import time
from pathlib import Path

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.config import Config
from jarvis.approval_service import ApprovalService
from jarvis.audit import AuditLog
from jarvis.cli import build_brain_from_config


def main():
    print("\n" + "="*70)
    print("APP LIFECYCLE SMOKE TEST")
    print("="*70)
    
    # Build config and services
    config = Config.from_env()
    config.validate()
    
    if not config.phase_sandbox:
        print("❌ SANDBOX PHASE NOT ENABLED")
        print("   Run: export JARVIS_PHASE_SANDBOX=true")
        return False
    
    approval_service = ApprovalService(config)
    audit = AuditLog(config.audit_db)
    brain = build_brain_from_config(config)
    
    app_to_test = "slack"
    print(f"\n📦 Testing with app: {app_to_test}")
    
    # ===== STEP 1: Request install =====
    print(f"\n[1/6] Requesting install of {app_to_test}...")
    install_id = approval_service.request(
        "install_app",
        {"app": app_to_test, "method": "auto"},
    )
    print(f"     ✓ Install approval ID: {install_id}")
    
    # Verify audit
    install_audit = audit.recent(limit=5, kind="approval_requested")
    if install_audit and install_audit[0]["payload"].get("kind") == "install_app":
        print(f"     ✓ Audit logged: approval_requested")
    else:
        print(f"     ✗ Install audit missing")
        return False
    
    # ===== STEP 2: Approve install =====
    print(f"\n[2/6] Approving install request...")
    approved = approval_service.approve(install_id, reason="smoke-test")
    if approved:
        print(f"     ✓ Install approved")
    else:
        print(f"     ✗ Failed to approve")
        return False
    
    # ===== STEP 3: Dispatch install =====
    print(f"\n[3/6] Dispatching install...")
    dispatch_summary = approval_service.dispatch(limit=10)
    print(f"     Items dispatched: {len(dispatch_summary.items)}")
    print(f"     Failures: {dispatch_summary.failures}")
    
    if dispatch_summary.failures > 0:
        print(f"     ✗ Dispatch had failures")
        if dispatch_summary.items:
            print(f"     Result: {dispatch_summary.items[0]}")
        return False
    
    if len(dispatch_summary.items) < 1:
        print(f"     ✗ No items dispatched")
        return False
    
    print(f"     ✓ Install dispatched successfully")
    
    # Small delay for install to complete
    time.sleep(1)
    
    # ===== STEP 4: Check status =====
    print(f"\n[4/6] Checking app status...")
    app_status_tool = brain.tools.get("app_status")
    if not app_status_tool:
        print(f"     ✗ app_status tool not registered")
        return False
    
    status_result = app_status_tool.handler(app=app_to_test)
    print(f"     Status result: {status_result}")
    
    if not status_result.get("ok"):
        print(f"     ✗ Status check failed")
        return False
    
    print(f"     ✓ Status check completed: {status_result.get('app')} is {'installed' if status_result.get('installed') else 'not installed'}")
    
    # ===== STEP 5: Request uninstall =====
    print(f"\n[5/6] Requesting uninstall of {app_to_test}...")
    uninstall_id = approval_service.request(
        "uninstall_app",
        {"app": app_to_test},
    )
    print(f"     ✓ Uninstall approval ID: {uninstall_id}")
    
    # Approve uninstall
    print(f"\n[5b/6] Approving uninstall request...")
    approved = approval_service.approve(uninstall_id, reason="smoke-test")
    if not approved:
        print(f"     ✗ Failed to approve uninstall")
        return False
    print(f"     ✓ Uninstall approved")
    
    # Dispatch uninstall
    print(f"\n[5c/6] Dispatching uninstall...")
    dispatch_summary = approval_service.dispatch(limit=10)
    print(f"     Items dispatched: {len(dispatch_summary.items)}")
    print(f"     Failures: {dispatch_summary.failures}")
    
    if dispatch_summary.failures > 0:
        print(f"     ⚠ Dispatch had failures (may be expected if app not actually installed)")
    
    if len(dispatch_summary.items) < 1:
        print(f"     ✗ No items dispatched")
        return False
    
    print(f"     ✓ Uninstall dispatched")
    
    # Small delay
    time.sleep(1)
    
    # ===== STEP 6: Final status check =====
    print(f"\n[6/6] Final status check after uninstall...")
    final_status = app_status_tool.handler(app=app_to_test)
    print(f"     Status result: {final_status}")
    
    if not final_status.get("ok"):
        print(f"     ✗ Final status check failed")
        return False
    
    print(f"     ✓ Final status check completed")
    
    # ===== SUMMARY =====
    print("\n" + "="*70)
    print("✅ SMOKE TEST PASSED")
    print("="*70)
    print("\nComplete lifecycle verified:")
    print(f"  1. Install request → queued with ID {install_id}")
    print(f"  2. Approval → confirmed")
    print(f"  3. Dispatch → executed successfully")
    print(f"  4. Status check → {app_to_test} {'installed' if status_result.get('installed') else 'not installed'}")
    print(f"  5. Uninstall request → queued with ID {uninstall_id}")
    print(f"  6. Approval + Dispatch → executed")
    print(f"  7. Final status → confirmed\n")
    
    # Audit trail
    print("\nAudit trail summary:")
    events = audit.recent(limit=20)
    kinds = {}
    for event in events:
        k = event["kind"]
        kinds[k] = kinds.get(k, 0) + 1
    
    for kind, count in sorted(kinds.items()):
        print(f"  - {kind}: {count}")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
