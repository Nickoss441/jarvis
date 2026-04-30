# Planes Tab Hardening Checklist

## Production Readiness for Flight Digital Twin System

This checklist ensures the Planes tab meets production standards for security, reliability, performance, and operations.

---

## Security

### API Endpoints
- [ ] `/hud/air/states` rate-limited to prevent abuse (10 req/min per IP)
- [ ] OpenSky API credentials stored in `config.py`, not hardcoded
- [ ] Input validation on `/hud/air/flight/{id}` and `/hud/air/route/{id}` (alphanumeric IDs only)
- [ ] CORS headers configured to allow only trusted origins
- [ ] No sensitive data in error responses (generic "Error 500" messages)
- [ ] API responses logged without PII (aircraft ID hashed if needed)

### Frontend
- [ ] ESLint configured to catch XSS vulnerabilities
- [ ] Content Security Policy (CSP) header enforced
- [ ] No inline scripts in `planes.html` (all code in modules)
- [ ] Third-party CDN dependencies (Globe.gl, Mapbox) verified for security
- [ ] Mapbox token restricted to specific domains in Mapbox dashboard

### Data Privacy
- [ ] OpenSky data usage complies with their T&Cs (non-commercial, attribution)
- [ ] Flight data not stored in browser localStorage
- [ ] Session data cleared on page close
- [ ] No analytics/tracking without user consent

---

## Reliability

### Error Recovery
- [ ] AirBridge falls back gracefully (live → cached → mock) ✓
- [ ] All renderers handle null camera states
- [ ] Renderer transitions never leave screen blank (both visible during fade)
- [ ] Polling resumes after network disconnect (with exponential backoff)
- [ ] Smoke test covers failure scenarios (API down, timeout, malformed data)

### Data Consistency
- [ ] Aircraft state never partially updated (atomic updates only)
- [ ] Selected flight cleared if aircraft no longer in list
- [ ] Camera state preserved across renderer transitions
- [ ] Duplicate aircraft IDs impossible (Set-based deduplication)

### State Machine
- [ ] Clear state transitions: IDLE → GLOBE → MAP → GLOBE
- [ ] No orphaned renderers after transition (both disposed properly)
- [ ] LOD altitude thresholds never conflict (GLOBE_TO_MAP < MAP_TO_CITY < CITY_TO_MAP < MAP_TO_GLOBE)
- [ ] Altitude conversion functions (zoom ↔ meters) tested with boundary values

### Monitoring
- [ ] Health check endpoint `/hud/air/states` returns `state` field (LIVE/STALE/ERROR)
- [ ] Logs capture: fetch latency, cache hits, fallback triggers, errors
- [ ] Dashboard shows data state badge (green/amber/red)
- [ ] Alerts trigger on: 3+ consecutive API failures, cache invalidation, render hang

---

## Performance

### Targets
- [ ] **FPS**: ≥30 FPS on desktop (Chrome 90+), ≥20 FPS on mobile
- [ ] **Initial load**: <2s (planes.html + renderers + first aircraft poll)
- [ ] **Aircraft update**: <100ms (list update, marker placement, camera prep)
- [ ] **Transition**: <500ms (fade animation between renderers)
- [ ] **Memory**: <150 MB heap (desktop), <100 MB (mobile)

### Optimization
- [ ] Aircraft points pooled/reused (no new objects per frame)
- [ ] Frustum culling enabled (only render visible buildings in Mapbox)
- [ ] Terrain disabled by default (optional toggle with warning if device slow)
- [ ] deck.gl overlay only enabled if `DeckGLRenderer.canHandle(aircraftCount)` ✓
- [ ] Animation loop throttled to monitor refresh rate (requestAnimationFrame)
- [ ] Polling interval adaptive (5s if live, 10s if fallback)

### Load Testing
- [ ] PerformanceProfiler integrated into planes.html
- [ ] Smoke test runs profiling for 30s, outputs FPS/memory stats
- [ ] Tested with: 10, 100, 500, 1000+ mock aircraft
- [ ] Memory leak detection: heap snapshot before/after 1h test
- [ ] Stress test: rapid selection → transition → deselect → repeat

---

## Operations

### Deployment
- [ ] `smoke_test_planes.py` passes on staging before production
- [ ] OpenSky API credentials rotated quarterly
- [ ] Mapbox token refresh procedure documented
- [ ] Rollback plan: if `/hud/air/states` fails, serve static demo data
- [ ] Deployment checklist includes: cache TTL validation, API endpoint verification

### Monitoring & Alerting
- [ ] Prometheus metrics exposed at `/hud/metrics` (optional):
  - `planes_air_fetch_duration_ms`
  - `planes_cache_hit_rate`
  - `planes_renderer_fps`
  - `planes_memory_heap_mb`
- [ ] Alerts configured for:
  - Air fetch latency > 5s (3 occurrences → warn)
  - Data state ERROR for >5 min → critical alert
  - FPS < 20 → performance regression alert

### Runbooks
- [ ] [docs/runbooks/opensky-integration.md](../runbooks/opensky-integration.md) ✓
- [ ] Troubleshooting guide for common issues (see runbook)
- [ ] Recovery procedures for: API outage, rate limit, memory spike
- [ ] Escalation path: Debug info → Alert → On-call → incident

### Logging
- [ ] Backend logs to `approval_api.log`:
  ```
  [air_bridge] FETCH /hud/air/states: 245ms, 1200 aircraft, state=LIVE
  [air_bridge] CACHE HIT: 10s TTL, reusing 1200 aircraft
  [air_bridge] FALLBACK: OpenSky timeout, serving cached data (STALE)
  ```
- [ ] Frontend logs to console + optional remote logger:
  ```
  [AirDataService] Fetch error: HTTP 429, retrying in 30s
  [RendererManager] Transition: globe → mapbox, 450ms
  [Planes] Updated 1200 aircraft, FPS: 45
  ```

### Backup & Disaster Recovery
- [ ] Mock aircraft data embedded in `air_bridge.py` (always available)
- [ ] config.py with OpenSky credentials backed up in secure vault
- [ ] Planes.html static asset cached by browser (offline fallback)
- [ ] Database/audit log backup: none required (data is ephemeral)

---

## Testing

### Unit Tests
- [ ] `test_air_bridge.py`: cache TTL, OpenSky normalization, fallback logic ✓
- [ ] `test_air_data_schema.py`: DTO creation, serialization, type safety
- [ ] JS: AircraftState, CameraState, SelectedFlightState instantiation
- [ ] JS: AirDataService subscription model, polling lifecycle

### Integration Tests
- [ ] End-to-end: page load → poll → render → select → transition → reset ✓
- [ ] Renderer switching: GLOBE → MAP → GLOBE under 500ms ✓
- [ ] Error recovery: API timeout → fallback → manual retry
- [ ] Cache behavior: live → stale → live transition

### Smoke Tests
- [ ] `smoke_test_planes.py` validates:
  - Backend endpoints respond ✓
  - AirBridge produces valid aircraft ✓
  - Planes page loads ✓
  - Integration scenario completes ✓

### Performance Tests
- [ ] Profile runs included in CI/CD (threshold check)
- [ ] Desktop: 60 FPS target on Chrome with 500 aircraft
- [ ] Mobile: 30 FPS target on iOS Safari with 100 aircraft
- [ ] Memory: no growth after 10k frame cycles
- [ ] Stress: survive 10 rapid selection changes without crash

### Browser Compatibility
- [ ] Chrome 90+ (primary)
- [ ] Firefox 88+ (secondary)
- [ ] Safari 14+ (tertiary, Mapbox token required)
- [ ] Mobile: iOS Safari 14+, Chrome Android 90+

---

## Documentation

- [x] [OpenSky Integration Runbook](../runbooks/opensky-integration.md) ✓
- [ ] API Contract Doc: `/hud/air/*` endpoint specifications
- [ ] Architecture Doc: LOD system, renderer manager, state flow
- [ ] Troubleshooting Guide: common errors, recovery steps
- [ ] Performance Tuning Guide: cache TTL, poll interval, CDN selection

---

## Sign-Off

- [ ] Product Owner: Feature complete and meets requirements
- [ ] QA Lead: All tests green, no critical bugs
- [ ] DevOps: Monitoring, alerting, and runbooks ready
- [ ] Security: API protected, credentials managed, no sensitive data exposed
- [ ] Performance: Meets FPS/memory targets under load

**Approval Date**: _____  
**Approved By**: _____  
**Production Release Date**: _____
