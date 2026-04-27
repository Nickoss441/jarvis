"""Latest known location helper for GPS-aware assistant behavior."""
from __future__ import annotations

import time
from typing import Any

from ..event_bus import EventBus
from . import Tool


def make_location_current_tool(event_bus: EventBus) -> Tool:
    def handler(max_age_seconds: float | None = None) -> dict[str, Any]:
        rows = event_bus.recent(limit=50, kind="location_update")
        if not rows:
            return {
                "ok": False,
                "error": "no_location_data",
                "message": "No location updates available yet.",
            }

        latest = rows[0]
        payload = latest.payload if isinstance(latest.payload, dict) else {}
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return {
                "ok": False,
                "error": "invalid_location_payload",
                "message": "Latest location payload is missing latitude/longitude.",
            }

        age_seconds = max(0.0, float(time.time() - latest.timestamp))
        stale = False
        if max_age_seconds is not None:
            try:
                threshold = float(max_age_seconds)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid_max_age_seconds"}
            if threshold < 0:
                return {"ok": False, "error": "invalid_max_age_seconds"}
            stale = age_seconds > threshold

        return {
            "ok": True,
            "stale": stale,
            "location": {
                "latitude": float(lat),
                "longitude": float(lon),
                "accuracy_m": payload.get("accuracy_m"),
            },
            "source": latest.source,
            "event_id": latest.id,
            "timestamp": latest.timestamp,
            "age_seconds": round(age_seconds, 3),
        }

    return Tool(
        name="location_current",
        description=(
            "Return the latest known GPS location from local location updates. "
            "Useful before route_eta and weather_now calls."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "max_age_seconds": {
                    "type": "number",
                    "description": "Optional freshness threshold for location staleness.",
                }
            },
        },
        handler=handler,
        tier="open",
    )
