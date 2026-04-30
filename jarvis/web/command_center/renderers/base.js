/**
 * Abstract base renderer interface and utilities for LOD-based rendering.
 * Defines common interface and transition helpers for all renderer implementations.
 */

class BaseRenderer {
    constructor(container, options = {}) {
        this.container = container;
        this.options = options;
        this.isInitialized = false;
        this.selectedFlightId = null;
        this.listeners = [];
    }

    /**
     * Initialize renderer (must be implemented by subclasses).
     */
    async init() {
        throw new Error("init() must be implemented");
    }

    /**
     * Update aircraft data on map/globe.
     */
    updateAircraft(aircraftList) {
        throw new Error("updateAircraft() must be implemented");
    }

    /**
     * Select a flight and focus on it.
     */
    selectFlight(flightId) {
        this.selectedFlightId = flightId;
        this._notifyListeners("select", { flightId });
    }

    /**
     * Clear selection.
     */
    clearSelection() {
        this.selectedFlightId = null;
        this._notifyListeners("deselect");
    }

    /**
     * Get current camera state.
     */
    getCamera() {
        throw new Error("getCamera() must be implemented");
    }

    /**
     * Set camera state.
     */
    setCamera(cameraState) {
        throw new Error("setCamera() must be implemented");
    }

    /**
     * Render a frame.
     */
    render() {
        throw new Error("render() must be implemented");
    }

    /**
     * Cleanup and teardown.
     */
    destroy() {
        throw new Error("destroy() must be implemented");
    }

    /**
     * Check if renderer is ready for interaction.
     */
    isReady() {
        return this.isInitialized;
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
                console.error(`Renderer listener error (${event}):`, e);
            }
        });
    }
}

/**
 * Transition helper for smooth LOD transitions.
 */
class RendererTransition {
    constructor(fromRenderer, toRenderer, durationMs = 500) {
        this.fromRenderer = fromRenderer;
        this.toRenderer = toRenderer;
        this.durationMs = durationMs;
        this.startTime = null;
        this.isComplete = false;
    }

    async execute(onProgress) {
        return new Promise((resolve) => {
            this.startTime = performance.now();

            const animate = (currentTime) => {
                if (!this.startTime) this.startTime = currentTime;

                const elapsed = currentTime - this.startTime;
                const progress = Math.min(elapsed / this.durationMs, 1);

                if (onProgress) {
                    onProgress(progress, this.fromRenderer, this.toRenderer);
                }

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    this.isComplete = true;
                    resolve();
                }
            };

            requestAnimationFrame(animate);
        });
    }

    /**
     * Standard fade transition: fade out from, fade in to.
     */
    async fadeBetween() {
        const fromElement = this.fromRenderer.container;
        const toElement = this.toRenderer.container;

        // Ensure both are visible
        fromElement.style.opacity = "1";
        toElement.style.opacity = "0";

        await this.execute((progress) => {
            fromElement.style.opacity = String(1 - progress);
            toElement.style.opacity = String(progress);
        });
    }

    /**
     * Zoom + fade: zoom into target while fading.
     */
    async zoomFade() {
        const fromElement = this.fromRenderer.container;
        const toElement = this.toRenderer.container;

        fromElement.style.opacity = "1";
        toElement.style.opacity = "0";
        toElement.style.transform = "scale(0.95)";

        await this.execute((progress) => {
            fromElement.style.opacity = String(1 - progress);
            toElement.style.opacity = String(progress);
            toElement.style.transform = `scale(${0.95 + progress * 0.05})`;
        });

        toElement.style.transform = "scale(1)";
    }
}

/**
 * Performance monitor for renderer FPS and frame time.
 */
class RendererPerformanceMonitor {
    constructor(historySize = 60) {
        this.historySize = historySize;
        this.frameTimes = [];
        this.fps = 60;
        this.avgFrameTime = 0;
    }

    recordFrame(deltaMs) {
        this.frameTimes.push(deltaMs);
        if (this.frameTimes.length > this.historySize) {
            this.frameTimes.shift();
        }

        if (this.frameTimes.length > 0) {
            this.avgFrameTime =
                this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
            this.fps = Math.round(1000 / this.avgFrameTime);
        }
    }

    getStats() {
        return {
            fps: this.fps,
            avgFrameTime: Math.round(this.avgFrameTime * 100) / 100,
            minFrameTime: Math.min(...this.frameTimes),
            maxFrameTime: Math.max(...this.frameTimes),
        };
    }

    isGoodPerformance(minFps = 30) {
        return this.fps >= minFps;
    }
}

export { BaseRenderer, RendererTransition, RendererPerformanceMonitor };
