"""Encrypted user-manifest helpers (authenticated, file-friendly envelope)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any


def _derive_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _xor_keystream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    output = bytearray(len(data))
    counter = 0
    offset = 0
    while offset < len(data):
        block = hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
        take = min(len(block), len(data) - offset)
        for idx in range(take):
            output[offset + idx] = data[offset + idx] ^ block[idx]
        offset += take
        counter += 1
    return bytes(output)


def encrypt_manifest_payload(payload: dict[str, Any], secret: str) -> dict[str, Any]:
    if not secret:
        raise ValueError("manifest secret is required")

    key = _derive_key(secret)
    nonce = secrets.token_bytes(16)
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = _xor_keystream(plaintext, key=key, nonce=nonce)
    mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()

    return {
        "version": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "mac": mac,
    }


def decrypt_manifest_payload(envelope: dict[str, Any], secret: str) -> dict[str, Any]:
    if not secret:
        raise ValueError("manifest secret is required")

    if envelope.get("version") != 1:
        raise ValueError("unsupported manifest version")

    try:
        nonce = base64.b64decode(str(envelope["nonce"]))
        ciphertext = base64.b64decode(str(envelope["ciphertext"]))
        mac = str(envelope["mac"])
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid manifest envelope") from exc

    key = _derive_key(secret)
    expected_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("manifest authentication failed")

    plaintext = _xor_keystream(ciphertext, key=key, nonce=nonce)
    try:
        decoded = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("manifest payload decode failed") from exc
    if not isinstance(decoded, dict):
        raise ValueError("manifest payload must be an object")
    return decoded


def is_encrypted_manifest_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and {
        "version",
        "nonce",
        "ciphertext",
        "mac",
    }.issubset(payload.keys())