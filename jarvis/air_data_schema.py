"""
Air data schemas and contracts for LOD-based flight digital twin.
Defines shared state contracts for camera, selected flight, and aircraft data.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum


class DataSourceMode(str, Enum):
    """Data source mode for planes module."""
    LIVE = "live"
    MOCK = "mock"
    REPLAY = "replay"


class DataState(str, Enum):
    """Flight data freshness state."""
    LIVE = "live"
    STALE = "stale"
    ERROR = "error"


@dataclass
class AircraftDTO:
    """Normalized aircraft state from OpenSky or mock source."""
    id: str  # icao24 or unique identifier
    callsign: Optional[str] = None
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0  # meters (barometric)
    velocity: float = 0.0  # m/s
    heading: Optional[float] = None  # degrees true track, None if stationary
    state: DataState = DataState.LIVE
    timestamp: float = 0.0  # Unix timestamp
    on_ground: bool = False
    origin_country: Optional[str] = None
    vertical_rate: Optional[float] = None  # m/s, positive = climbing
    squawk: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class FlightDetailDTO:
    """Detailed flight information for selected aircraft."""
    id: str
    callsign: str
    airline: Optional[str] = None
    aircraft_type: Optional[str] = None
    departure: Optional[str] = None
    destination: Optional[str] = None
    eta: Optional[float] = None
    status: str = "in-flight"  # in-flight, landed, unknown
    state: DataState = DataState.LIVE
    timestamp: float = 0.0

    def to_dict(self):
        return asdict(self)


@dataclass
class RoutePoint:
    """Single waypoint on flight route."""
    lat: float
    lon: float
    alt: Optional[float] = None


@dataclass
class RouteDTO:
    """Route polyline and corridor for selected flight."""
    id: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    waypoints: List[RoutePoint] = field(default_factory=list)
    state: DataState = DataState.LIVE
    timestamp: float = 0.0

    def to_dict(self):
        d = asdict(self)
        d["waypoints"] = [asdict(wp) for wp in self.waypoints]
        return d


@dataclass
class CameraState:
    """Shared 3D camera state for LOD transitions."""
    mode: str  # "globe", "regional", "city"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 100000.0  # meters (or equivalent scale)
    fov: float = 75.0  # degrees
    bearing: float = 0.0  # degrees
    pitch: float = 0.0  # degrees

    def to_dict(self):
        return asdict(self)


@dataclass
class SelectedFlightState:
    """Shared selected flight state across LODs."""
    id: Optional[str] = None
    callsign: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt: Optional[float] = None
    velocity: Optional[float] = None
    heading: Optional[float] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class AirStatesPayload:
    """Response payload for /hud/air/states endpoint."""
    aircraft: List[AircraftDTO] = field(default_factory=list)
    state: DataState = DataState.LIVE
    timestamp: float = 0.0
    message: Optional[str] = None

    def to_dict(self):
        return {
            "aircraft": [a.to_dict() for a in self.aircraft],
            "state": self.state.value,
            "timestamp": self.timestamp,
            "message": self.message,
        }
