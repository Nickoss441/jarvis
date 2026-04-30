/**
 * Leaflet-based European airspace map renderer with dead-reckoning animation.
 * Positions extrapolated every second between polls so aircraft fly continuously.
 * Icon cache avoids recreating SVG objects each DR tick.
 */
import { BaseRenderer } from "./base.js";

const DEG_TO_RAD = Math.PI / 180;
const M_PER_DEG_LAT = 111320;
const MAX_DR_SECONDS = 90;

// Europe-centered defaults
const DEFAULT_CENTER = [52, 10];
const DEFAULT_ZOOM = 5;

function deadReckon(ac, nowMs) {
    const v = ac.velocity || 0;
    if (v < 3 || ac.on_ground) return { lat: ac.lat, lon: ac.lon };
    const dt = (nowMs / 1000) - ac.timestamp;
    if (dt <= 0 || dt > MAX_DR_SECONDS) return { lat: ac.lat, lon: ac.lon };
    const hRad = (ac.heading || 0) * DEG_TO_RAD;
    const latRad = ac.lat * DEG_TO_RAD;
    const dlat = (v * Math.cos(hRad) * dt) / M_PER_DEG_LAT;
    const dlon = (v * Math.sin(hRad) * dt) / (M_PER_DEG_LAT * Math.cos(latRad));
    return { lat: ac.lat + dlat, lon: ac.lon + dlon };
}

const AIRCRAFT_SVG = (color, size) =>
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}" style="filter:drop-shadow(0 0 3px ${color}88)"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>`;

// Cache icons by "color_size_roundedHeading" — avoids recreating SVG every second
const _iconCache = new Map();
function makeIcon(L, color, size, heading) {
    const rh = Math.round(heading / 5) * 5;
    const key = `${color}_${size}_${rh}`;
    if (!_iconCache.has(key)) {
        if (_iconCache.size > 2000) _iconCache.clear(); // prevent unbounded growth
        _iconCache.set(key, L.divIcon({
            html: `<div style="transform:rotate(${rh}deg);transform-origin:center;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;">${AIRCRAFT_SVG(color, size)}</div>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
            className: "ac-icon",
        }));
    }
    return _iconCache.get(key);
}

function injectDRStyles() {
    if (document.getElementById("dr-styles")) return;
    const s = document.createElement("style");
    s.id = "dr-styles";
    s.textContent = `.ac-icon.leaflet-zoom-animated { transition: transform 1s linear !important; }`;
    document.head.appendChild(s);
}

// Per-marker icon state to skip setIcon when nothing changed
function _iconParams(ac, selectedId) {
    const isSelected = ac.id === selectedId;
    const isGround = ac.on_ground || (ac.velocity || 0) < 5;
    return {
        color: isSelected ? "#00ff88" : isGround ? "#888888" : "#22d3ee",
        size:  isSelected ? 20 : isGround ? 10 : 14,
        rh:    Math.round((ac.heading ?? 0) / 5) * 5,
    };
}

class GlobeRenderer extends BaseRenderer {
    constructor(container, options = {}) {
        super(container, options);
        this.map = null;
        this.L = null;
        this.markers = new Map();   // id → { marker, color, size, rh }
        this.aircraft = [];
        this._mapDiv = null;
        this._drTimer = null;
    }

    async init() {
        if (this.isInitialized) return;

        if (!document.querySelector("#leaflet-css")) {
            const link = document.createElement("link");
            link.id = "leaflet-css";
            link.rel = "stylesheet";
            link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
            document.head.appendChild(link);
        }

        if (!window.L) {
            await new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
                s.onload = resolve;
                s.onerror = () => reject(new Error("Failed to load Leaflet"));
                document.head.appendChild(s);
            });
        }

        injectDRStyles();
        this.L = window.L;
        const L = this.L;

        this._mapDiv = document.createElement("div");
        this._mapDiv.style.cssText = "width:100%;height:100%;";
        this.container.appendChild(this._mapDiv);

        this.map = L.map(this._mapDiv, {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            zoomControl: false,
            attributionControl: false,
        });

        L.tileLayer(
            "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
            { subdomains: "abcd", maxZoom: 18 }
        ).addTo(this.map);

        L.tileLayer(
            "https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
            { subdomains: "abcd", maxZoom: 18, opacity: 0.5 }
        ).addTo(this.map);

        L.control.zoom({ position: "bottomright" }).addTo(this.map);
        L.control.attribution({ prefix: false }).addAttribution("© CartoDB © OSM").addTo(this.map);

        this.map.on("click", () => {
            if (!this._clickedMarker) this.clearSelection();
            this._clickedMarker = false;
        });

        this._startDRLoop();
        this.isInitialized = true;
    }

    updateAircraft(aircraftList) {
        this.aircraft = aircraftList;
        if (!this.map || !this.L) return;
        this._syncMarkers(Date.now(), true);
    }

    _startDRLoop() {
        this._drTimer = setInterval(() => {
            if (!this.map || this.aircraft.length === 0) return;
            this._syncMarkers(Date.now(), false);
        }, 1000);
    }

    // fullSync=true on fresh poll (add/remove markers)
    // fullSync=false on DR tick (position + icon updates only)
    _syncMarkers(nowMs, fullSync) {
        const L = this.L;
        const seen = new Set();

        for (const ac of this.aircraft) {
            if (ac.lat == null || ac.lon == null) continue;
            seen.add(ac.id);

            const pos = deadReckon(ac, nowMs);
            const { color, size, rh } = _iconParams(ac, this.selectedFlightId);

            if (this.markers.has(ac.id)) {
                const entry = this.markers.get(ac.id);
                entry.marker.setLatLng([pos.lat, pos.lon]);
                // Only call setIcon when appearance actually changed
                if (entry.color !== color || entry.size !== size || entry.rh !== rh) {
                    entry.marker.setIcon(makeIcon(L, color, size, rh));
                    entry.color = color;
                    entry.size = size;
                    entry.rh = rh;
                }
            } else if (fullSync) {
                const icon = makeIcon(L, color, size, rh);
                const m = L.marker([pos.lat, pos.lon], { icon }).addTo(this.map);
                m.on("click", (e) => {
                    L.DomEvent.stopPropagation(e);
                    this._clickedMarker = true;
                    this.selectFlight(ac.id);
                });
                this.markers.set(ac.id, { marker: m, color, size, rh });
            }
        }

        if (fullSync) {
            for (const [id, entry] of this.markers) {
                if (!seen.has(id)) {
                    entry.marker.remove();
                    this.markers.delete(id);
                }
            }
        }
    }

    selectFlight(flightId) {
        super.selectFlight(flightId);
        const ac = this.aircraft.find((a) => a.id === flightId);
        if (ac && this.map) {
            const pos = deadReckon(ac, Date.now());
            this.map.setView([pos.lat, pos.lon], Math.max(this.map.getZoom(), 7), {
                animate: true, duration: 0.8,
            });
            this._notifyListeners("flight-selected", { flightId, position: ac });
        }
        this._syncMarkers(Date.now(), false);
    }

    clearSelection() {
        super.clearSelection();
        if (this.map) {
            this.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM, { animate: true, duration: 0.8 });
        }
        this._syncMarkers(Date.now(), false);
        this._notifyListeners("flight-deselected", {});
    }

    getCamera() {
        if (!this.map) return null;
        const c = this.map.getCenter();
        return { mode: "map", latitude: c.lat, longitude: c.lng, altitude: 1000000 };
    }

    setCamera(state) {
        if (!this.map) return;
        this.map.setView([state.latitude, state.longitude], 4);
    }

    render() {}

    destroy() {
        if (this._drTimer) { clearInterval(this._drTimer); this._drTimer = null; }
        if (this.map) { this.map.remove(); this.map = null; }
        if (this._mapDiv) { this._mapDiv.remove(); this._mapDiv = null; }
        this.markers.clear();
        this.isInitialized = false;
    }
}

export { GlobeRenderer };
