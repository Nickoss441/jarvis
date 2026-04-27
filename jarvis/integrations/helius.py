"""Helius/Solana RPC helpers used by tools and monitors."""
from typing import Any, Callable

import httpx


def _redact_sensitive_error_text(text: str) -> str:
    redacted = text
    marker = "api-key="
    while marker in redacted:
        start = redacted.index(marker) + len(marker)
        end = start
        while end < len(redacted) and redacted[end] not in "& \"'\\n\\r":
            end += 1
        redacted = redacted[:start] + "[REDACTED]" + redacted[end:]
    return redacted


def _safe_error_message(e: Exception) -> str:
    return _redact_sensitive_error_text(f"{e.__class__.__name__}: {e}")


def build_helius_rpc_url(api_key: str, network: str = "mainnet") -> str:
    """Return a Helius RPC URL for the requested Solana network."""
    network_normalized = (network or "mainnet").strip().lower()
    if network_normalized in {"mainnet", "mainnet-beta", "mainnetbeta"}:
        host = "mainnet.helius-rpc.com"
    elif network_normalized in {"devnet"}:
        host = "devnet.helius-rpc.com"
    else:
        host = "mainnet.helius-rpc.com"
    return f"https://{host}/?api-key={api_key}"


def build_helius_enhanced_base_url(network: str = "mainnet") -> str:
    network_normalized = (network or "mainnet").strip().lower()
    if network_normalized in {"mainnet", "mainnet-beta", "mainnetbeta"}:
        return "https://api-mainnet.helius-rpc.com/v0"
    if network_normalized in {"devnet"}:
        return "https://api-devnet.helius-rpc.com/v0"
    return "https://api-mainnet.helius-rpc.com/v0"


def rpc_request(
    rpc_url: str,
    method: str,
    params: list[Any],
    http_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    post = http_post or httpx.post
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    try:
        resp = post(rpc_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"helius request failed: {_safe_error_message(e)}"}

    if isinstance(data, dict) and data.get("error"):
        return {"error": f"helius rpc error: {data['error']}"}

    return {"result": data.get("result") if isinstance(data, dict) else data}


def enhanced_get(
    base_url: str,
    path: str,
    api_key: str,
    params: dict[str, Any] | None = None,
    http_get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    get = http_get or httpx.get
    query = dict(params or {})
    query["api-key"] = api_key
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        resp = get(url, params=query, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"helius enhanced request failed: {_safe_error_message(e)}"}
    return {"result": data}


def fetch_enhanced_transactions_by_signatures(
    base_url: str,
    api_key: str,
    signatures: list[str],
    http_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    post = http_post or httpx.post
    url = f"{base_url.rstrip('/')}/transactions"
    query = {"api-key": api_key}
    try:
        resp = post(url, params=query, json={"transactions": signatures}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"helius enhanced request failed: {_safe_error_message(e)}"}
    return {"result": data}


def fetch_enhanced_address_transactions(
    base_url: str,
    api_key: str,
    address: str,
    limit: int = 10,
    before: str | None = None,
    http_get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
    if before:
        params["before"] = before
    return enhanced_get(
        base_url,
        f"addresses/{address}/transactions",
        api_key=api_key,
        params=params,
        http_get=http_get,
    )


def fetch_transaction(
    rpc_url: str,
    signature: str,
    http_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    return rpc_request(
        rpc_url,
        "getTransaction",
        [signature, {"maxSupportedTransactionVersion": 0, "encoding": "json"}],
        http_post=http_post,
    )


def fetch_wallet_activity(
    rpc_url: str,
    wallet: str,
    limit: int = 10,
    http_post: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    return rpc_request(
        rpc_url,
        "getSignaturesForAddress",
        [wallet, {"limit": max(1, min(limit, 100))}],
        http_post=http_post,
    )
