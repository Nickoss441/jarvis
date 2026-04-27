from jarvis.tools.solana_helius import make_solana_helius_tools


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_solana_tx_lookup_uses_rpc_payload():
    captured = {"method": None}

    def _post(_url, json, timeout):
        captured["method"] = json.get("method")
        return _Resp({"result": {"slot": 123}})

    tools = make_solana_helius_tools(api_key="k", network="mainnet", http_post=_post)
    tx_tool = next(t for t in tools if t.name == "solana_tx_lookup")

    result = tx_tool.handler(signature="abc")

    assert captured["method"] == "getTransaction"
    assert result["transaction"]["slot"] == 123


def test_solana_wallet_activity_requires_key():
    tools = make_solana_helius_tools(api_key="", network="mainnet")
    wallet_tool = next(t for t in tools if t.name == "solana_wallet_activity")

    result = wallet_tool.handler(wallet="w")

    assert "error" in result
    assert "HELIUS_API_KEY" in result["error"]


def test_solana_wallet_activity_returns_count():
    def _post(_url, json, timeout):
        assert json.get("method") == "getSignaturesForAddress"
        return _Resp({"result": [{"signature": "s1"}, {"signature": "s2"}]})

    tools = make_solana_helius_tools(api_key="k", network="mainnet", http_post=_post)
    wallet_tool = next(t for t in tools if t.name == "solana_wallet_activity")

    result = wallet_tool.handler(wallet="wallet1", limit=2)

    assert result["count"] == 2
    assert result["activity"][0]["signature"] == "s1"


def test_solana_enhanced_tx_lookup_uses_transactions_endpoint():
    seen = {"url": None}

    def _post(url, params, json, timeout):
        seen["url"] = url
        assert "api-key" in params
        assert json["transactions"] == ["sig1"]
        return _Resp([{"signature": "sig1", "type": "TRANSFER"}])

    tools = make_solana_helius_tools(api_key="k", network="mainnet", http_post=_post)
    tool = next(t for t in tools if t.name == "solana_enhanced_tx_lookup")

    result = tool.handler(signature="sig1")

    assert seen["url"].endswith("/transactions")
    assert result["count"] == 1
    assert result["transactions"][0]["signature"] == "sig1"


def test_solana_enhanced_address_transactions_uses_address_endpoint():
    seen = {"url": None, "params": None}

    def _get(url, params, timeout):
        seen["url"] = url
        seen["params"] = params
        return _Resp([{"signature": "sigA"}])

    tools = make_solana_helius_tools(api_key="k", network="mainnet", http_get=_get)
    tool = next(t for t in tools if t.name == "solana_enhanced_address_transactions")

    result = tool.handler(address="walletA", limit=5)

    assert "/addresses/walletA/transactions" in seen["url"]
    assert seen["params"]["limit"] == 5
    assert "api-key" in seen["params"]
    assert result["count"] == 1
    assert result["transactions"][0]["signature"] == "sigA"


def test_solana_tools_use_api_key_getter_at_call_time():
    keybox = {"key": "k1"}
    seen = {"url": None}

    def _post(url, json, timeout):
        seen["url"] = url
        return _Resp({"result": {"slot": 123}})

    tools = make_solana_helius_tools(
        api_key="",
        network="mainnet",
        api_key_getter=lambda: keybox["key"],
        http_post=_post,
    )
    tx_tool = next(t for t in tools if t.name == "solana_tx_lookup")

    tx_tool.handler(signature="abc")
    assert "api-key=k1" in (seen["url"] or "")

    keybox["key"] = "k2"
    tx_tool.handler(signature="abc")
    assert "api-key=k2" in (seen["url"] or "")
