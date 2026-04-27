"""Helpers for posting camera frames to the vision listener."""

import hashlib
import hmac
import json
from typing import Any


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """Serialize JSON deterministically for signature generation."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_signature(secret: str, payload: dict[str, Any]) -> str:
    """Build X-Jarvis-Signature header value for a JSON payload."""
    body = _canonical_json(payload)
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_shortcut_template(url: str, secret: str = "") -> dict[str, Any]:
    """Return a ready-to-use request template for iPhone Shortcuts."""
    payload: dict[str, Any] = {
        "device": "rayban_meta",
        "stream": "camera",
        "frame_id": "frame-001",
        "frame_ts": "2026-04-25T12:00:00Z",
        "labels": ["person", "door"],
        "text": "Front door",
        "image_base64": "aGVsbG8=",
        "image_url": "",
    }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Event-Type": "vision.frame",
    }
    if secret:
        headers["X-Jarvis-Signature"] = build_signature(secret, payload)

    return {
        "request": {
            "url": url,
            "method": "POST",
            "headers": headers,
            "json_body": payload,
        },
        "notes": [
            "Replace json_body.image_base64 with a real base64 frame string from your iPhone shortcut.",
            "If using JARVIS_VISION_SECRET, keep X-Jarvis-Signature enabled and regenerate after body changes.",
            "Post to /frame (or any path); listener maps all paths to vision_frame.",
        ],
    }


def build_shortcut_guide(url: str, signing_enabled: bool) -> dict[str, Any]:
    """Return a step-by-step iPhone Shortcuts guide for vision uploads."""
    steps = [
        {
            "step": 1,
            "title": "Create Shortcut",
            "actions": [
                "Open the Shortcuts app and create a new shortcut named Jarvis Vision Upload.",
                "Add action: Take Photo (or Choose from Photos).",
            ],
        },
        {
            "step": 2,
            "title": "Build Request",
            "actions": [
                "Add action: Get Contents of URL.",
                f"Set URL to {url}.",
                "Set Method to POST.",
                "Set Request Body to File for direct binary upload, or Form for multipart upload.",
            ],
        },
        {
            "step": 3,
            "title": "Add Metadata Headers",
            "actions": [
                "Add headers: X-Device=iphone_camera, X-Frame-Id=<timestamp>, X-Labels=person,door, X-Text=<optional text>.",
                "Set Content-Type to image/jpeg (or image/png) when sending raw file body.",
            ],
        },
        {
            "step": 4,
            "title": "Run and Verify",
            "actions": [
                "Run the shortcut once to upload an image.",
                "In terminal: python3 -m jarvis events-process 20",
                "In terminal: python3 -m jarvis events-actions 20 vision_frame",
            ],
        },
    ]

    if signing_enabled:
        steps.insert(
            3,
            {
                "step": 4,
                "title": "Enable Signature",
                "actions": [
                    "Keep JARVIS_VISION_SECRET set on Jarvis.",
                    "Compute SHA-256 HMAC over the exact request body and set X-Jarvis-Signature=sha256=<digest>.",
                    "If body content changes, regenerate signature before sending.",
                ],
            },
        )
        # Keep step numbering human-friendly after insertion.
        for index, item in enumerate(steps, start=1):
            item["step"] = index

    return {
        "title": "iPhone Shortcuts Vision Upload Guide",
        "url": url,
        "signing_enabled": signing_enabled,
        "steps": steps,
        "tip": "Use vision-shortcut-template to generate a JSON request example.",
    }
