# OpenSky Flight Data Integration Runbook

## Overview

The Planes tab uses the **OpenSky Network** API as the primary live data source for aircraft tracking. This runbook covers configuration, rate limiting, error handling, and troubleshooting.

## OpenSky API Details

- **Endpoint**: `https://opensky-network.org/api/states/all`
- **Free Tier Limits**: ~400 requests per hour (~6-7 per minute)
- **Timeout**: 10 seconds (production)
- **Response Format**: JSON with state vectors array

### API Response Fields

```json
{
  "icao24": "string",           // ICAO 24-bit aircraft identifier
  "callsign": "string",         // Flight callsign (may be null)
  "origin_country": "string",   // Country of registration
  "time_position": "integer",   // Last position timestamp
  "last_contact": "integer",    // Last API contact timestamp
  "longitude": "float",         // WGS-84 longitude
  "latitude": "float",          // WGS-84 latitude
  "baro_altitude": "float",     // Barometric altitude in meters
  "on_ground": "boolean",       // Ground status
  "velocity": "float",          // Velocity in m/s
  "true_track": "float",        // True track heading in degrees
  "vertical_rate": "float",     // Vertical rate in m/s
  "sensors": "[integer]",       // Receiver IDs contributing data
  "geo_altitude": "float"       // Geometric altitude in meters
}
```

## Configuration

### Backend (Python)

File: `jarvis/air_bridge.py`

```python
# Key configuration constants
OPENSKY_URL = "https://opensky-network.org/api/states/all"
OPENSKY_TIMEOUT = 10  # seconds
CACHE_TTL = 10  # 10 second cache
RATE_LIMIT_THRESHOLD = 2  # min requests per minute
```

### Optional: Authenticated Access

For higher rate limits, create an OpenSky account and configure credentials:

```python
# In air_bridge.py, modify _fetch_opensky:
auth = ("username", "password")
with urlopen(OPENSKY_URL, timeout=OPENSKY_TIMEOUT, auth=auth) as response:
    data = json.loads(response.read().decode())
```

**Benefits of authentication**:
- Increases rate limit to ~4000 requests/hour (~66/minute)
- Priority for large area requests
- Reduced latency

## Rate Limiting

The service implements a **caching strategy** to stay within free tier limits:

1. **Cache TTL**: 10 seconds (minimum between requests)
2. **Request Throttling**: Frontend polls at 5-second intervals, backend cache serves within 10-second window
3. **Error Recovery**: Falls back to cached data if live source unavailable

### Monitoring Rate Limits

Watch for HTTP 429 responses or delay messages in logs:

```
[AirBridge] OpenSky fetch failed: HTTP 429: Too Many Requests
[AirBridge] Returning cached or fallback data
```

### Handling Rate Limits

If rate-limited:

1. **Increase cache TTL**: `CACHE_TTL = 15` (up to 20s acceptable)
2. **Reduce frontend poll interval**: Change from 5s to 10s in `planes.html`
3. **Upgrade to authenticated access** (recommended for production)
4. **Implement request batching**: Pool regional requests instead of global

## Error Handling

### Common Errors

| Error | Cause | Recovery |
|-------|-------|----------|
| HTTP 401/403 | Auth credentials invalid | Verify OpenSky username/password |
| HTTP 429 | Rate limit exceeded | Wait 60s, increase cache TTL, or upgrade |
| HTTP 500/503 | OpenSky service unavailable | Return cached data, retry in 30s |
| Timeout | Network latency/connection lost | Fallback to mock or cached data |
| Parse error | Corrupted response | Log and skip, retry next poll |

### Fallback Strategy

When live data fails, the service hierarchy is:

1. **Live**: Direct OpenSky API call (~10s latency)
2. **Cached**: Use last successful response (marked STALE)
3. **Mock**: Demo dataset for UI testing (marked ERROR)

See `DataState` enum in `air_data_schema.py`:
- `LIVE`: Current data from API
- `STALE`: Cached data (live source unavailable)
- `ERROR`: Mock/fallback data

## Performance Tuning

### Backend

```python
# Adjust for your environment
CACHE_TTL = 10  # 5-15s recommended
OPENSKY_TIMEOUT = 10  # Lower if network is fast, higher if unreliable
```

### Frontend

```javascript
// In planes.html
const airService = new AirDataService("/hud/air", 5000); // Poll interval
// Increase to 10000 (10s) if hitting rate limits
```

### Monitoring

Check performance in browser DevTools Console:

```javascript
// Get service stats
console.log(airService.getSecondsSinceLastFetch());
console.log(rendererManager.getPerformanceStats());
```

## Troubleshooting

### Issue: "DATA SYNC: ERROR" badge appears

**Check**:
1. OpenSky API status: https://opensky-network.org/
2. Network connectivity: `curl https://opensky-network.org/api/states/all`
3. Firewall/proxy blocking: Check browser network tab (F12)
4. Rate limit: Look for HTTP 429 responses

**Recovery**:
- Wait 60 seconds for rate limit reset
- Check OpenSky status page
- Verify network connectivity
- Increase backend cache TTL temporarily

### Issue: Aircraft not updating

**Check**:
1. Is polling active? Check browser console for `[Planes]` logs
2. Is renderer manager initialized? Should see "Renderers initialized"
3. Check network tab (F12) for `/hud/air/states` requests
4. Is data state LIVE or STALE?

**Recovery**:
- Reload page
- Check logs: `tail -f /var/log/jarvis/approval_api.log`
- Verify `/hud/air/states` endpoint: `curl http://127.0.0.1:8080/hud/air/states`

### Issue: Frequent transitions between LIVE/STALE/ERROR

**Root cause**: Network instability or rate limit approaching

**Solutions**:
1. Increase cache TTL: `CACHE_TTL = 15`
2. Reduce frontend poll frequency: `5000ms` → `10000ms`
3. Add circuit breaker: Skip fetches temporarily after 3 consecutive failures
4. Upgrade to authenticated OpenSky access

### Issue: Renderers not initializing (blank screen)

**Check**:
1. Browser console for errors (F12)
2. Do Globe.gl and Mapbox scripts load? Check Network tab
3. Is Mapbox token configured?

**Recovery**:
- Check browser compatibility (Chrome 90+, Firefox 88+)
- Verify CDN URLs are accessible
- Check Mapbox token in `/hud/globe/config` endpoint
- Try private/incognito mode to bypass cache issues

## Deployment Checklist

Before production, verify:

- [ ] OpenSky API access working (test with curl)
- [ ] Cache TTL set appropriately (10-15s)
- [ ] Rate limit monitoring in place
- [ ] Fallback data looks reasonable
- [ ] Error badges display correctly in UI
- [ ] Smoke test passes (select flight → transition → reset)
- [ ] Logs clean (no repeated errors)
- [ ] Load testing done (100+ concurrent requests)
- [ ] Authentication configured (if upgrading to paid tier)
- [ ] Monitoring/alerting for data quality

## Metrics to Track

For operational visibility, monitor:

```python
# Backend metrics
- /hud/air/states response time (target: <500ms)
- Cache hit rate (target: >80%)
- Error rate (target: <1%)
- OpenSky API failures per hour
- Average aircraft count per poll

# Frontend metrics
- Data state transitions (LIVE → STALE → ERROR)
- Polling latency (time from request to response)
- Renderer FPS during aircraft updates
- Selection → transition time
```

## References

- **OpenSky Network**: https://opensky-network.org/
- **OpenSky API Docs**: https://opensky-network.org/api/
- **Rate Limit Docs**: https://opensky-network.org/api/doc#about
- **Status Page**: https://status.opensky-network.org/
