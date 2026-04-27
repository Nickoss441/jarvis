"""Mac-to-PC pipeline scaffolding helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid


def build_pipeline_packet(
    *,
    command: str,
    source_id: str,
    target_id: str,
    payload: dict[str, object] | None = None,
    shared_secret: str = "",
) -> dict[str, object]:
    """Build a deterministic bridge packet with optional HMAC signature."""
    normalized_command = str(command or "").strip()
    if not normalized_command:
        raise ValueError("command is required")

    packet: dict[str, object] = {
        "packet_id": str(uuid.uuid4()),
        "ts": time.time(),
        "source_id": str(source_id or "mac").strip() or "mac",
        "target_id": str(target_id or "pc").strip() or "pc",
        "command": normalized_command,
        "payload": dict(payload or {}),
    }

    encoded = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode("utf-8")
    packet["sha256"] = hashlib.sha256(encoded).hexdigest()
    if shared_secret.strip():
        packet["signature"] = "sha256=" + hmac.new(
            shared_secret.encode("utf-8"),
            encoded,
            hashlib.sha256,
        ).hexdigest()
    else:
        packet["signature"] = ""

    return packet


def build_mac_pc_pipeline_report(
    *,
    mode: str,
    source_id: str,
    target_id: str,
    target_url: str,
    shared_secret: str,
    strict: bool = False,
) -> dict[str, object]:
    """Return setup/readiness report for cross-device bridge scaffolding."""
    normalized_mode = (mode or "dry_run").strip().lower() or "dry_run"
    packet = build_pipeline_packet(
        command="desktop_control.active_window",
        source_id=source_id,
        target_id=target_id,
        payload={"kind": "self_test"},
        shared_secret=shared_secret,
    )

    missing: list[str] = []
    if not target_url.strip():
        missing.append("target_url")
    if not shared_secret.strip():
        missing.append("shared_secret")

    strict_failure = bool(strict and missing)
    return {
        "ok": not strict_failure,
        "strict": bool(strict),
        "mode": normalized_mode,
        "source_id": source_id,
        "target_id": target_id,
        "target_url_configured": bool(target_url.strip()),
        "shared_secret_configured": bool(shared_secret.strip()),
        "packet_preview": {
            "packet_id": packet["packet_id"],
            "command": packet["command"],
            "has_signature": bool(packet.get("signature")),
            "sha256": packet["sha256"],
        },
        "missing": missing,
        **({"error": "mac_pc_pipeline_not_configured"} if strict_failure else {}),
    }
