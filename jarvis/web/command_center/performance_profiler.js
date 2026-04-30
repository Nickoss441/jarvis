/**
 * Performance profiler for Planes tab renderers.
 * Measures FPS, render time, memory, and provides performance reports.
 */

class PerformanceProfiler {
    constructor(targetFps = 60, historySize = 300) {
        this.targetFps = targetFps;
        this.historySize = historySize;
        this.frameTimes = [];
        this.memorySnapshots = [];
        this.startTime = performance.now();
        this.isRecording = false;
        this.lastFrameTime = 0;
        this.maxFrameTime = 0;
        this.minFrameTime = Infinity;
        this.droppedFrames = 0;
    }

    /**
     * Record a frame execution time.
     */
    recordFrame(deltaMs) {
        if (!this.isRecording) return;

        this.frameTimes.push(deltaMs);
        if (this.frameTimes.length > this.historySize) {
            this.frameTimes.shift();
        }

        this.lastFrameTime = deltaMs;
        this.maxFrameTime = Math.max(this.maxFrameTime, deltaMs);
        this.minFrameTime = Math.min(this.minFrameTime, deltaMs);

        // Track dropped frames (>33ms for 30fps, >16ms for 60fps)
        const targetFrameTime = 1000 / this.targetFps;
        if (deltaMs > targetFrameTime * 1.5) {
            this.droppedFrames += 1;
        }
    }

    /**
     * Record memory snapshot.
     */
    recordMemory() {
        if (!this.isRecording || !performance.memory) return;

        this.memorySnapshots.push({
            timestamp: performance.now(),
            heapUsed: performance.memory.usedJSHeapSize,
            heapLimit: performance.memory.jsHeapSizeLimit,
            external: performance.memory.jsExternalMemoryUsage,
        });

        if (this.memorySnapshots.length > 50) {
            this.memorySnapshots.shift();
        }
    }

    /**
     * Start profiling session.
     */
    start() {
        this.isRecording = true;
        this.frameTimes = [];
        this.memorySnapshots = [];
        this.startTime = performance.now();
        this.droppedFrames = 0;
        console.log("[PerformanceProfiler] Profiling started");
    }

    /**
     * Stop profiling and generate report.
     */
    stop() {
        this.isRecording = false;
        const report = this.generateReport();
        console.log("[PerformanceProfiler] Profiling stopped");
        return report;
    }

    /**
     * Get current performance stats.
     */
    getStats() {
        const avgFrameTime =
            this.frameTimes.length > 0
                ? this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length
                : 0;

        const fps = avgFrameTime > 0 ? Math.round(1000 / avgFrameTime) : 0;
        const droppedFrameRate =
            this.frameTimes.length > 0
                ? (this.droppedFrames / this.frameTimes.length) * 100
                : 0;

        let memStats = null;
        if (this.memorySnapshots.length > 0) {
            const latest = this.memorySnapshots[this.memorySnapshots.length - 1];
            memStats = {
                heapUsedMB: (latest.heapUsed / 1024 / 1024).toFixed(2),
                heapLimitMB: (latest.heapLimit / 1024 / 1024).toFixed(2),
                externalMB: (latest.external / 1024 / 1024).toFixed(2),
            };
        }

        return {
            fps,
            avgFrameTime: Math.round(avgFrameTime * 100) / 100,
            minFrameTime: Math.round(this.minFrameTime * 100) / 100,
            maxFrameTime: Math.round(this.maxFrameTime * 100) / 100,
            droppedFrames: this.droppedFrames,
            droppedFrameRate: Math.round(droppedFrameRate * 10) / 10,
            memory: memStats,
        };
    }

    /**
     * Generate comprehensive performance report.
     */
    generateReport() {
        const stats = this.getStats();
        const duration = (performance.now() - this.startTime) / 1000;
        const meetsTarget = stats.fps >= this.targetFps * 0.95; // Allow 5% variance

        return {
            timestamp: new Date().toISOString(),
            durationSeconds: Math.round(duration * 100) / 100,
            targetFps: this.targetFps,
            meetsTarget,
            performance: stats,
            recommendations: this._generateRecommendations(stats),
        };
    }

    /**
     * Generate performance recommendations.
     */
    _generateRecommendations(stats) {
        const recommendations = [];

        if (stats.fps < this.targetFps * 0.8) {
            recommendations.push(
                "FPS below target. Consider: reduce polygon count, enable LOD culling, or disable terrain."
            );
        }

        if (stats.droppedFrameRate > 10) {
            recommendations.push(
                "High dropped frame rate. Check for: heavy JS execution, unnecessary re-renders, or large DOM updates."
            );
        }

        if (stats.maxFrameTime > 50) {
            recommendations.push(
                "Frame time spikes detected. Profile with DevTools to identify long-running tasks."
            );
        }

        if (stats.memory && parseFloat(stats.memory.heapUsedMB) > 300) {
            recommendations.push(
                "High memory usage. Check for: memory leaks, unreleased textures, or unbounded arrays."
            );
        }

        if (recommendations.length === 0) {
            recommendations.push("Performance is optimal. Monitor for regressions.");
        }

        return recommendations;
    }

    /**
     * Profile a specific task and return execution time.
     */
    static profileTask(name, task) {
        const start = performance.now();
        const result = task();
        const duration = performance.now() - start;
        console.log(`[Profile] ${name}: ${Math.round(duration * 100) / 100}ms`);
        return { result, duration };
    }

    /**
     * Profile async task.
     */
    static async profileTaskAsync(name, task) {
        const start = performance.now();
        const result = await task();
        const duration = performance.now() - start;
        console.log(`[Profile] ${name}: ${Math.round(duration * 100) / 100}ms`);
        return { result, duration };
    }
}

export { PerformanceProfiler };
