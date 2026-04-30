/**
 * Mapbox GL JS renderer for LOD-1/2 (regional and city views).
 * Provides map-based visualization with terrain and building wireframes.
 */
import { BaseRenderer } from "./base.js";

class MapboxRenderer extends BaseRenderer {
    constructor(container, options = {}) {
        super(container, options);
        this.map = null;
        this.mapboxToken = options.mapboxToken || "";
        this.aircraftMarkers = new Map();
        this.selectedMarker = null;
        this.terrainEnabled = options.terrain ?? false;
        this.lastFrameTime = performance.now();
    }

    async init() {
        if (this.isInitialized) return;

        // Load Mapbox GL
        const mapboxLink = document.createElement("link");
        mapboxLink.href = "https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css";
        mapboxLink.rel = "stylesheet";
        document.head.appendChild(mapboxLink);

        const mapboxScript = document.createElement("script");
        mapboxScript.src = "https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js";

        return new Promise((resolve, reject) => {
            mapboxScript.onload = () => {
                try {
                    const mapboxgl = window.mapboxgl;
                    mapboxgl.accessToken = this.mapboxToken;

                    this.map = new mapboxgl.Map({
                        container: this.container,
                        style: "mapbox://styles/mapbox/dark-v11",
                        center: [0, 20],
                        zoom: 2,
                        pitch: 30,
                        bearing: 0,
                    });

                    this.map.on("load", () => {
                        this._setupMapLayers();
                        this.isInitialized = true;
                        resolve();
                    });

                    this.map.on("error", (err) => {
                        reject(new Error(`Mapbox error: ${err.error}`));
                    });
                } catch (err) {
                    reject(err);
                }
            };

            mapboxScript.onerror = () => {
                reject(new Error("Failed to load Mapbox GL"));
            };

            document.body.appendChild(mapboxScript);
        });
    }

    updateAircraft(aircraftList) {
        if (!this.map || !this.map.isStyleLoaded()) return;

        // Remove old markers
        this.aircraftMarkers.forEach((marker) => marker.remove());
        this.aircraftMarkers.clear();

        // Add new markers
        aircraftList.forEach((ac) => {
            if (ac.lat === null || ac.lon === null) return;

            const el = document.createElement("div");
            el.className = "aircraft-marker";
            el.style.width = "24px";
            el.style.height = "24px";
            el.style.backgroundImage =
                "radial-gradient(circle, " +
                (this.selectedFlightId === ac.id ? "#00FF00" : "#00FFFF") +
                ", transparent)";
            el.style.cursor = "pointer";
            el.onclick = () => this.selectFlight(ac.id);

            const marker = new window.mapboxgl.Marker(el)
                .setLngLat([ac.lon, ac.lat])
                .addTo(this.map);

            this.aircraftMarkers.set(ac.id, marker);
        });
    }

    selectFlight(flightId) {
        super.selectFlight(flightId);

        // Find aircraft and center map
        const marker = this.aircraftMarkers.get(flightId);
        if (marker) {
            const lngLat = marker.getLngLat();
            this.map.flyTo({
                center: [lngLat.lng, lngLat.lat],
                zoom: 8,
                duration: 1000,
            });

            this.selectedMarker = marker;
            this._notifyListeners("flight-selected", { flightId, lngLat });
        }
    }

    clearSelection() {
        super.clearSelection();
        this.selectedMarker = null;
    }

    toggleTerrain(enabled) {
        if (!this.map || !this.map.isStyleLoaded()) return;

        this.terrainEnabled = enabled;

        if (enabled && !this.map.getTerrain()) {
            this.map.setTerrain({
                source: "mapbox-dem",
                exaggeration: 1.5,
            });
        } else if (!enabled && this.map.getTerrain()) {
            this.map.setTerrain(null);
        }
    }

    getCamera() {
        if (!this.map) return null;
        const center = this.map.getCenter();
        return {
            mode: "regional",
            latitude: center.lat,
            longitude: center.lng,
            altitude: this._zoomToAltitude(this.map.getZoom()),
            fov: 75,
            bearing: this.map.getBearing(),
            pitch: this.map.getPitch(),
        };
    }

    setCamera(cameraState) {
        if (!this.map) return;
        this.map.flyTo({
            center: [cameraState.longitude, cameraState.latitude],
            zoom: this._altitudeToZoom(cameraState.altitude),
            bearing: cameraState.bearing,
            pitch: cameraState.pitch,
            duration: 1000,
        });
    }

    render() {
        // Mapbox handles rendering internally via GL
    }

    destroy() {
        if (this.map) {
            this.map.remove();
        }
        this.aircraftMarkers.clear();
        this.map = null;
        this.isInitialized = false;
    }

    _setupMapLayers() {
        if (!this.map) return;

        // Add terrain source if not present
        if (!this.map.getSource("mapbox-dem")) {
            this.map.addSource("mapbox-dem", {
                type: "raster-dem",
                url: "mapbox://mapbox.mapbox-dem-v1",
                tileSize: 512,
                maxZoom: 14,
            });
        }

        // Add 3D building extrusion layer (wireframe style)
        if (!this.map.getLayer("3d-buildings")) {
            this.map.addLayer(
                {
                    id: "3d-buildings",
                    source: "composite",
                    "source-layer": "building",
                    type: "fill-extrusion",
                    paint: {
                        "fill-extrusion-color": "rgba(0, 0, 0, 0.1)",
                        "fill-extrusion-height": ["interpolate", ["linear"], ["zoom"], 15, 0, 15.05, ["get", "height"]],
                        "fill-extrusion-base": [
                            "interpolate",
                            ["linear"],
                            ["zoom"],
                            15,
                            0,
                            15.05,
                            ["get", "min_height"],
                        ],
                        "fill-extrusion-opacity": 0.6,
                    },
                },
                "waterway-label"
            );

            // Add cyan stroke to buildings
            this.map.setPaintProperty("3d-buildings", "fill-extrusion-stroke-color", "#00FFFF");
            this.map.setPaintProperty("3d-buildings", "fill-extrusion-stroke-width", 0.5);
        }
    }

    _zoomToAltitude(zoom) {
        // Rough conversion: zoom 2 = 100M m, zoom 12 = 10k m
        return Math.pow(2, 23 - zoom) / 8388608 * 1000000;
    }

    _altitudeToZoom(altitude) {
        return 23 - Math.log2(altitude * 8388608 / 1000000);
    }
}

export { MapboxRenderer };
