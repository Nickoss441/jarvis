/**
 * Renderer manager for seamless LOD-based switching.
 * Manages transition, selection, and coordination between globe/mapbox renderers.
 */
import { RendererTransition, RendererPerformanceMonitor } from "./base.js";
import { AirStateManager } from "../air_state.js";

class RendererManager {
    constructor(containerGlobe, containerMap, options = {}) {
        this.containerGlobe = containerGlobe;
        this.containerMap = containerMap;
        this.globeRenderer = null;
        this.mapboxRenderer = null;
        this.currentRenderer = null;
        this.nextRenderer = null;
        this.isTransitioning = false;
        this.options = options;
        this.performanceMonitor = new RendererPerformanceMonitor();
        this.stateManager = new AirStateManager();
        this.listeners = [];

        // Altitude thresholds for auto-transition
        this.altitudeThresholds = {
            GLOBE_TO_MAP: 500000, // 500k m
            MAP_TO_CITY: 50000,   // 50k m
            CITY_TO_MAP: 100000,
            MAP_TO_GLOBE: 1000000, // 1M m
        };
    }

    async init() {
        // Initialize renderers
        const { GlobeRenderer } = await import("./globe.js");
        const { MapboxRenderer } = await import("./mapbox.js");

        this.globeRenderer = new GlobeRenderer(this.containerGlobe, this.options);
        this.mapboxRenderer = new MapboxRenderer(this.containerMap, this.options);

        // Subscribe to renderer events
        this.globeRenderer.subscribe((event) => {
            if (event.event === "flight-selected") {
                this._onFlightSelected(event.data);
            }
        });

        this.mapboxRenderer.subscribe((event) => {
            if (event.event === "flight-selected") {
                this._onFlightSelected(event.data);
            }
        });

        // Initialize both
        await this.globeRenderer.init();
        try {
            await this.mapboxRenderer.init();
        } catch (err) {
            console.warn("[RendererManager] Mapbox init skipped (no token or load error):", err.message);
            this.mapboxRenderer = null;
        }

        this.currentRenderer = this.globeRenderer;
        this.containerGlobe.style.display = "block";
        this.containerMap.style.display = "none";
    }

    /**
     * Update aircraft on current and next renderers.
     */
    updateAircraft(aircraftList) {
        if (this.currentRenderer) {
            this.currentRenderer.updateAircraft(aircraftList);
        }
        if (this.nextRenderer) {
            this.nextRenderer.updateAircraft(aircraftList);
        }

        // Check if we need to transition based on selected flight
        if (this.stateManager.selectedFlight.id) {
            const aircraft = aircraftList.find(
                (ac) => ac.id === this.stateManager.selectedFlight.id
            );
            if (aircraft) {
                this._checkAutoTransition(aircraft.alt);
            }
        }
    }

    /**
     * Select a flight and prepare transition if needed.
     */
    async selectFlight(flightId) {
        this.stateManager.selectFlight(flightId);

        if (this.currentRenderer) {
            this.currentRenderer.selectFlight(flightId);
        }

        // Trigger transition to next LOD
        await this._transitionToNextLOD();
    }

    /**
     * Clear selection and revert to globe view.
     */
    async clearSelection() {
        this.stateManager.clearSelection();

        if (this.currentRenderer) {
            this.currentRenderer.clearSelection();
        }

        // Transition back to globe if needed
        if (this.currentRenderer !== this.globeRenderer) {
            await this._transitionTo(this.globeRenderer);
        }
    }

    /**
     * Manually transition between renderers.
     */
    async transitionTo(targetRenderer) {
        if (this.isTransitioning || this.currentRenderer === targetRenderer) {
            return;
        }

        await this._transitionTo(targetRenderer);
    }

    /**
     * Get performance stats.
     */
    getPerformanceStats() {
        return this.performanceMonitor.getStats();
    }

    /**
     * Check if auto-transition is needed based on altitude.
     */
    _checkAutoTransition(altitude) {
        if (!this.currentRenderer || this.isTransitioning) return;

        const isOnGlobe = this.currentRenderer === this.globeRenderer;

        if (
            isOnGlobe &&
            altitude < this.altitudeThresholds.GLOBE_TO_MAP
        ) {
            this._transitionTo(this.mapboxRenderer);
        } else if (
            !isOnGlobe &&
            altitude > this.altitudeThresholds.MAP_TO_GLOBE
        ) {
            this._transitionTo(this.globeRenderer);
        }
    }

    /**
     * Internal transition implementation.
     */
    async _transitionTo(targetRenderer) {
        if (this.isTransitioning) return;
        this.isTransitioning = true;
        this._notifyListeners("transition-start", { target: targetRenderer });

        try {
            const fromRenderer = this.currentRenderer;
            const transition = new RendererTransition(fromRenderer, targetRenderer, 500);

            await transition.fadeBetween();

            // Swap visibility
            this.containerGlobe.style.display = targetRenderer === this.globeRenderer ? "block" : "none";
            this.containerMap.style.display = targetRenderer === this.mapboxRenderer ? "block" : "none";

            // Reset opacity
            this.containerGlobe.style.opacity = "1";
            this.containerMap.style.opacity = "1";

            this.currentRenderer = targetRenderer;
            this._notifyListeners("transition-end", { target: targetRenderer });
        } catch (err) {
            console.error("Transition failed:", err);
            this._notifyListeners("transition-error", { error: err.message });
        } finally {
            this.isTransitioning = false;
        }
    }

    /**
     * Transition to next LOD based on current state.
     * When mapbox is unavailable, Leaflet handles zoom natively.
     */
    async _transitionToNextLOD() {
        if (!this.mapboxRenderer) return;
        if (this.currentRenderer === this.globeRenderer) {
            await this._transitionTo(this.mapboxRenderer);
        }
    }

    /**
     * Handle flight selection from renderer.
     */
    _onFlightSelected(data) {
        this._notifyListeners("flight-selected", data);
    }

    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener);
        };
    }

    _notifyListeners(event, data) {
        this.listeners.forEach((listener) => {
            try {
                listener({ event, data });
            } catch (e) {
                console.error(`RendererManager listener error (${event}):`, e);
            }
        });
    }

    destroy() {
        this.globeRenderer?.destroy();
        this.mapboxRenderer?.destroy();
        this.listeners = [];
    }
}

export { RendererManager };
