/**
 * Frontend air data service for polling backend endpoints.
 * Handles polling, error recovery, and cache management.
 */
import { AircraftState, DataState } from "./air_state.js";

class AirDataService {
    constructor(baseUrl = "/hud/air", pollIntervalMs = 15000) {
        this.baseUrl = baseUrl;
        this.pollIntervalMs = pollIntervalMs;
        this.pollTimer = null;
        this.isPolling = false;
        this._paused = false;
        this.lastFetch = 0;
        this.errorCount = 0;
        this.maxErrorsBeforeFallback = 3;
        this.listeners = [];
    }

    /**
     * Start polling for aircraft states.
     */
    startPolling(listener) {
        if (this.isPolling) return;
        this.isPolling = true;
        this._paused = false;
        if (listener) this.listeners.push(listener);
        this._schedulePoll(0);
    }

    stopPolling() {
        this.isPolling = false;
        this._paused = false;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }

    pause() {
        this._paused = true;
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
    }

    resume() {
        if (!this._paused) return;
        this._paused = false;
        if (this.isPolling) this._schedulePoll(0);
    }

    _schedulePoll(delayMs) {
        this.pollTimer = setTimeout(async () => {
            if (!this.isPolling || this._paused) return;
            try {
                const data = await this.fetchStates();
                this.errorCount = 0;
                this._notifyListeners(data);
            } catch (err) {
                this.errorCount += 1;
                this._notifyListeners({
                    aircraft: [],
                    state: DataState.ERROR,
                    message: `Fetch failed: ${err.message}`,
                });
            }
            if (this.isPolling && !this._paused) {
                this._schedulePoll(this.pollIntervalMs);
            }
        }, delayMs);
    }

    /**
     * Fetch all aircraft states from /hud/air/states.
     */
    async fetchStates() {
        const url = `${this.baseUrl}/states`;
        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const json = await response.json();
        this.lastFetch = Date.now();

        // Normalize aircraft to AircraftState objects
        const aircraft = (json.aircraft || []).map((a) => new AircraftState(a));

        return {
            aircraft,
            state: json.state || DataState.LIVE,
            timestamp: json.timestamp || Date.now() / 1000,
            message: json.message || null,
        };
    }

    /**
     * Fetch detailed flight info for a single aircraft.
     */
    async fetchFlightDetail(flightId) {
        const url = `${this.baseUrl}/flight/${encodeURIComponent(flightId)}`;
        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Flight not found`);
        }

        return await response.json();
    }

    /**
     * Fetch route/corridor for a flight. Passes callsign so the backend
     * can look up origin/destination via adsbdb.com.
     */
    async fetchRoute(flightId, callsign = "") {
        const cs = callsign ? `?cs=${encodeURIComponent(callsign)}` : "";
        const url = `${this.baseUrl}/route/${encodeURIComponent(flightId)}${cs}`;
        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: Route not found`);
        }

        const json = await response.json();
        // Normalize waypoints if present
        if (json.waypoints && Array.isArray(json.waypoints)) {
            json.waypoints = json.waypoints.map((wp) => ({
                lat: wp.lat,
                lon: wp.lon,
                alt: wp.alt || null,
            }));
        }
        return json;
    }

    async fetchWatchlist() {
        const res = await fetch(`${this.baseUrl}/watchlist`, { headers: { Accept: "application/json" } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }

    async addToWatchlist(icaoId) {
        const res = await fetch(`${this.baseUrl}/watchlist`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ id: icaoId.toLowerCase() }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }

    async removeFromWatchlist(icaoId) {
        const res = await fetch(`${this.baseUrl}/watchlist/${encodeURIComponent(icaoId.toLowerCase())}`, {
            method: "DELETE",
            headers: { Accept: "application/json" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener);
        };
    }

    _notifyListeners(data) {
        this.listeners.forEach((listener) => {
            try {
                listener(data);
            } catch (e) {
                console.error("[AirDataService] Listener error:", e);
            }
        });
    }

    /**
     * Check connection health.
     */
    async checkHealth() {
        try {
            const data = await this.fetchStates();
            return data.state === DataState.LIVE;
        } catch {
            return false;
        }
    }

    /**
     * Get seconds since last successful fetch.
     */
    getSecondsSinceLastFetch() {
        if (this.lastFetch === 0) return Infinity;
        return (Date.now() - this.lastFetch) / 1000;
    }
}

export { AirDataService };
