/**
 * Air data state schema and utilities for flight digital twin.
 * Shared state contracts for camera, selected flight, and aircraft data.
 */

const DataSourceMode = {
    LIVE: "live",
    MOCK: "mock",
    REPLAY: "replay",
};

const DataState = {
    LIVE: "live",
    STALE: "stale",
    ERROR: "error",
};

class AircraftState {
    constructor(data = {}) {
        this.id = data.id || "";
        this.callsign = data.callsign || null;
        this.lat = data.lat ?? 0;
        this.lon = data.lon ?? 0;
        this.alt = data.alt ?? 0;
        this.velocity = data.velocity ?? 0;
        this.heading = data.heading ?? null;
        this.state = data.state || DataState.LIVE;
        this.timestamp = data.timestamp || Date.now() / 1000;
        this.on_ground = data.on_ground ?? false;
        this.origin_country = data.origin_country || null;
        this.vertical_rate = data.vertical_rate ?? null;
        this.squawk = data.squawk || null;
    }

    isValid() {
        return !isNaN(this.lat) && !isNaN(this.lon);
    }

    distanceTo(other) {
        // Simple Euclidean distance, not geodesic
        const dx = this.lon - other.lon;
        const dy = this.lat - other.lat;
        return Math.sqrt(dx * dx + dy * dy);
    }
}

class CameraState {
    constructor(data = {}) {
        this.mode = data.mode || "globe"; // globe, regional, city
        this.latitude = data.latitude ?? 0;
        this.longitude = data.longitude ?? 0;
        this.altitude = data.altitude ?? 100000;
        this.fov = data.fov ?? 75;
        this.bearing = data.bearing ?? 0;
        this.pitch = data.pitch ?? 0;
    }

    toGlobeView() {
        return { lat: this.latitude, lon: this.longitude, altitude: this.altitude };
    }

    toMapboxView() {
        return {
            center: [this.longitude, this.latitude],
            zoom: this.altitude > 5000000 ? 2 : this.altitude > 1000000 ? 4 : 8,
            bearing: this.bearing,
            pitch: this.pitch,
        };
    }
}

class SelectedFlightState {
    constructor(data = {}) {
        this.id = data.id || null;
        this.callsign = data.callsign || null;
        this.lat = data.lat ?? null;
        this.lon = data.lon ?? null;
        this.alt = data.alt ?? null;
        this.velocity = data.velocity ?? null;
        this.heading = data.heading ?? null;
    }

    isSelected() {
        return this.id !== null;
    }

    updateFromAircraft(aircraft) {
        this.id = aircraft.id;
        this.callsign = aircraft.callsign;
        this.lat = aircraft.lat;
        this.lon = aircraft.lon;
        this.alt = aircraft.alt;
        this.velocity = aircraft.velocity;
        this.heading = aircraft.heading;
    }

    clear() {
        this.id = null;
        this.callsign = null;
        this.lat = null;
        this.lon = null;
        this.alt = null;
        this.velocity = null;
        this.heading = null;
    }
}

class AirStateManager {
    constructor() {
        this.aircraft = new Map(); // id -> AircraftState
        this.selectedFlight = new SelectedFlightState();
        this.camera = new CameraState();
        this.dataState = DataState.LIVE;
        this.lastUpdate = 0;
        this.listeners = [];
    }

    updateAircraft(aircraftList) {
        this.aircraft.clear();
        for (const ac of aircraftList) {
            if (ac.isValid && ac.isValid()) {
                this.aircraft.set(ac.id, ac);
            }
        }
        this.lastUpdate = Date.now() / 1000;
        this._notifyListeners("aircraft");
    }

    selectFlight(aircraftId) {
        const aircraft = this.aircraft.get(aircraftId);
        if (aircraft) {
            this.selectedFlight.updateFromAircraft(aircraft);
            this._notifyListeners("selected");
        }
    }

    clearSelection() {
        this.selectedFlight.clear();
        this._notifyListeners("selected");
    }

    setCamera(newCamera) {
        this.camera = new CameraState(newCamera);
        this._notifyListeners("camera");
    }

    setDataState(state) {
        this.dataState = state;
        this._notifyListeners("data-state");
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener);
        };
    }

    _notifyListeners(topic) {
        this.listeners.forEach((listener) => {
            try {
                listener(topic, this);
            } catch (e) {
                console.error("Listener error:", e);
            }
        });
    }

    getAircraftNear(lat, lon, radiusDegrees = 10) {
        const center = { lat, lon };
        return Array.from(this.aircraft.values()).filter(
            (ac) => ac.distanceTo(center) < radiusDegrees
        );
    }
}

export {
    DataSourceMode,
    DataState,
    AircraftState,
    CameraState,
    SelectedFlightState,
    AirStateManager,
};
