"""GPS-aware weather summary tool."""
from __future__ import annotations

import json
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from . import Tool


def _dry_run_weather(latitude: float, longitude: float, units: str) -> dict[str, Any]:
    # Deterministic placeholder response for local development.
    base = (abs(latitude) + abs(longitude)) % 20
    temp_c = round(8.0 + base, 1)
    wind_kph = round(5.0 + (base / 2.0), 1)
    rain_mm = round((base % 3) * 0.2, 2)

    if units == "imperial":
        temp = round((temp_c * 9.0 / 5.0) + 32.0, 1)
        wind = round(wind_kph * 0.621371, 1)
        return {
            "ok": True,
            "mode": "dry_run",
            "location": {"latitude": latitude, "longitude": longitude},
            "units": "imperial",
            "temperature_f": temp,
            "wind_mph": wind,
            "rain_inches": round(rain_mm / 25.4, 3),
            "summary": "dry-run weather estimate",
        }

    return {
        "ok": True,
        "mode": "dry_run",
        "location": {"latitude": latitude, "longitude": longitude},
        "units": "metric",
        "temperature_c": temp_c,
        "wind_kph": wind_kph,
        "rain_mm": rain_mm,
        "summary": "dry-run weather estimate",
    }


def make_weather_now_tool(mode: str = "dry_run") -> Tool:
    normalized_mode = (mode or "").strip().lower() or "dry_run"

    def _handler(latitude: float, longitude: float, units: str = "metric") -> dict[str, Any]:
        unit = (units or "").strip().lower() or "metric"
        if unit not in {"metric", "imperial"}:
            return {"error": "units must be 'metric' or 'imperial'"}

        lat = float(latitude)
        lon = float(longitude)
        if not (-90.0 <= lat <= 90.0):
            return {"error": "latitude must be between -90 and 90"}
        if not (-180.0 <= lon <= 180.0):
            return {"error": "longitude must be between -180 and 180"}

        if normalized_mode != "live":
            return _dry_run_weather(lat, lon, unit)

        query = urllib_parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,rain,wind_speed_10m",
                "forecast_days": 1,
                "wind_speed_unit": "mph" if unit == "imperial" else "kmh",
                "temperature_unit": "fahrenheit" if unit == "imperial" else "celsius",
                "precipitation_unit": "inch" if unit == "imperial" else "mm",
            }
        )
        url = f"https://api.open-meteo.com/v1/forecast?{query}"

        try:
            with urllib_request.urlopen(url, timeout=10.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "mode": "live",
                "error": f"weather lookup failed: {exc}",
            }

        current = payload.get("current", {})
        result = {
            "ok": True,
            "mode": "live",
            "provider": "open-meteo",
            "location": {"latitude": lat, "longitude": lon},
            "units": unit,
            "rain": current.get("rain"),
            "precipitation": current.get("precipitation"),
            "summary": "live weather snapshot",
        }
        if unit == "imperial":
            result["temperature_f"] = current.get("temperature_2m")
            result["wind_mph"] = current.get("wind_speed_10m")
        else:
            result["temperature_c"] = current.get("temperature_2m")
            result["wind_kph"] = current.get("wind_speed_10m")
        return result

    return Tool(
        name="weather_now",
        description=(
            "Get current weather at GPS coordinates. Returns temperature, wind, "
            "and rain/precipitation values with metric or imperial units."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude in decimal degrees"},
                "longitude": {"type": "number", "description": "Longitude in decimal degrees"},
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "default": "metric",
                    "description": "Output units",
                },
            },
            "required": ["latitude", "longitude"],
        },
        handler=_handler,
        tier="open",
    )
