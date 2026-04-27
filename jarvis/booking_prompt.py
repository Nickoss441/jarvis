"""Outbound booking prompt builder.

Produces a deterministic, disclosure-first phone script for reservation calls.
"""

from typing import Any

from .tools.call_phone import build_call_disclosure, inject_disclosure_first_line


def build_outbound_booking_prompt(
    *,
    venue_name: str,
    party_size: int,
    date_label: str,
    time_label: str,
    contact_name: str,
    callback_number: str,
    user_name: str | None = None,
    special_requests: str | None = None,
) -> dict[str, Any]:
    """Build a structured outbound booking call script.

    The returned payload is intended for telephony tools and approval previews.
    """

    venue = (venue_name or "").strip()
    name = (contact_name or "").strip()
    callback = (callback_number or "").strip()
    date_value = (date_label or "").strip()
    time_value = (time_label or "").strip()

    if not venue:
        return {"ok": False, "error": "venue_name is required"}
    if int(party_size) <= 0:
        return {"ok": False, "error": "party_size must be a positive integer"}
    if not name:
        return {"ok": False, "error": "contact_name is required"}
    if not callback:
        return {"ok": False, "error": "callback_number is required"}
    if not date_value:
        return {"ok": False, "error": "date_label is required"}
    if not time_value:
        return {"ok": False, "error": "time_label is required"}

    purpose = f"book a table at {venue}"
    disclosure = build_call_disclosure(user_name=user_name, purpose=purpose)

    body_lines = [
        f"Hi, I'd like to book a table for {int(party_size)} on {date_value} at {time_value}.",
        f"The reservation name is {name} and callback number is {callback}.",
        "Please confirm availability and whether a deposit is required.",
    ]

    request_notes = (special_requests or "").strip()
    if request_notes:
        body_lines.append(f"Special requests: {request_notes}.")

    body_lines.append(
        "If a deposit is required, hold the reservation while I confirm payment authorization."
    )

    script = inject_disclosure_first_line(
        message="\n".join(body_lines),
        disclosure=disclosure,
    )

    return {
        "ok": True,
        "purpose": purpose,
        "subject": f"Reservation request: {venue}",
        "disclosure": disclosure,
        "script": script,
        "call_payload": {
            "subject": f"Reservation request: {venue}",
            "purpose": purpose,
            "message": script,
        },
    }
