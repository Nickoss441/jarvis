"""Reservation-call wrapper over call_phone approval flow."""
from __future__ import annotations

from typing import Any, Callable

from ..booking_prompt import build_outbound_booking_prompt
from . import Tool


def make_reservation_call_tool(
    request_approval: Callable[[str, dict[str, Any]], str],
    get_approval: Callable[[str], dict[str, Any] | None] | None = None,
    user_name: str | None = None,
) -> Tool:
    """Create a reservation-focused calling tool with approval gating."""

    def _handler(
        venue_name: str,
        phone_number: str,
        party_size: int,
        date_label: str,
        time_label: str,
        contact_name: str,
        callback_number: str,
        special_requests: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        destination = (phone_number or "").strip()
        if not destination:
            return {"error": "phone_number is required"}
        if not destination.startswith("+") or len(destination) < 10:
            return {"error": "phone_number must be in E.164 format (e.g., +14155552671)"}

        prompt = build_outbound_booking_prompt(
            venue_name=venue_name,
            party_size=party_size,
            date_label=date_label,
            time_label=time_label,
            contact_name=contact_name,
            callback_number=callback_number,
            user_name=user_name,
            special_requests=special_requests,
        )
        if not prompt.get("ok"):
            return {"error": str(prompt.get("error") or "failed to build reservation prompt")}

        approval_id = request_approval(
            "call_phone",
            {
                "phone_number": destination,
                "subject": str(prompt.get("subject") or ""),
                "purpose": str(prompt.get("purpose") or ""),
                "message": str(prompt.get("script") or ""),
            },
        )
        approval = get_approval(approval_id) if get_approval else None

        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "correlation_id": approval["correlation_id"] if approval else "",
            "kind": "reservation_call",
            "queued_kind": "call_phone",
            "venue_name": venue_name,
            "disclosure_preview": str(prompt.get("disclosure") or ""),
            "script_preview": str(prompt.get("script") or ""),
            "message": "reservation call queued for approval",
        }

    return Tool(
        name="reservation_call",
        description=(
            "Create a reservation phone-call script and queue it as a call_phone approval. "
            "Use for booking restaurants or similar venues with disclosure-first outbound calls."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "venue_name": {"type": "string"},
                "phone_number": {
                    "type": "string",
                    "description": "Venue phone in E.164 format (e.g., +14155552671)",
                },
                "party_size": {"type": "integer", "minimum": 1},
                "date_label": {"type": "string"},
                "time_label": {"type": "string"},
                "contact_name": {"type": "string"},
                "callback_number": {"type": "string"},
                "special_requests": {"type": "string"},
            },
            "required": [
                "venue_name",
                "phone_number",
                "party_size",
                "date_label",
                "time_label",
                "contact_name",
                "callback_number",
            ],
        },
        handler=_handler,
        tier="gated",
    )