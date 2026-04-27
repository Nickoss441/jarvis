"""Home Assistant read + non-critical write scaffold.

Supports three actions:
  * get_state    — read a single entity's current state
  * list_states  — list all entities, optionally filtered by domain prefix
  * call_service — call an HA service (e.g. light.turn_on)

Critical-entity writes (locks, alarm, garage, oven) are blocked upstream by
``Policy.check_tool`` before this handler is ever invoked.

Modes
-----
``dry_run`` (default) — no network calls; returns simulated realistic responses.
``live``              — calls the HA REST API via httpx.

Phase gate
----------
Register only when ``config.phase_smart_home`` is True.
"""
import time
import uuid
from typing import Any, Callable

from . import Tool

_ALLOWED_ACTIONS = {"get_state", "list_states", "call_service"}

# ── dry-run stub data ──────────────────────────────────────────────────────────

_STUB_STATES: list[dict[str, Any]] = [
    {
        "entity_id": "light.living_room",
        "state": "on",
        "attributes": {"brightness": 180, "friendly_name": "Living Room Light"},
        "last_changed": "2026-04-26T08:00:00+00:00",
        "last_updated": "2026-04-26T08:00:00+00:00",
    },
    {
        "entity_id": "switch.office_fan",
        "state": "off",
        "attributes": {"friendly_name": "Office Fan"},
        "last_changed": "2026-04-26T07:30:00+00:00",
        "last_updated": "2026-04-26T07:30:00+00:00",
    },
    {
        "entity_id": "sensor.bedroom_temperature",
        "state": "21.3",
        "attributes": {"unit_of_measurement": "°C", "friendly_name": "Bedroom Temperature"},
        "last_changed": "2026-04-26T09:10:00+00:00",
        "last_updated": "2026-04-26T09:10:00+00:00",
    },
    {
        "entity_id": "binary_sensor.front_door",
        "state": "off",
        "attributes": {"device_class": "door", "friendly_name": "Front Door"},
        "last_changed": "2026-04-26T06:00:00+00:00",
        "last_updated": "2026-04-26T06:00:00+00:00",
    },
]


def _stub_get_state(entity_id: str) -> dict[str, Any]:
    for s in _STUB_STATES:
        if s["entity_id"] == entity_id:
            return {"mode": "dry_run", "entity": s}
    return {
        "mode": "dry_run",
        "entity_id": entity_id,
        "state": "unknown",
        "attributes": {},
        "note": "entity not in dry-run stub data",
    }


def _stub_list_states(domain: str | None) -> dict[str, Any]:
    states = _STUB_STATES
    if domain:
        prefix = domain.rstrip(".") + "."
        states = [s for s in states if s["entity_id"].startswith(prefix)]
    return {
        "mode": "dry_run",
        "count": len(states),
        "entities": states,
    }


def _stub_call_service(
    domain: str,
    service: str,
    entity_id: str,
    service_data: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "mode": "dry_run",
        "action": "call_service",
        "domain": domain,
        "service": service,
        "entity_id": entity_id,
        "service_data": service_data or {},
        "call_id": str(uuid.uuid4()),
        "ts": time.time(),
        "result": "simulated_ok",
    }


# ── live helpers ───────────────────────────────────────────────────────────────

def _live_get_state(
    ha_url: str,
    token: str,
    entity_id: str,
    timeout: int,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not installed. pip install httpx"}

    url = f"{ha_url.rstrip('/')}/api/states/{entity_id}"
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=float(timeout),
        )
        resp.raise_for_status()
        return {"entity": resp.json()}
    except Exception as exc:
        return {"error": f"HA request failed: {exc}"}


def _live_list_states(
    ha_url: str,
    token: str,
    domain: str | None,
    timeout: int,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not installed. pip install httpx"}

    url = f"{ha_url.rstrip('/')}/api/states"
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=float(timeout),
        )
        resp.raise_for_status()
        entities = resp.json()
    except Exception as exc:
        return {"error": f"HA request failed: {exc}"}

    if domain:
        prefix = domain.rstrip(".") + "."
        entities = [e for e in entities if e.get("entity_id", "").startswith(prefix)]

    return {"count": len(entities), "entities": entities}


def _live_call_service(
    ha_url: str,
    token: str,
    domain: str,
    service: str,
    entity_id: str,
    service_data: dict[str, Any] | None,
    timeout: int,
) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not installed. pip install httpx"}

    url = f"{ha_url.rstrip('/')}/api/services/{domain}/{service}"
    body: dict[str, Any] = {"entity_id": entity_id}
    if service_data:
        body.update(service_data)

    try:
        resp = httpx.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=float(timeout),
        )
        resp.raise_for_status()
        return {
            "action": "call_service",
            "domain": domain,
            "service": service,
            "entity_id": entity_id,
            "result": "ok",
        }
    except Exception as exc:
        return {"error": f"HA request failed: {exc}"}


# ── tool factory ───────────────────────────────────────────────────────────────

def make_home_assistant_tool(
    ha_url: str,
    ha_token_getter: Callable[[], str],
    mode: str = "dry_run",
    timeout_seconds: int = 10,
) -> Tool:
    """Build the home_assistant Tool.

    Parameters
    ----------
    ha_url:
        Base URL of the Home Assistant instance (e.g. ``http://homeassistant.local:8123``).
    ha_token_getter:
        Zero-argument callable that returns the long-lived access token.  Called
        at request time so the secret is never captured at build time.
    mode:
        ``"dry_run"`` (default) or ``"live"``.
    timeout_seconds:
        HTTP timeout for live requests.
    """
    mode = (mode or "dry_run").strip().lower()

    def _handler(
        action: str,
        entity_id: str = "",
        domain: str = "",
        service: str = "",
        service_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        action = (action or "").strip().lower()

        if action not in _ALLOWED_ACTIONS:
            return {
                "error": (
                    f"unknown action '{action}'. "
                    "allowed: " + ", ".join(sorted(_ALLOWED_ACTIONS))
                )
            }

        # ── get_state ──────────────────────────────────────────────────────────
        if action == "get_state":
            if not entity_id.strip():
                return {"error": "entity_id is required for get_state"}
            if mode != "live":
                return _stub_get_state(entity_id.strip())
            return _live_get_state(ha_url, ha_token_getter(), entity_id.strip(), timeout_seconds)

        # ── list_states ────────────────────────────────────────────────────────
        if action == "list_states":
            domain_filter = domain.strip() if domain else None
            if mode != "live":
                return _stub_list_states(domain_filter)
            return _live_list_states(ha_url, ha_token_getter(), domain_filter, timeout_seconds)

        # ── call_service ───────────────────────────────────────────────────────
        # action == "call_service"
        domain_norm = domain.strip().lower()
        service_norm = service.strip().lower()
        entity_id_norm = entity_id.strip()

        if not domain_norm:
            return {"error": "domain is required for call_service"}
        if not service_norm:
            return {"error": "service is required for call_service"}
        if not entity_id_norm:
            return {"error": "entity_id is required for call_service"}

        if mode != "live":
            return _stub_call_service(domain_norm, service_norm, entity_id_norm, service_data)
        return _live_call_service(
            ha_url,
            ha_token_getter(),
            domain_norm,
            service_norm,
            entity_id_norm,
            service_data,
            timeout_seconds,
        )

    return Tool(
        name="home_assistant",
        description=(
            "Control and query Home Assistant. "
            "Use get_state to read an entity, list_states to browse entities "
            "(optionally filter by domain), and call_service to send a command "
            "(e.g. turn lights on/off). "
            "Critical entities (locks, alarm, garage, oven) are policy-blocked."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_state", "list_states", "call_service"],
                    "description": "Operation to perform.",
                },
                "entity_id": {
                    "type": "string",
                    "description": (
                        "Target entity ID (e.g. 'light.living_room'). "
                        "Required for get_state and call_service."
                    ),
                },
                "domain": {
                    "type": "string",
                    "description": (
                        "Entity domain for list_states filter (e.g. 'light') "
                        "or service domain for call_service (e.g. 'light')."
                    ),
                },
                "service": {
                    "type": "string",
                    "description": (
                        "Service name for call_service (e.g. 'turn_on', 'turn_off')."
                    ),
                },
                "service_data": {
                    "type": "object",
                    "description": (
                        "Extra payload for call_service (e.g. {\"brightness\": 200})."
                    ),
                },
            },
            "required": ["action"],
        },
        handler=_handler,
        tier="open",
    )
