"""Wallet-activity monitor scaffold backed by Helius RPC."""
from typing import Any, Callable

from ...integrations.helius import build_helius_rpc_url, fetch_wallet_activity


class HeliusWalletMonitor:
    """Poll-based monitor that emits newly seen wallet signatures."""

    def __init__(
        self,
        api_key: str,
        network: str = "mainnet",
        http_post: Callable[..., Any] | None = None,
    ):
        self.api_key = api_key
        self.network = network
        self.http_post = http_post
        self._last_seen: dict[str, str] = {}

    def poll_once(self, wallet: str, limit: int = 20) -> dict[str, Any]:
        if not self.api_key:
            return {"error": "HELIUS_API_KEY is not configured"}
        rpc_url = build_helius_rpc_url(self.api_key, self.network)
        out = fetch_wallet_activity(rpc_url, wallet, limit=limit, http_post=self.http_post)
        if "error" in out:
            return out

        rows = out.get("result") or []
        last = self._last_seen.get(wallet)
        fresh = []
        for row in rows:
            sig = row.get("signature")
            if not sig:
                continue
            if sig == last:
                break
            fresh.append(row)

        if rows:
            newest = rows[0].get("signature")
            if newest:
                self._last_seen[wallet] = newest

        fresh.reverse()
        events = [
            {
                "type": "wallet_activity",
                "wallet": wallet,
                "network": self.network,
                "signature": r.get("signature"),
                "slot": r.get("slot"),
                "err": r.get("err"),
                "memo": r.get("memo"),
                "block_time": r.get("blockTime"),
            }
            for r in fresh
        ]
        return {"wallet": wallet, "events": events, "count": len(events)}
