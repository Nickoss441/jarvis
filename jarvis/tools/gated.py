"""Gated tool stubs for future phases.

These tools are intentionally non-operational in current scaffolding.
They return explicit status payloads until each integration is implemented.
"""
from typing import Any

from . import Tool


def _stub(name: str, required_phase: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "tool": name,
        "required_phase": required_phase,
        "message": (
            f"'{name}' is scaffolded but not implemented yet. "
            f"Enable phase '{required_phase}' and wire the provider integration."
        ),
        "received": args,
    }


payments = Tool(
    name="payments",
    description=(
        "Prepare and execute a payment proposal through an approval workflow."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "merchant": {"type": "string"},
            "amount_eur": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["merchant", "amount_eur", "reason"],
    },
    handler=lambda **kwargs: _stub("payments", "payments", kwargs),
    tier="gated",
)


trade = Tool(
    name="trade",
    description="Propose or execute a broker trade order through policy + approval.",
    input_schema={
        "type": "object",
        "properties": {
            "instrument": {"type": "string"},
            "side": {"type": "string", "enum": ["buy", "sell"]},
            "size": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["instrument", "side", "size", "reason"],
    },
    handler=lambda **kwargs: _stub("trade", "trading", kwargs),
    tier="gated",
)


call_phone = Tool(
    name="call_phone",
    description=(
        "Place an outbound phone call with mandatory AI disclosure and logging."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "phone_number": {"type": "string"},
            "purpose": {"type": "string"},
            "script_preview": {"type": "string"},
        },
        "required": ["phone_number", "purpose"],
    },
    handler=lambda **kwargs: _stub("call_phone", "telephony", kwargs),
    tier="gated",
)

