from jarvis.booking_prompt import build_outbound_booking_prompt


def test_build_outbound_booking_prompt_requires_venue_name() -> None:
    out = build_outbound_booking_prompt(
        venue_name="",
        party_size=2,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
    )

    assert out["ok"] is False
    assert "venue_name" in out["error"]


def test_build_outbound_booking_prompt_requires_positive_party_size() -> None:
    out = build_outbound_booking_prompt(
        venue_name="Lupa",
        party_size=0,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
    )

    assert out["ok"] is False
    assert "party_size" in out["error"]


def test_build_outbound_booking_prompt_generates_disclosure_first_script() -> None:
    out = build_outbound_booking_prompt(
        venue_name="Lupa",
        party_size=2,
        date_label="Saturday",
        time_label="7:00 PM",
        contact_name="Nick",
        callback_number="+14155552671",
        user_name="Nickos",
        special_requests="window seat",
    )

    assert out["ok"] is True
    assert out["subject"] == "Reservation request: Lupa"
    assert out["script"].splitlines()[0] == out["disclosure"]
    assert "book a table at Lupa" in out["disclosure"]
    assert "Special requests: window seat." in out["script"]
    assert out["call_payload"]["message"] == out["script"]
