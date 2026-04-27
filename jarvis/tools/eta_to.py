"""Destination ETA helper built on location_current + route_eta."""
from __future__ import annotations

from typing import Any

from ..event_bus import EventBus
from . import Tool
from .location_current import make_location_current_tool
from .route_eta import make_route_eta_tool


def make_eta_to_tool(event_bus: EventBus, mode: str = "dry_run") -> Tool:
    location_tool = make_location_current_tool(event_bus)
    route_tool = make_route_eta_tool(mode=mode)

    def _handler(
        destination_latitude: float,
        destination_longitude: float,
        transport: str = "driving",
        max_age_seconds: float | None = None,
    ) -> dict[str, Any]:
        location = location_tool.handler(max_age_seconds=max_age_seconds)
        if not location.get("ok"):
            return {
                "ok": False,
                "error": "location_unavailable",
                "location": location,
            }
        if max_age_seconds is not None and bool(location.get("stale")):
            return {
                "ok": False,
                "error": "location_stale",
                "location": location,
            }

        coordinates = location.get("location", {})
        result = route_tool.handler(
            origin_latitude=coordinates.get("latitude"),
            origin_longitude=coordinates.get("longitude"),
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            transport=transport,
        )

        if not isinstance(result, dict):
            return {"ok": False, "error": "route_unavailable"}

        if result.get("ok") is False:
            return {
                "ok": False,
                "error": "route_unavailable",
                "route": result,
                "location": location,
            }

        result["origin"] = {
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
            "source": location.get("source"),
            "stale": location.get("stale", False),
            "event_id": location.get("event_id"),
            "age_seconds": location.get("age_seconds"),
        }
        return result

    return Tool(
        name="eta_to",
        description=(
            "Estimate route ETA from your latest known location to a destination. "
            "Use this when origin coordinates are not provided explicitly."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "destination_latitude": {"type": "number"},
                "destination_longitude": {"type": "number"},
                "transport": {
                    "type": "string",
                    "enum": ["driving", "walking", "cycling"],
                    "default": "driving",
                },
                "max_age_seconds": {
                    "type": "number",
                    "description": "Optional freshness threshold for location staleness.",
                },
            },
            "required": ["destination_latitude", "destination_longitude"],
        },
        handler=_handler,
        tier="open",
    )
