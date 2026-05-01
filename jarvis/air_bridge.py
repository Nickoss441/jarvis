"""
Air bridge: OpenSky proxy with cache layer and graceful fallback.
Handles live aircraft state polling with 5-15s cache and mock/offline modes.
"""
import os
import time
import json
import logging
import base64
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from . import config as _config  # ensures .env is loaded  # noqa: F401
from .air_data_schema import (
    AircraftDTO,
    FlightDetailDTO,
    RouteDTO,
    RoutePoint,
    AirStatesPayload,
    DataState,
    DataSourceMode,
)

logger = logging.getLogger(__name__)

# OpenSky API configuration
OPENSKY_URL = "https://opensky-network.org/api/states/all"
OPENSKY_TIMEOUT = 10  # seconds
CACHE_TTL = 15  # seconds

# Fallback: community ADS-B aggregator — European bounding box (no auth, no rate limit)
ADSBCOMMUNITY_URL = "https://api.adsb.lol/v2/bounds/34/72/-25/45"
ADSBCOMMUNITY_TIMEOUT = 10
MAX_AIRCRAFT = 150  # cap before sending to frontend (prioritise airborne)

# adsbdb.com — free aircraft/callsign lookup, no auth required
ADSBDB_URL = "https://api.adsbdb.com/v0"
ADSBDB_TIMEOUT = 5
DETAIL_CACHE_TTL = 3600   # aircraft type/operator is static data
ROUTE_CACHE_TTL  = 300    # callsign routes can vary between legs

# Module-level caches survive across per-request AirBridge() instantiations
_detail_cache: Dict[str, Tuple[float, FlightDetailDTO]] = {}
_route_cache:  Dict[str, Tuple[float, RouteDTO]]        = {}


class AirBridge:
    """
    Unified air data service with OpenSky proxy, cache, and fallback modes.
    """

    def __init__(self, mode: DataSourceMode = DataSourceMode.LIVE):
        self.mode = mode
        self._cache: Optional[Dict] = None
        self._cache_time: float = 0.0
        self._mock_data = self._generate_mock_data()

    def get_all_aircraft(self) -> AirStatesPayload:
        """
        Get all aircraft states with caching and fallback.
        Returns AirStatesPayload with state=LIVE/STALE/ERROR.
        """
        if self.mode == DataSourceMode.MOCK:
            return self._get_mock_aircraft()
        return self._get_live_aircraft()

    def _get_live_aircraft(self) -> AirStatesPayload:
        """Fetch from OpenSky with cache and fallback to mock."""
        now = time.time()

        # Check cache
        if self._cache and (now - self._cache_time) < CACHE_TTL:
            return AirStatesPayload(
                aircraft=[AircraftDTO(**a) for a in self._cache],
                state=DataState.LIVE,
                timestamp=now,
            )

        # Fetch fresh data — try OpenSky first, fall back to community ADS-B
        try:
            aircraft_list = self._fetch_opensky()
            if aircraft_list:
                self._cache = [a.to_dict() for a in aircraft_list]
                self._cache_time = now
                return AirStatesPayload(
                    aircraft=aircraft_list,
                    state=DataState.LIVE,
                    timestamp=now,
                )
        except Exception as e:
            logger.warning(f"OpenSky fetch failed: {e}. Trying community fallback.")

        try:
            aircraft_list = self._fetch_adsb_community()
            if aircraft_list:
                self._cache = [a.to_dict() for a in aircraft_list]
                self._cache_time = now
                return AirStatesPayload(
                    aircraft=aircraft_list,
                    state=DataState.LIVE,
                    timestamp=now,
                )
        except Exception as e:
            logger.warning(f"Community ADS-B fetch failed: {e}. Returning cached or fallback.")

        # Fallback: return cached data marked STALE
        if self._cache:
            return AirStatesPayload(
                aircraft=[AircraftDTO(**a) for a in self._cache],
                state=DataState.STALE,
                timestamp=now,
                message="Data from cache (live source unavailable)",
            )

        # Final fallback: return mock data marked ERROR
        return AirStatesPayload(
            aircraft=self._mock_data,
            state=DataState.ERROR,
            timestamp=now,
            message="Unable to reach live data source. Serving mock data.",
        )

    def _fetch_opensky(self) -> List[AircraftDTO]:
        """Fetch raw data from OpenSky API, normalise, and cap to MAX_AIRCRAFT."""
        try:
            req = Request(OPENSKY_URL)
            user = os.environ.get("OPENSKY_USER")
            pwd  = os.environ.get("OPENSKY_PASS")
            if user and pwd:
                token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
                req.add_header("Authorization", f"Basic {token}")
            with urlopen(req, timeout=OPENSKY_TIMEOUT) as response:
                data = json.loads(response.read().decode())
                all_aircraft = self._normalize_opensky(data)
                return self._prioritise(all_aircraft, MAX_AIRCRAFT)
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            logger.error(f"OpenSky API error: {e}")
            raise

    def _normalize_opensky(self, raw: Dict) -> List[AircraftDTO]:
        """
        Normalize OpenSky raw response to AircraftDTO list.
        OpenSky format: [icao24, callsign, origin, time_position, last_contact, lon, lat, altitude, ...]
        """
        aircraft = []
        states = raw.get("states", [])
        now = time.time()

        for state in states:
            if len(state) < 12:
                continue

            icao24 = state[0]
            callsign = (state[1] or "").strip()
            origin_country = state[2] if len(state) > 2 else None
            lon = state[5]
            lat = state[6]
            alt = state[7]
            on_ground = bool(state[8]) if state[8] is not None else False
            velocity = state[9]
            heading = state[10]
            vertical_rate = state[11] if len(state) > 11 else None
            squawk = state[13] if len(state) > 13 and state[13] else None

            if lat is None or lon is None:
                continue

            aircraft.append(
                AircraftDTO(
                    id=icao24,
                    callsign=callsign or None,
                    lat=lat,
                    lon=lon,
                    alt=alt or 0.0,
                    velocity=velocity or 0.0,
                    heading=heading,
                    state=DataState.LIVE,
                    timestamp=now,
                    on_ground=on_ground,
                    origin_country=origin_country,
                    vertical_rate=vertical_rate,
                    squawk=squawk,
                )
            )

        return aircraft

    def _fetch_adsb_community(self) -> List[AircraftDTO]:
        """Fetch from adsb.lol community aggregator — no auth, global coverage."""
        try:
            req = Request(ADSBCOMMUNITY_URL)
            req.add_header("User-Agent", "Jarvis/1.0")
            with urlopen(req, timeout=ADSBCOMMUNITY_TIMEOUT) as response:
                data = json.loads(response.read().decode())
                all_aircraft = self._normalize_adsb_community(data)
                return self._prioritise(all_aircraft, MAX_AIRCRAFT)
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            logger.error(f"ADS-B community API error: {e}")
            raise

    def _normalize_adsb_community(self, raw: Dict) -> List[AircraftDTO]:
        """Normalize adsb.lol response to AircraftDTO list."""
        aircraft = []
        now = time.time()
        for ac in raw.get("ac", []):
            lat = ac.get("lat")
            lon = ac.get("lon")
            if lat is None or lon is None:
                continue
            alt_baro = ac.get("alt_baro", 0)
            alt = float(alt_baro) if isinstance(alt_baro, (int, float)) else 0.0
            gs = ac.get("gs") or 0.0
            on_ground = alt_baro == "ground" or (isinstance(alt_baro, (int, float)) and alt_baro < 100 and gs < 30)
            aircraft.append(
                AircraftDTO(
                    id=ac.get("hex", ""),
                    callsign=(ac.get("flight") or "").strip() or None,
                    lat=lat,
                    lon=lon,
                    alt=alt,
                    velocity=gs,
                    heading=ac.get("track") or ac.get("true_heading") or 0.0,
                    state=DataState.LIVE,
                    timestamp=now,
                    on_ground=on_ground,
                    origin_country=None,
                    vertical_rate=ac.get("baro_rate") or ac.get("geom_rate") or None,
                    squawk=ac.get("squawk") or None,
                )
            )
        return aircraft

    @staticmethod
    def _prioritise(aircraft: List[AircraftDTO], limit: int) -> List[AircraftDTO]:
        """Keep the most interesting aircraft up to *limit*.

        Priority order: airborne with callsign > airborne no callsign > ground.
        Within each tier, sort by velocity descending so fast movers appear first.
        """
        airborne_named   = [a for a in aircraft if not a.on_ground and a.callsign and a.velocity > 5]
        airborne_unnamed = [a for a in aircraft if not a.on_ground and (not a.callsign or a.velocity <= 5)]
        on_ground        = [a for a in aircraft if a.on_ground]

        for tier in (airborne_named, airborne_unnamed, on_ground):
            tier.sort(key=lambda a: a.velocity or 0, reverse=True)

        combined = airborne_named + airborne_unnamed + on_ground
        return combined[:limit]

    def get_flight_detail(self, flight_id: str) -> Optional[FlightDetailDTO]:
        """Fetch aircraft detail from adsbdb.com (type, operator, registration)."""
        icao = flight_id.strip().lower()
        now = time.time()

        if icao in _detail_cache:
            ts, dto = _detail_cache[icao]
            if now - ts < DETAIL_CACHE_TTL:
                return dto

        dto = self._fetch_adsbdb_aircraft(icao)
        _detail_cache[icao] = (now, dto)
        return dto

    def _fetch_adsbdb_aircraft(self, icao: str) -> FlightDetailDTO:
        """Call adsbdb.com /v0/aircraft/{icao} and return a FlightDetailDTO."""
        try:
            req = Request(f"{ADSBDB_URL}/aircraft/{icao}")
            req.add_header("User-Agent", "Jarvis/1.0")
            with urlopen(req, timeout=ADSBDB_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            ac = data.get("response", {}).get("aircraft") or {}
            if not ac:
                raise ValueError("no aircraft record")
            return FlightDetailDTO(
                id=icao,
                callsign=ac.get("Registration", ""),
                airline=ac.get("RegisteredOwners") or "",
                aircraft_type=ac.get("Type") or "",
                status="unknown",
                state=DataState.LIVE,
                timestamp=time.time(),
            )
        except Exception as exc:
            logger.debug(f"adsbdb aircraft lookup failed for {icao}: {exc}")
            return FlightDetailDTO(
                id=icao,
                callsign="",
                airline="",
                status="unknown",
                state=DataState.ERROR,
                timestamp=time.time(),
            )

    def get_route(self, flight_id: str, callsign: Optional[str] = None) -> Optional[RouteDTO]:
        """Fetch origin/destination from adsbdb.com using the flight callsign."""
        cs = (callsign or "").strip().upper()
        if not cs:
            return RouteDTO(id=flight_id, state=DataState.ERROR, timestamp=time.time())

        now = time.time()
        if cs in _route_cache:
            ts, dto = _route_cache[cs]
            if now - ts < ROUTE_CACHE_TTL:
                return dto

        dto = self._fetch_adsbdb_callsign(flight_id, cs)
        _route_cache[cs] = (now, dto)
        return dto

    def _fetch_adsbdb_callsign(self, flight_id: str, callsign: str) -> RouteDTO:
        """Call adsbdb.com /v0/callsign/{callsign} and return a RouteDTO."""
        try:
            req = Request(f"{ADSBDB_URL}/callsign/{callsign}")
            req.add_header("User-Agent", "Jarvis/1.0")
            with urlopen(req, timeout=ADSBDB_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            cs_data = data.get("response", {}).get("callsign") or {}
            if not cs_data:
                raise ValueError("no callsign record")
            origin = cs_data.get("Origin") or None
            dest   = cs_data.get("Destination") or None
            return RouteDTO(
                id=flight_id,
                origin=origin,
                destination=dest,
                waypoints=[],
                state=DataState.LIVE,
                timestamp=time.time(),
            )
        except Exception as exc:
            logger.debug(f"adsbdb callsign lookup failed for {callsign}: {exc}")
            return RouteDTO(
                id=flight_id,
                state=DataState.ERROR,
                timestamp=time.time(),
            )

    def _get_mock_aircraft(self) -> AirStatesPayload:
        """Return mock aircraft for testing/demo (explicitly labelled MOCK)."""
        return AirStatesPayload(
            aircraft=self._mock_data,
            state=DataState.ERROR,
            timestamp=time.time(),
            message="MOCK mode — no live data source.",
        )

    def _generate_mock_data(self) -> List[AircraftDTO]:
        """Generate European demo aircraft for fallback/offline mode."""
        now = time.time()
        return [
            AircraftDTO(
                id="3c6444",
                callsign="DLH123",
                lat=50.0379,
                lon=8.5622,
                alt=9500,
                velocity=240.0,
                heading=270.0,
                state=DataState.LIVE,
                timestamp=now,
                origin_country="Germany",
            ),
            AircraftDTO(
                id="4ca7b3",
                callsign="RYR456",
                lat=53.4264,
                lon=-6.2499,
                alt=37000,
                velocity=230.0,
                heading=180.0,
                state=DataState.LIVE,
                timestamp=now,
                origin_country="Ireland",
            ),
            AircraftDTO(
                id="3949e2",
                callsign="AFR789",
                lat=48.8566,
                lon=2.3522,
                alt=11000,
                velocity=260.0,
                heading=45.0,
                state=DataState.LIVE,
                timestamp=now,
                origin_country="France",
            ),
        ]


WATCHLIST_PATH = Path("D:/jarvis-data/air_watchlist.json")


class WatchlistManager:
    """JSON-backed store for user-tracked flight ICAO IDs."""

    def __init__(self, path: Path = WATCHLIST_PATH):
        self._path = path

    def _load(self) -> list:
        try:
            return json.loads(self._path.read_text(encoding="utf-8")).get("ids", [])
        except FileNotFoundError:
            return []
        except Exception as exc:
            logger.warning("watchlist load failed, using empty list: %s", exc)
            return []

    def _save(self, ids: list) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"ids": ids}), encoding="utf-8")

    def get_watchlist(self) -> list:
        return self._load()

    def add_to_watchlist(self, icao_id: str) -> bool:
        ids = self._load()
        icao_id = icao_id.strip().lower()
        if icao_id in ids:
            return False
        ids.append(icao_id)
        self._save(ids)
        return True

    def remove_from_watchlist(self, icao_id: str) -> bool:
        ids = self._load()
        icao_id = icao_id.strip().lower()
        if icao_id not in ids:
            return False
        ids.remove(icao_id)
        self._save(ids)
        return True

