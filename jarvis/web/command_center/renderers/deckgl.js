/**
 * deck.gl overlay renderer for high-density aircraft visualization.
 * Optional LOD-2 enhancement for rendering 1000+ aircraft with performance optimization.
 * Feature-flagged behind ENABLE_DECKGL constant.
 */
import { BaseRenderer } from "./base.js";

const ENABLE_DECKGL = false; // Set to true to enable deck.gl overlay

class DeckGLRenderer extends BaseRenderer {
    constructor(container, options = {}) {
        super(container, options);
        this.deckglLoaded = false;
        this.deck = null;
        this.layers = [];
        this.enabled = ENABLE_DECKGL;
    }

    async init() {
        if (!this.enabled) {
            console.log("[DeckGLRenderer] Disabled via ENABLE_DECKGL flag");
            return;
        }

        if (this.isInitialized) return;

        // Lazy load deck.gl
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://esm.sh/deck.gl@14";
            script.type = "module";

            script.onload = async () => {
                try {
                    // deck.gl will be available as window.deck or via import
                    this.deckglLoaded = true;
                    this.isInitialized = true;
                    resolve();
                } catch (err) {
                    reject(err);
                }
            };

            script.onerror = () => {
                reject(new Error("Failed to load deck.gl"));
            };

            document.head.appendChild(script);
        });
    }

    updateAircraft(aircraftList) {
        if (!this.enabled || !this.deckglLoaded) return;

        // Filter valid aircraft
        const validAircraft = aircraftList.filter(
            (ac) => ac.lat !== null && ac.lon !== null
        );

        // Create scatterplot layer for aircraft points
        const scatterplotData = validAircraft.map((ac) => ({
            position: [ac.lon, ac.lat],
            id: ac.id,
            color:
                this.selectedFlightId === ac.id
                    ? [0, 255, 0, 200] // Green for selected
                    : [0, 255, 255, 100], // Cyan for others
            size: this.selectedFlightId === ac.id ? 200 : 100,
            altitude: ac.alt,
            velocity: ac.velocity,
        }));

        // Create arc layer for selected flight route
        const arcData = [];
        if (this.selectedFlightId) {
            const selected = validAircraft.find((ac) => ac.id === this.selectedFlightId);
            if (selected) {
                arcData.push({
                    sourcePosition: [selected.lon, selected.lat],
                    targetPosition: [selected.lon + 5, selected.lat + 5], // Demo destination
                    color: [0, 255, 0, 160],
                });
            }
        }

        // Update layers (placeholder - actual implementation depends on deck.gl version)
        this._notifyListeners("update", { aircraftCount: validAircraft.length });
    }

    selectFlight(flightId) {
        super.selectFlight(flightId);
        this._notifyListeners("flight-selected", { flightId });
    }

    clearSelection() {
        super.clearSelection();
        this._notifyListeners("flight-deselected");
    }

    getCamera() {
        // Return placeholder camera state
        return {
            mode: "deckgl",
            latitude: 0,
            longitude: 0,
            altitude: 100000,
            fov: 75,
            bearing: 0,
            pitch: 45,
        };
    }

    setCamera(cameraState) {
        if (!this.deckglLoaded) return;
        // Update viewport
    }

    render() {
        if (!this.deckglLoaded) return;
        // Render deck.gl scene
    }

    destroy() {
        if (this.deck) {
            this.deck.finalize();
        }
        this.deck = null;
        this.deckglLoaded = false;
        this.isInitialized = false;
    }

    /**
     * Check if deck.gl is available and enabled.
     */
    static isAvailable() {
        return ENABLE_DECKGL && typeof window !== "undefined";
    }

    /**
     * Performance estimate for aircraft count.
     */
    static canHandle(aircraftCount) {
        // deck.gl can efficiently render 1000+ points
        return aircraftCount > 500;
    }
}

export { DeckGLRenderer };
