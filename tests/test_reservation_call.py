from jarvis.tools.reservation_call import make_reservation_call_tool


def test_reservation_call_tool_queues_call_phone_approval() -> None:
    captured: dict[str, object] = {}

    def _request(kind: str, payload: dict[str, object]) -> str:
        captured["kind"] = kind
        captured["payload"] = payload
        return "approval-123"

    def _get(_approval_id: str):
        return {"correlation_id": "corr-1"}

    tool = make_reservation_call_tool(
        request_approval=_request,
        get_approval=_get,
        user_name="Nick",
    )

    out = tool.handler(
        venue_name="Lupa",
        phone_number="+14155552671",
        party_size=2,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
        special_requests="window seat",
    )

    assert captured["kind"] == "call_phone"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["phone_number"] == "+14155552671"
    assert payload["subject"] == "Reservation request: Lupa"
    assert "window seat" in payload["message"]

    assert out["status"] == "pending_approval"
    assert out["approval_id"] == "approval-123"
    assert out["correlation_id"] == "corr-1"
    assert out["kind"] == "reservation_call"
    assert out["queued_kind"] == "call_phone"


def test_reservation_call_tool_validates_phone_number() -> None:
    tool = make_reservation_call_tool(request_approval=lambda _k, _p: "approval-1")

    out = tool.handler(
        venue_name="Lupa",
        phone_number="123",
        party_size=2,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
    )

    assert "E.164" in out["error"]


def test_reservation_call_tool_surfaces_booking_prompt_validation_error() -> None:
    tool = make_reservation_call_tool(request_approval=lambda _k, _p: "approval-1")

    out = tool.handler(
        venue_name="",
        phone_number="+14155552671",
        party_size=2,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
    )

    assert "venue_name" in out["error"]