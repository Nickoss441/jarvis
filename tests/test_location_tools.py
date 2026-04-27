import json
import time

from jarvis.event_bus import EventBus
from jarvis.runtime import RuntimeEventEnvelope
from jarvis.tools.eta_to import make_eta_to_tool
from jarvis.tools.location_current import make_location_current_tool
from jarvis.tools.route_eta import make_route_eta_tool
from jarvis.tools.weather_here import make_weather_here_tool
from jarvis.tools.weather_now import make_weather_now_tool


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def test_weather_now_dry_run_returns_metric_snapshot():
    tool = make_weather_now_tool(mode="dry_run")

    out = tool.handler(latitude=52.3676, longitude=4.9041, units="metric")

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["units"] == "metric"
    assert "temperature_c" in out
    assert "wind_kph" in out


def test_weather_now_live_parses_open_meteo_payload(monkeypatch):
    payload = {
        "current": {
            "temperature_2m": 15.4,
            "wind_speed_10m": 22.0,
            "rain": 0.3,
            "precipitation": 0.5,
        }
    }
    monkeypatch.setattr(
        "jarvis.tools.weather_now.urllib_request.urlopen",
        lambda *_args, **_kwargs: _FakeResponse(payload),
    )

    tool = make_weather_now_tool(mode="live")
    out = tool.handler(latitude=52.3676, longitude=4.9041)

    assert out["ok"] is True
    assert out["mode"] == "live"
    assert out["provider"] == "open-meteo"
    assert out["temperature_c"] == 15.4
    assert out["wind_kph"] == 22.0


def test_route_eta_dry_run_returns_distance_and_eta():
    tool = make_route_eta_tool(mode="dry_run")

    out = tool.handler(
        origin_latitude=52.3676,
        origin_longitude=4.9041,
        destination_latitude=52.5200,
        destination_longitude=13.4050,
        transport="driving",
    )

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["distance_km"] > 0
    assert out["eta_minutes"] > 0


def test_route_eta_live_parses_osrm_payload(monkeypatch):
    payload = {"routes": [{"distance": 12500.0, "duration": 1080.0}]}
    monkeypatch.setattr(
        "jarvis.tools.route_eta.urllib_request.urlopen",
        lambda *_args, **_kwargs: _FakeResponse(payload),
    )

    tool = make_route_eta_tool(mode="live")
    out = tool.handler(
        origin_latitude=52.3676,
        origin_longitude=4.9041,
        destination_latitude=52.5200,
        destination_longitude=13.4050,
        transport="driving",
    )

    assert out["ok"] is True
    assert out["mode"] == "live"
    assert out["provider"] == "osrm"
    assert out["distance_km"] == 12.5
    assert out["eta_minutes"] == 18


def test_location_current_reports_missing_when_no_events(tmp_path):
    tool = make_location_current_tool(EventBus(tmp_path / "event-bus.db"))

    out = tool.handler()

    assert out["ok"] is False
    assert out["error"] == "no_location_data"


def test_location_current_returns_latest_coordinates(tmp_path):
    bus = EventBus(tmp_path / "event-bus.db")
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            payload={"latitude": 52.3676, "longitude": 4.9041, "accuracy_m": 8.0},
        )
    )
    tool = make_location_current_tool(bus)

    out = tool.handler(max_age_seconds=300)

    assert out["ok"] is True
    assert out["stale"] is False
    assert out["location"]["latitude"] == 52.3676
    assert out["location"]["longitude"] == 4.9041
    assert out["source"] == "ios-shortcut"


def test_weather_here_uses_latest_location(tmp_path):
    bus = EventBus(tmp_path / "event-bus.db")
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            payload={"latitude": 52.3676, "longitude": 4.9041, "accuracy_m": 8.0},
        )
    )
    tool = make_weather_here_tool(bus, mode="dry_run")

    out = tool.handler(units="metric", max_age_seconds=300)

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["origin"]["source"] == "ios-shortcut"
    assert "temperature_c" in out


def test_eta_to_uses_latest_location_as_origin(tmp_path):
    bus = EventBus(tmp_path / "event-bus.db")
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            payload={"latitude": 52.3676, "longitude": 4.9041, "accuracy_m": 8.0},
        )
    )
    tool = make_eta_to_tool(bus, mode="dry_run")

    out = tool.handler(
        destination_latitude=52.5200,
        destination_longitude=13.4050,
        transport="driving",
        max_age_seconds=300,
    )

    assert out["ok"] is True
    assert out["mode"] == "dry_run"
    assert out["origin"]["source"] == "ios-shortcut"
    assert out["eta_minutes"] > 0


def test_weather_here_fails_when_location_is_stale(tmp_path):
    bus = EventBus(tmp_path / "event-bus.db")
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            timestamp=time.time() - 10_000,
            payload={"latitude": 52.3676, "longitude": 4.9041},
        )
    )
    tool = make_weather_here_tool(bus, mode="dry_run")

    out = tool.handler(max_age_seconds=300)

    assert out["ok"] is False
    assert out["error"] == "location_stale"


def test_eta_to_fails_when_location_is_stale(tmp_path):
    bus = EventBus(tmp_path / "event-bus.db")
    bus.emit(
        RuntimeEventEnvelope(
            kind="location_update",
            source="ios-shortcut",
            timestamp=time.time() - 10_000,
            payload={"latitude": 52.3676, "longitude": 4.9041},
        )
    )
    tool = make_eta_to_tool(bus, mode="dry_run")

    out = tool.handler(
        destination_latitude=52.5200,
        destination_longitude=13.4050,
        max_age_seconds=300,
    )

    assert out["ok"] is False
    assert out["error"] == "location_stale"
