from jarvis.perception.monitors.helius_wallet import HeliusWalletMonitor


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_wallet_monitor_emits_new_events_only():
    calls = {"n": 0}

    def _post(_url, json, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp({"result": [{"signature": "b"}, {"signature": "a"}]})
        return _Resp({"result": [{"signature": "c"}, {"signature": "b"}]})

    mon = HeliusWalletMonitor(api_key="k", http_post=_post)

    first = mon.poll_once("wallet1")
    second = mon.poll_once("wallet1")

    assert first["count"] == 2
    assert [e["signature"] for e in first["events"]] == ["a", "b"]
    assert second["count"] == 1
    assert second["events"][0]["signature"] == "c"


def test_wallet_monitor_requires_key():
    mon = HeliusWalletMonitor(api_key="")

    out = mon.poll_once("wallet1")

    assert "error" in out
    assert "HELIUS_API_KEY" in out["error"]
