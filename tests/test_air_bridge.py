"""
Tests for air data service and renderer integration.
Covers state machine, data fetching, and renderer transitions.
"""
import unittest
import time
from unittest.mock import MagicMock, patch

from jarvis.air_bridge import AirBridge
from jarvis.air_data_schema import (
    AircraftDTO,
    AirStatesPayload,
    DataState,
    DataSourceMode,
)


class TestAirBridge(unittest.TestCase):
    """Test AirBridge OpenSky proxy and caching."""

    def test_mock_aircraft_generation(self):
        """Test mock data generation."""
        bridge = AirBridge(mode=DataSourceMode.MOCK)
        payload = bridge.get_all_aircraft()

        self.assertGreater(len(payload.aircraft), 0)
        self.assertEqual(payload.state, DataState.LIVE)
        for ac in payload.aircraft:
            self.assertIsNotNone(ac.id)
            self.assertIsNotNone(ac.lat)
            self.assertIsNotNone(ac.lon)

    def test_cache_ttl(self):
        """Test caching behavior."""
        bridge = AirBridge(mode=DataSourceMode.MOCK)

        # First fetch
        payload1 = bridge.get_all_aircraft()
        time1 = payload1.timestamp

        # Immediate fetch should use cache
        time.sleep(0.1)
        payload2 = bridge.get_all_aircraft()
        time2 = payload2.timestamp

        # Times should be identical (cached)
        self.assertEqual(time1, time2)

        # Wait for cache to expire
        bridge._cache_time = 0
        time.sleep(0.1)
        payload3 = bridge.get_all_aircraft()
        time3 = payload3.timestamp

        # Times should be different (cache expired)
        self.assertNotEqual(time1, time3)

    def test_fallback_on_error(self):
        """Test fallback to mock when live fails."""
        bridge = AirBridge(mode=DataSourceMode.LIVE)

        # Simulate OpenSky being unavailable
        with patch.object(bridge, "_fetch_opensky", side_effect=Exception("API Error")):
            payload = bridge.get_all_aircraft()

            # Should fall back to mock data
            self.assertGreater(len(payload.aircraft), 0)
            self.assertIn(
                payload.state, [DataState.STALE, DataState.ERROR]
            )

    def test_normalize_opensky(self):
        """Test OpenSky data normalization."""
        bridge = AirBridge(mode=DataSourceMode.LIVE)

        # Mock OpenSky response
        raw = {
            "states": [
                ["icao24_1", "callsign1", None, None, None, -74.0, 40.0, 10000, None, 200, 45.0],
                ["icao24_2", None, None, None, None, 0, 51.5, 8000, None, 150, 180.0],
                ["invalid", "bad", None, None, None, None, None, None, None, None, None],
            ]
        }

        aircraft = bridge._normalize_opensky(raw)

        # Should have 2 valid aircraft (skip invalid)
        self.assertEqual(len(aircraft), 2)
        self.assertEqual(aircraft[0].id, "icao24_1")
        self.assertEqual(aircraft[0].callsign, "callsign1")
        self.assertEqual(aircraft[0].lat, 40.0)
        self.assertEqual(aircraft[0].lon, -74.0)

    def test_get_flight_detail(self):
        """Test flight detail retrieval."""
        bridge = AirBridge()
        detail = bridge.get_flight_detail("test_id")

        self.assertIsNotNone(detail)
        self.assertEqual(detail.id, "test_id")
        self.assertIsNotNone(detail.callsign)

    def test_get_route(self):
        """Test route retrieval."""
        bridge = AirBridge()
        route = bridge.get_route("test_id")

        self.assertIsNotNone(route)
        self.assertEqual(route.id, "test_id")
        self.assertGreater(len(route.waypoints), 0)


class TestAircraftDTO(unittest.TestCase):
    """Test aircraft data transfer object."""

    def test_aircraft_creation(self):
        """Test creating valid aircraft DTO."""
        ac = AircraftDTO(
            id="ac123",
            callsign="UAL456",
            lat=35.0,
            lon=-80.0,
            alt=35000,
            velocity=450.0,
            heading=270.0,
        )

        self.assertEqual(ac.id, "ac123")
        self.assertEqual(ac.lat, 35.0)
        self.assertTrue(ac.state in [DataState.LIVE, DataState.STALE, DataState.ERROR])

    def test_aircraft_dict_conversion(self):
        """Test conversion to dict."""
        ac = AircraftDTO(
            id="ac123",
            callsign="UAL456",
            lat=35.0,
            lon=-80.0,
        )

        d = ac.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["id"], "ac123")
        self.assertEqual(d["lat"], 35.0)


class TestAirStatesPayload(unittest.TestCase):
    """Test air states response payload."""

    def test_payload_creation(self):
        """Test payload with aircraft."""
        aircraft = [
            AircraftDTO(id="ac1", lat=0, lon=0),
            AircraftDTO(id="ac2", lat=10, lon=10),
        ]

        payload = AirStatesPayload(aircraft=aircraft, state=DataState.LIVE)

        self.assertEqual(len(payload.aircraft), 2)
        self.assertEqual(payload.state, DataState.LIVE)

    def test_payload_dict_conversion(self):
        """Test payload serialization."""
        aircraft = [AircraftDTO(id="ac1", lat=0, lon=0)]
        payload = AirStatesPayload(aircraft=aircraft)

        d = payload.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("aircraft", d)
        self.assertIn("state", d)
        self.assertEqual(len(d["aircraft"]), 1)


if __name__ == "__main__":
    unittest.main()
