#!/usr/bin/env python
"""
Smoke test for Planes tab (Flight Digital Twin).
Validates end-to-end functionality: air data API, renderers, and state machine.
"""
import asyncio
import json
import time
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# Add jarvis to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.air_bridge import AirBridge
from jarvis.air_data_schema import DataSourceMode, DataState


class PlanesSmokeTester:
    """Comprehensive smoke test for Planes tab."""

    def __init__(self, base_url="http://127.0.0.1:8080"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.tests = []

    def log(self, status, message):
        """Log test result."""
        symbol = "✓" if status == "PASS" else "✗"
        print(f"  [{symbol}] {message}")

        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
        self.tests.append((status, message))

    async def test_backend_endpoints(self):
        """Test /hud/air/* backend endpoints."""
        print("\n[Phase 1] Backend Endpoints")

        # Test /hud/air/states
        try:
            url = f"{self.base_url}/hud/air/states"
            with urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                if response.status == 200 and "aircraft" in data:
                    self.log("PASS", f"/hud/air/states returned {len(data['aircraft'])} aircraft")
                else:
                    self.log("FAIL", f"/hud/air/states invalid response: {data}")
        except URLError as e:
            self.log("FAIL", f"/hud/air/states unreachable: {e}")

        # Test /hud/air/flight/{id}
        try:
            url = f"{self.base_url}/hud/air/flight/test123"
            with urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                if response.status == 200 and "id" in data:
                    self.log("PASS", f"/hud/air/flight/{{id}} returned flight details")
                else:
                    self.log("FAIL", f"/hud/air/flight/{{id}} invalid response")
        except URLError:
            self.log("FAIL", "/hud/air/flight/{id} endpoint not found")

        # Test /hud/air/route/{id}
        try:
            url = f"{self.base_url}/hud/air/route/test123"
            with urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                if response.status == 200 and "waypoints" in data:
                    self.log("PASS", f"/hud/air/route/{{id}} returned route with {len(data['waypoints'])} waypoints")
                else:
                    self.log("FAIL", f"/hud/air/route/{{id}} invalid response")
        except URLError:
            self.log("FAIL", "/hud/air/route/{id} endpoint not found")

    async def test_air_bridge(self):
        """Test AirBridge service."""
        print("\n[Phase 2] AirBridge Service")

        # Test LIVE mode (with fallback to mock)
        try:
            bridge = AirBridge(mode=DataSourceMode.LIVE)
            payload = bridge.get_all_aircraft()

            if len(payload.aircraft) > 0:
                self.log("PASS", f"LIVE mode returned {len(payload.aircraft)} aircraft")
            else:
                self.log("FAIL", "LIVE mode returned no aircraft")

            if payload.state in [DataState.LIVE, DataState.STALE]:
                self.log("PASS", f"Data state is {payload.state.value}")
            else:
                self.log("FAIL", f"Unexpected data state: {payload.state.value}")
        except Exception as e:
            self.log("FAIL", f"LIVE mode error: {e}")

        # Test MOCK mode
        try:
            bridge = AirBridge(mode=DataSourceMode.MOCK)
            payload = bridge.get_all_aircraft()

            if len(payload.aircraft) == 3:  # Expected mock count
                self.log("PASS", "MOCK mode returned 3 aircraft")
            else:
                self.log("FAIL", f"MOCK mode expected 3 aircraft, got {len(payload.aircraft)}")
        except Exception as e:
            self.log("FAIL", f"MOCK mode error: {e}")

        # Test caching
        try:
            bridge = AirBridge(mode=DataSourceMode.MOCK)
            payload1 = bridge.get_all_aircraft()
            time.sleep(0.1)
            payload2 = bridge.get_all_aircraft()

            if payload1.timestamp == payload2.timestamp:
                self.log("PASS", "Cache working (timestamps equal)")
            else:
                self.log("FAIL", "Cache not working (timestamps differ)")
        except Exception as e:
            self.log("FAIL", f"Cache test error: {e}")

        # Test flight detail
        try:
            bridge = AirBridge()
            detail = bridge.get_flight_detail("test_id")

            if detail and detail.id == "test_id":
                self.log("PASS", "Flight detail retrieval working")
            else:
                self.log("FAIL", "Flight detail invalid")
        except Exception as e:
            self.log("FAIL", f"Flight detail error: {e}")

        # Test route
        try:
            bridge = AirBridge()
            route = bridge.get_route("test_id")

            if route and len(route.waypoints) > 0:
                self.log("PASS", f"Route retrieval working ({len(route.waypoints)} waypoints)")
            else:
                self.log("FAIL", "Route invalid")
        except Exception as e:
            self.log("FAIL", f"Route error: {e}")

    async def test_planes_page(self):
        """Test Planes page accessibility."""
        print("\n[Phase 3] Planes Page")

        try:
            url = f"{self.base_url}/hud/cc/planes.html"
            with urlopen(url, timeout=5) as response:
                html = response.read().decode()
                if response.status == 200 and "Nexus Control" in html:
                    self.log("PASS", "/hud/cc/planes.html loads successfully")
                else:
                    self.log("FAIL", "/hud/cc/planes.html invalid response")

                # Check for key features in HTML
                if "globe-container" in html:
                    self.log("PASS", "Globe container present in HTML")
                else:
                    self.log("FAIL", "Globe container missing")

                if "map-container" in html:
                    self.log("PASS", "Map container present in HTML")
                else:
                    self.log("FAIL", "Map container missing")

                if "air_service.js" in html:
                    self.log("PASS", "Air service module loaded")
                else:
                    self.log("FAIL", "Air service module not loaded")

                if "renderers/manager.js" in html:
                    self.log("PASS", "Renderer manager module loaded")
                else:
                    self.log("FAIL", "Renderer manager module not loaded")
        except URLError as e:
            self.log("FAIL", f"/hud/cc/planes.html unreachable: {e}")

    async def test_integration_scenario(self):
        """Test end-to-end scenario."""
        print("\n[Phase 4] Integration Scenario")

        try:
            # Simulate page load flow
            bridge = AirBridge(mode=DataSourceMode.MOCK)

            # Step 1: Get initial aircraft
            payload = bridge.get_all_aircraft()
            if payload.aircraft:
                self.log("PASS", "Step 1: Initial aircraft load")
            else:
                self.log("FAIL", "Step 1: No aircraft loaded")
                return

            # Step 2: Select first aircraft
            first_ac = payload.aircraft[0]
            detail = bridge.get_flight_detail(first_ac.id)
            if detail:
                self.log("PASS", "Step 2: Flight detail fetched")
            else:
                self.log("FAIL", "Step 2: Flight detail failed")
                return

            # Step 3: Get route
            route = bridge.get_route(first_ac.id)
            if route and route.waypoints:
                self.log("PASS", "Step 3: Route fetched")
            else:
                self.log("FAIL", "Step 3: Route fetch failed")
                return

            # Step 4: Simulate cache hit
            payload2 = bridge.get_all_aircraft()
            if payload2.timestamp == payload.timestamp:
                self.log("PASS", "Step 4: Cache hit on second poll")
            else:
                self.log("FAIL", "Step 4: Cache miss (unexpected)")

        except Exception as e:
            self.log("FAIL", f"Integration scenario error: {e}")

    async def run_all(self):
        """Run all smoke tests."""
        print("\n" + "=" * 60)
        print("PLANES TAB SMOKE TEST")
        print("=" * 60)

        await self.test_backend_endpoints()
        await self.test_air_bridge()
        await self.test_planes_page()
        await self.test_integration_scenario()

        # Summary
        print("\n" + "=" * 60)
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print("=" * 60 + "\n")

        if self.failed > 0:
            print("FAILED TESTS:")
            for status, msg in self.tests:
                if status == "FAIL":
                    print(f"  - {msg}")

        return self.failed == 0


if __name__ == "__main__":
    tester = PlanesSmokeTester()
    success = asyncio.run(tester.run_all())
    sys.exit(0 if success else 1)
