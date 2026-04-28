#!/usr/bin/env python3
"""Smoke test for Jarvis HUD endpoints and response contracts.

Checks HTML surfaces and core JSON APIs used by HUD pages.

Run with:
    python scripts/smoke_test_hud.py
    python scripts/smoke_test_hud.py --base-url http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def http_get(url: str, timeout: float = 4.0) -> tuple[int, str, dict[str, str], bytes]:
    req = urllib.request.Request(url, headers={"Accept": "*/*", "User-Agent": "jarvis-smoke/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed local URL from args
            body = resp.read()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp.reason, headers, body
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, str(exc.reason), headers, body


def require(cond: bool, ok_msg: str, fail_msg: str) -> bool:
    if cond:
        print(f"[OK] {ok_msg}")
        return True
    print(f"[FAIL] {fail_msg}")
    return False


def check_html(base_url: str, path: str, name: str) -> bool:
    status, reason, headers, body = http_get(f"{base_url}{path}")
    ctype = headers.get("content-type", "")
    text = body.decode("utf-8", errors="replace")
    ok = True
    ok &= require(status == 200, f"{name} returned HTTP 200", f"{name} returned HTTP {status} ({reason})")
    ok &= require("text/html" in ctype, f"{name} content-type is HTML", f"{name} content-type unexpected: {ctype}")
    ok &= require("<html" in text.lower(), f"{name} contains HTML markup", f"{name} body does not look like HTML")
    return ok


def check_json(base_url: str, path: str, name: str, required_keys: list[str]) -> bool:
    status, reason, headers, body = http_get(f"{base_url}{path}")
    ctype = headers.get("content-type", "")
    ok = True
    ok &= require(status == 200, f"{name} returned HTTP 200", f"{name} returned HTTP {status} ({reason})")
    ok &= require("application/json" in ctype, f"{name} content-type is JSON", f"{name} content-type unexpected: {ctype}")

    payload = None
    if ok:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            ok = require(False, "", f"{name} payload is not valid JSON") and ok

    if payload is not None:
        missing = [k for k in required_keys if k not in payload]
        ok &= require(not missing, f"{name} has required keys", f"{name} missing keys: {', '.join(missing)}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Jarvis HUD endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Jarvis base URL")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print("=" * 68)
    print("JARVIS HUD SMOKE TEST")
    print("=" * 68)
    print(f"Base URL: {base_url}")

    all_ok = True

    # HTML routes used by HUD workflows
    all_ok &= check_html(base_url, "/hud/cc", "Command Center")
    all_ok &= check_html(base_url, "/hud/react", "React HUD")
    all_ok &= check_html(base_url, "/hud/home", "Home HUD")
    all_ok &= check_html(base_url, "/hud/ops", "Ops HUD")

    # JSON routes backing HUD cards
    all_ok &= check_json(base_url, "/hud/version", "HUD version", ["version"])
    all_ok &= check_json(base_url, "/hud/contracts", "HUD contracts", ["version", "routes"])
    all_ok &= check_json(base_url, "/health", "Health", ["status", "source"])
    all_ok &= check_json(base_url, "/hud/metals", "Metals", ["gold", "silver", "source"])
    all_ok &= check_json(base_url, "/approvals/pending?limit=10", "Approvals pending", ["items"])

    print("\n" + "=" * 68)
    if all_ok:
        print("SMOKE TEST PASSED")
        print("=" * 68)
        return 0

    print("SMOKE TEST FAILED")
    print("=" * 68)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
