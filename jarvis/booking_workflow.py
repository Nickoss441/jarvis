"""Deterministic booking decision workflow.

This module keeps booking go/no-go logic outside LLM reasoning so future
reservation-call tools can reuse a predictable decision path.
"""

from typing import Any


def build_booking_decision(
    *,
    party_size: int,
    available: bool,
    deposit_per_person_eur: float | None = None,
    hold_minutes: int | None = None,
    budget_remaining_eur: float | None = None,
    per_transaction_limit_eur: float = 50.0,
    user_max_deposit_eur: float | None = None,
) -> dict[str, Any]:
    """Return a deterministic decision for a booking attempt.

    Actions are intentionally narrow and operational:
    - ``defer`` when no inventory is available.
    - ``confirm_without_payment`` when there is no deposit requirement.
    - ``request_payment_approval`` when a deposit is needed and policy allows.
    - ``manual_split_payment`` when deposit exceeds single-transaction limit.
    - ``ask_user_budget_override`` when user-configured max deposit is exceeded.
    - ``decline_due_to_budget`` when remaining budget cannot cover the deposit.
    """

    if int(party_size) <= 0:
        return {
            "ok": False,
            "error": "party_size must be a positive integer",
        }

    if not available:
        return {
            "ok": True,
            "action": "defer",
            "requires_approval": False,
            "deposit_total_eur": 0.0,
            "next_step": "offer_alternative_times",
            "reason": "venue reports no availability",
            "hold_minutes": hold_minutes,
        }

    deposit_value = float(deposit_per_person_eur or 0.0)
    if deposit_value <= 0:
        return {
            "ok": True,
            "action": "confirm_without_payment",
            "requires_approval": False,
            "deposit_total_eur": 0.0,
            "next_step": "confirm_booking_details",
            "reason": "no deposit required",
            "hold_minutes": hold_minutes,
        }

    deposit_total = float(party_size) * deposit_value

    if user_max_deposit_eur is not None and deposit_total > float(user_max_deposit_eur):
        return {
            "ok": True,
            "action": "ask_user_budget_override",
            "requires_approval": True,
            "deposit_total_eur": deposit_total,
            "next_step": "request_explicit_budget_override",
            "reason": "deposit exceeds user max deposit preference",
            "hold_minutes": hold_minutes,
        }

    if budget_remaining_eur is not None and deposit_total > float(budget_remaining_eur):
        return {
            "ok": True,
            "action": "decline_due_to_budget",
            "requires_approval": False,
            "deposit_total_eur": deposit_total,
            "next_step": "decline_and_offer_alternative",
            "reason": "deposit exceeds remaining booking budget",
            "hold_minutes": hold_minutes,
        }

    if deposit_total > float(per_transaction_limit_eur):
        return {
            "ok": True,
            "action": "manual_split_payment",
            "requires_approval": True,
            "deposit_total_eur": deposit_total,
            "next_step": "request_manual_payment_strategy",
            "reason": "deposit exceeds per-transaction limit",
            "hold_minutes": hold_minutes,
        }

    return {
        "ok": True,
        "action": "request_payment_approval",
        "requires_approval": True,
        "deposit_total_eur": deposit_total,
        "next_step": "create_deposit_approval",
        "reason": "deposit is within policy and budget",
        "hold_minutes": hold_minutes,
    }
