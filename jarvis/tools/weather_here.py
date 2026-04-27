"""Current-location weather helper built on location_current + weather_now."""
from __future__ import annotations

from typing import Any

from ..event_bus import EventBus
from . import Tool
from .location_current import make_location_current_tool
from .weather_now import make_weather_now_tool


def make_weather_here_tool(event_bus: EventBus, mode: str = "dry_run") -> Tool:
    location_tool = make_location_current_tool(event_bus)
    weather_tool = make_weather_now_tool(mode=mode)

    def _handler(units: str = "metric", max_age_seconds: float | None = None) -> dict[str, Any]:
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
        lat = coordinates.get("latitude")
        lon = coordinates.get("longitude")
        result = weather_tool.handler(latitude=lat, longitude=lon, units=units)

        if not isinstance(result, dict):
            return {"ok": False, "error": "weather_unavailable"}

        if result.get("ok") is False:
            return {
                "ok": False,
                "error": "weather_unavailable",
                "weather": result,
                "location": location,
            }

        result["origin"] = {
            "source": location.get("source"),
            "stale": location.get("stale", False),
            "event_id": location.get("event_id"),
            "age_seconds": location.get("age_seconds"),
        }
        return result

    return Tool(
        name="weather_here",
        description=(
            "Get current weather at your latest known location from location updates. "
            "Use this when coordinates are not provided explicitly."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "default": "metric",
                    "description": "Output units",
                },
                "max_age_seconds": {
                    "type": "number",
                    "description": "Optional freshness threshold for location staleness.",
                },
            },
        },
        handler=_handler,
        tier="open",
    )
