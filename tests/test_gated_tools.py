from jarvis.tools.gated import call_phone, payments, trade


def test_gated_tools_are_marked_gated():
    assert payments.tier == "gated"
    assert trade.tier == "gated"
    assert call_phone.tier == "gated"


def test_gated_stub_returns_not_implemented_payload():
    result = payments.handler(merchant="Cafe", amount_eur=12.5, reason="Lunch")

    assert result["status"] == "not_implemented"
    assert result["tool"] == "payments"
    assert result["required_phase"] == "payments"
    assert "scaffolded" in result["message"]
