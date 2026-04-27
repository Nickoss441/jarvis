"""GPS route ETA helper tool."""
from __future__ import annotations

import json
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from . import Tool


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def make_route_eta_tool(mode: str = "dry_run") -> Tool:
    normalized_mode = (mode or "").strip().lower() or "dry_run"

    def _handler(
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        transport: str = "driving",
    ) -> dict[str, Any]:
        transport_mode = (transport or "").strip().lower() or "driving"
        if transport_mode not in {"driving", "walking", "cycling"}:
            return {"error": "transport must be one of: driving, walking, cycling"}

        o_lat = float(origin_latitude)
        o_lon = float(origin_longitude)
        d_lat = float(destination_latitude)
        d_lon = float(destination_longitude)

        for label, value, low, high in (
            ("origin_latitude", o_lat, -90.0, 90.0),
            ("origin_longitude", o_lon, -180.0, 180.0),
            ("destination_latitude", d_lat, -90.0, 90.0),
            ("destination_longitude", d_lon, -180.0, 180.0),
        ):
            if not (low <= value <= high):
                return {"error": f"{label} out of range"}

        if normalized_mode != "live":
            km = _haversine_km(o_lat, o_lon, d_lat, d_lon)
            speed_kph = {"driving": 45.0, "cycling": 16.0, "walking": 5.0}[transport_mode]
            eta_minutes = round((km / speed_kph) * 60.0)
            return {
                "ok": True,
                "mode": "dry_run",
                "transport": transport_mode,
                "distance_km": round(km, 2),
                "eta_minutes": int(max(1, eta_minutes)),
                "summary": "dry-run ETA estimate",
            }

        profile = {
            "driving": "driving",
            "walking": "foot",
            "cycling": "bike",
        }[transport_mode]
        base_url = (
            "https://router.project-osrm.org/route/v1/"
            f"{profile}/{o_lon},{o_lat};{d_lon},{d_lat}"
        )
        query = urllib_parse.urlencode({"overview": "false", "alternatives": "false", "steps": "false"})
        url = f"{base_url}?{query}"

        try:
            with urllib_request.urlopen(url, timeout=10.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "mode": "live", "error": f"route lookup failed: {exc}"}

        routes = payload.get("routes", [])
        if not routes:
            return {"ok": False, "mode": "live", "error": "no route found"}

        route = routes[0]
        distance_m = float(route.get("distance", 0.0))
        duration_s = float(route.get("duration", 0.0))

        return {
            "ok": True,
            "mode": "live",
            "provider": "osrm",
            "transport": transport_mode,
            "distance_km": round(distance_m / 1000.0, 2),
            "duration_seconds": int(duration_s),
            "eta_minutes": int(max(1, round(duration_s / 60.0))),
            "summary": "live route ETA",
        }

    return Tool(
        name="route_eta",
        description=(
            "Estimate route distance and ETA between origin and destination GPS coordinates "
            "for driving, walking, or cycling."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "origin_latitude": {"type": "number"},
                "origin_longitude": {"type": "number"},
                "destination_latitude": {"type": "number"},
                "destination_longitude": {"type": "number"},
                "transport": {
                    "type": "string",
                    "enum": ["driving", "walking", "cycling"],
                    "default": "driving",
                },
            },
            "required": [
                "origin_latitude",
                "origin_longitude",
                "destination_latitude",
                "destination_longitude",
            ],
        },
        handler=_handler,
        tier="open",
    )
