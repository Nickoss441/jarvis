"""Solana tools powered by Helius RPC."""
from typing import Any, Callable

from ..integrations.helius import (
    build_helius_enhanced_base_url,
    build_helius_rpc_url,
    fetch_enhanced_address_transactions,
    fetch_enhanced_transactions_by_signatures,
    fetch_transaction,
    fetch_wallet_activity,
)
from . import Tool


def make_solana_helius_tools(
    api_key: str,
    network: str,
    api_key_getter: Callable[[], str] | None = None,
    http_post: Callable[..., Any] | None = None,
    http_get: Callable[..., Any] | None = None,
) -> list[Tool]:
    enhanced_base_url = build_helius_enhanced_base_url(network)

    def _current_api_key() -> str:
        if api_key_getter is not None:
            return (api_key_getter() or "").strip()
        return (api_key or "").strip()

    def _tx_lookup(signature: str) -> dict[str, Any]:
        key = _current_api_key()
        rpc_url = build_helius_rpc_url(key, network) if key else ""
        if not rpc_url:
            return {"error": "HELIUS_API_KEY is not configured"}
        if not signature.strip():
            return {"error": "signature is required"}
        out = fetch_transaction(rpc_url, signature, http_post=http_post)
        if "error" in out:
            return out
        return {
            "network": network,
            "signature": signature,
            "transaction": out.get("result"),
        }

    def _wallet_activity(wallet: str, limit: int = 10) -> dict[str, Any]:
        key = _current_api_key()
        rpc_url = build_helius_rpc_url(key, network) if key else ""
        if not rpc_url:
            return {"error": "HELIUS_API_KEY is not configured"}
        if not wallet.strip():
            return {"error": "wallet is required"}
        out = fetch_wallet_activity(rpc_url, wallet, limit=limit, http_post=http_post)
        if "error" in out:
            return out
        return {
            "network": network,
            "wallet": wallet,
            "count": len(out.get("result") or []),
            "activity": out.get("result") or [],
        }

    def _enhanced_tx_lookup(signature: str) -> dict[str, Any]:
        key = _current_api_key()
        if not key:
            return {"error": "HELIUS_API_KEY is not configured"}
        if not signature.strip():
            return {"error": "signature is required"}
        out = fetch_enhanced_transactions_by_signatures(
            enhanced_base_url,
            api_key=key,
            signatures=[signature],
            http_post=http_post,
        )
        if "error" in out:
            return out
        rows = out.get("result") or []
        return {
            "network": network,
            "signature": signature,
            "count": len(rows),
            "transactions": rows,
        }

    def _enhanced_address_txs(
        address: str,
        limit: int = 10,
        before: str | None = None,
    ) -> dict[str, Any]:
        key = _current_api_key()
        if not key:
            return {"error": "HELIUS_API_KEY is not configured"}
        if not address.strip():
            return {"error": "address is required"}
        out = fetch_enhanced_address_transactions(
            enhanced_base_url,
            api_key=key,
            address=address,
            limit=limit,
            before=before,
            http_get=http_get,
        )
        if "error" in out:
            return out
        rows = out.get("result") or []
        return {
            "network": network,
            "address": address,
            "count": len(rows),
            "transactions": rows,
        }

    return [
        Tool(
            name="solana_tx_lookup",
            description="Lookup a Solana transaction by signature using Helius RPC.",
            input_schema={
                "type": "object",
                "properties": {
                    "signature": {"type": "string", "description": "Transaction signature"}
                },
                "required": ["signature"],
            },
            handler=_tx_lookup,
            tier="open",
        ),
        Tool(
            name="solana_wallet_activity",
            description="Fetch recent transaction signatures for a Solana wallet address.",
            input_schema={
                "type": "object",
                "properties": {
                    "wallet": {"type": "string", "description": "Wallet public key"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["wallet"],
            },
            handler=_wallet_activity,
            tier="open",
        ),
        Tool(
            name="solana_enhanced_tx_lookup",
            description=(
                "Lookup parsed Solana transaction details via Helius Enhanced API "
                "POST /v0/transactions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "signature": {"type": "string", "description": "Transaction signature"}
                },
                "required": ["signature"],
            },
            handler=_enhanced_tx_lookup,
            tier="open",
        ),
        Tool(
            name="solana_enhanced_address_transactions",
            description=(
                "Fetch parsed transactions for an address via Helius Enhanced API "
                "GET /v0/addresses/{address}/transactions."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Wallet address"},
                    "limit": {"type": "integer", "default": 10},
                    "before": {
                        "type": "string",
                        "description": "Optional pagination signature",
                    },
                },
                "required": ["address"],
            },
            handler=_enhanced_address_txs,
            tier="open",
        ),
    ]
