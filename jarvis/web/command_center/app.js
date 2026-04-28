// ── Datasets Panel ──────────────────────────────────────────────────────────
function DatasetsCard() {
    const [files, setFiles] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState("");
    const [uploading, setUploading] = React.useState(false);
    const fileInputRef = React.useRef(null);

    const fetchFiles = async () => {
        setLoading(true); setError("");
        try {
            const { data, error } = await fetchJsonResult("/local/files", { timeoutMs: 3000 });
            if (error) throw error;
            setFiles(Array.isArray(data.files) ? data.files : []);
        } catch (err) {
            setError("Could not load file list");
        } finally {
            setLoading(false);
        }
    };

    React.useEffect(() => { fetchFiles(); }, []);

    const handleUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true); setError("");
        const form = new FormData();
        form.append("file", file);
        try {
            const res = await fetch("/local/upload", { method: "POST", body: form });
            const j = await res.json();
            if (!j.ok) throw new Error(j.error || "Upload failed");
            fetchFiles();
        } catch (err) {
            setError("Upload failed");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleDownload = (fname) => {
        const url = `/local/file?name=${encodeURIComponent(fname)}`;
        const a = document.createElement("a");
        a.href = url;
        a.download = fname;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => document.body.removeChild(a), 500);
    };

    return React.createElement(
        "div", { className: "cc-card cc-card-datasets", "data-accent": "cyan" },
        React.createElement("div", { className: "cc-section-title" }, "Datasets"),
        React.createElement("div", { style: { marginBottom: 8 } },
            React.createElement("input", {
                type: "file", ref: fileInputRef, style: { display: "none" },
                onChange: handleUpload, disabled: uploading
            }),
            React.createElement("button", {
                className: "cc-runtime-btn", style: { fontSize: 12, marginRight: 8 },
                onClick: () => fileInputRef.current?.click(), disabled: uploading
            }, uploading ? "Uploading…" : "Upload File"),
            React.createElement("button", {
                className: "cc-runtime-btn", style: { fontSize: 12 },
                onClick: fetchFiles, disabled: loading
            }, loading ? "Refreshing…" : "Refresh List")
        ),
        React.createElement("div", { style: { color: "#22d3ee", fontSize: 12, marginBottom: 8, marginTop: 2 } },
            "For large files (>200KB), drag and drop them directly into D:\\jarvis-data. They will appear here after you refresh."
        ),
        error && React.createElement("div", { style: { color: "#ff453a", fontSize: 12, marginBottom: 8 } }, error),
        React.createElement(
            "div", { className: "cc-datasets-list" },
            files.length === 0 && !loading
                ? React.createElement("div", { style: { color: "var(--text3)", fontSize: 12 } }, "No files found.")
                : files.map(fname =>
                    React.createElement(
                        "div", { key: fname, className: "cc-dataset-row" },
                        React.createElement("span", { className: "cc-dataset-fname" }, fname),
                        React.createElement("button", {
                            className: "cc-runtime-btn", style: { fontSize: 11, marginLeft: 8 },
                            onClick: () => handleDownload(fname)
                        }, "Download")
                    )
                )
        )
    );
}
import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

// ── market data ───────────────────────────────────────────────────────────────
const MARKETS = [
    { id: "nyse", name: "NYSE", city: "New York", tz: "America/New_York", openH: 9, openM: 30, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "nasdaq", name: "NASDAQ", city: "New York", tz: "America/New_York", openH: 9, openM: 30, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "tsx", name: "TSX", city: "Toronto", tz: "America/Toronto", openH: 9, openM: 30, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "lse", name: "LSE", city: "London", tz: "Europe/London", openH: 8, openM: 0, closeH: 16, closeM: 30, days: [1, 2, 3, 4, 5] },
    { id: "eur", name: "Euronext", city: "Paris", tz: "Europe/Paris", openH: 9, openM: 0, closeH: 17, closeM: 30, days: [1, 2, 3, 4, 5] },
    { id: "fwb", name: "Xetra", city: "Frankfurt", tz: "Europe/Berlin", openH: 9, openM: 0, closeH: 17, closeM: 30, days: [1, 2, 3, 4, 5] },
    { id: "bse", name: "BSE", city: "Mumbai", tz: "Asia/Kolkata", openH: 9, openM: 15, closeH: 15, closeM: 30, days: [1, 2, 3, 4, 5] },
    { id: "sgx", name: "SGX", city: "Singapore", tz: "Asia/Singapore", openH: 9, openM: 0, closeH: 17, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "hkex", name: "HKEX", city: "Hong Kong", tz: "Asia/Hong_Kong", openH: 9, openM: 30, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "sse", name: "SSE", city: "Shanghai", tz: "Asia/Shanghai", openH: 9, openM: 30, closeH: 15, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "tse", name: "TSE", city: "Tokyo", tz: "Asia/Tokyo", openH: 9, openM: 0, closeH: 15, closeM: 0, days: [1, 2, 3, 4, 5] },
    { id: "asx", name: "ASX", city: "Sydney", tz: "Australia/Sydney", openH: 10, openM: 0, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
];

// ── helpers ───────────────────────────────────────────────────────────────────
function localParts(date, tz) {
    const dtf = new Intl.DateTimeFormat("en-US", {
        timeZone: tz, hour12: false,
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "short",
    });
    const p = Object.fromEntries(dtf.formatToParts(date).map(x => [x.type, x.value]));
    const dow = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 }[p.weekday] ?? 0;
    return { y: +p.year, mo: +p.month, d: +p.day, h: +(p.hour === "24" ? 0 : p.hour), mi: +p.minute, dow };
}

function wallToUTC(now, tz, dayOff, h, mi) {
    const lp = localParts(now, tz);
    const asUTC = Date.UTC(lp.y, lp.mo - 1, lp.d, lp.h, lp.mi, 0);
    const offset = asUTC - now.getTime();
    const midnight = Date.UTC(lp.y, lp.mo - 1, lp.d);
    return midnight + dayOff * 86400e3 + h * 3600e3 + mi * 60e3 - offset;
}

function marketStatus(m, now) {
    const lp = localParts(now, m.tz);
    const openUTC = wallToUTC(now, m.tz, 0, m.openH, m.openM);
    const closeUTC = wallToUTC(now, m.tz, 0, m.closeH, m.closeM);
    const ms = now.getTime();
    if (m.days.includes(lp.dow) && ms >= openUTC && ms < closeUTC) {
        return { open: true, deltaMs: closeUTC - ms };
    }
    // next open
    for (let off = 0; off < 8; off++) {
        const probeDow = (lp.dow + off) % 7;
        const probeOpen = wallToUTC(now, m.tz, off, m.openH, m.openM);
        if (m.days.includes(probeDow) && probeOpen > ms) {
            return { open: false, deltaMs: probeOpen - ms };
        }
    }
    return { open: false, deltaMs: 0 };
}

function fmtCountdown(ms) {
    if (ms <= 0) return "";
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function fmtTime(d) {
    return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function fmtUTC(d) {
    const p = n => String(n).padStart(2, "0");
    return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}

function fmtDate(d) {
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function localTZName() {
    try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        // get short abbreviation e.g. "EDT", "PST"
        const abbr = new Intl.DateTimeFormat("en-US", { timeZoneName: "short", timeZone: tz })
            .formatToParts(new Date())
            .find(p => p.type === "timeZoneName")?.value ?? tz;
        return abbr;
    } catch (_) { return ""; }
}

function fmtPrice(n) {
    if (n >= 1000) return "$" + Math.round(n).toLocaleString("en-US");
    if (n >= 1) return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 });
}

function detectCardNetwork(cardNumberDigits) {
    if (/^4\d{12}(\d{3})?(\d{3})?$/.test(cardNumberDigits)) return "visa";
    if (/^(5[1-5]\d{14}|2(2[2-9]\d{12}|[3-7]\d{13}))$/.test(cardNumberDigits)) return "mastercard";
    if (/^3[47]\d{13}$/.test(cardNumberDigits)) return "amex";
    if (/^(6011\d{12}|65\d{14}|64[4-9]\d{13})$/.test(cardNumberDigits)) return "discover";
    return "unknown";
}

const FETCH_ERROR_TYPES = {
    TIMEOUT: "timeout",
    HTTP: "http",
    NETWORK: "network",
    PARSE: "parse",
    UNKNOWN: "unknown",
};

function makeFetchError(type, message, extra = {}) {
    const status = typeof extra.status === "number" ? extra.status : null;
    return {
        type,
        message,
        status,
        url: extra.url ?? null,
        retryable: type === FETCH_ERROR_TYPES.TIMEOUT
            || type === FETCH_ERROR_TYPES.NETWORK
            || (type === FETCH_ERROR_TYPES.HTTP && (status === 429 || status >= 500)),
    };
}

function normalizeFetchError(err, url = null) {
    if (err && typeof err === "object" && typeof err.type === "string") {
        return err;
    }
    if (err?.name === "AbortError") {
        return makeFetchError(FETCH_ERROR_TYPES.TIMEOUT, "Request timed out", { url });
    }
    const raw = String(err?.message || err || "");
    const httpCode = raw.match(/http[_\s:](\d{3})/i);
    if (httpCode) {
        const status = Number(httpCode[1]);
        return makeFetchError(FETCH_ERROR_TYPES.HTTP, `HTTP ${status}`, { status, url });
    }
    if (raw.toLowerCase().includes("json")) {
        return makeFetchError(FETCH_ERROR_TYPES.PARSE, "Invalid JSON response", { url });
    }
    if (raw) {
        return makeFetchError(FETCH_ERROR_TYPES.NETWORK, raw, { url });
    }
    return makeFetchError(FETCH_ERROR_TYPES.UNKNOWN, "Unknown fetch failure", { url });
}

async function fetchJsonResult(url, options = {}) {
    const {
        timeoutMs = 3000,
        method = "GET",
        headers = { Accept: "application/json" },
        cache = "no-store",
        body,
    } = options;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, {
            signal: controller.signal,
            cache,
            method,
            headers,
            body,
        });
        if (!response.ok) {
            return {
                data: null,
                error: makeFetchError(FETCH_ERROR_TYPES.HTTP, `HTTP ${response.status}`, {
                    status: response.status,
                    url,
                }),
            };
        }
        try {
            const data = await response.json();
            return { data, error: null };
        } catch (err) {
            return {
                data: null,
                error: makeFetchError(FETCH_ERROR_TYPES.PARSE, "Invalid JSON response", { url }),
            };
        }
    } catch (err) {
        return {
            data: null,
            error: normalizeFetchError(err, url),
        };
    } finally {
        clearTimeout(timer);
    }
}

async function safeFetchJson(url, timeoutMs = 3000) {
    const { data } = await fetchJsonResult(url, { timeoutMs });
    return data;
}

function isStaleByAge(lastOkMs, thresholdMs) {
    return Number.isFinite(lastOkMs) && lastOkMs > 0 && (Date.now() - lastOkMs) > thresholdMs;
}

// ── hooks ─────────────────────────────────────────────────────────────────────

function useBrainStream() {
    const [events, setEvents] = React.useState([]);
    const [status, setStatus] = React.useState("connecting");
    const [lastEventAt, setLastEventAt] = React.useState(0);
    const [retryMs, setRetryMs] = React.useState(1200);
    React.useEffect(() => {
        let closed = false;
        let es = null;
        let reconnectTimer = null;
        let nextRetryMs = 1200;

        const scheduleReconnect = () => {
            if (closed || reconnectTimer) return;
            setStatus("reconnecting");
            setRetryMs(nextRetryMs);
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connect();
            }, nextRetryMs);
            nextRetryMs = Math.min(12000, Math.floor(nextRetryMs * 1.7));
        };

        const connect = () => {
            if (closed) return;
            setStatus("connecting");
            try {
                es = new EventSource("/hud/stream");
            } catch (_) {
                scheduleReconnect();
                return;
            }
            es.onmessage = e => {
                nextRetryMs = 1200;
                setRetryMs(1200);
                setStatus("live");
                try {
                    const row = JSON.parse(e.data);
                    setLastEventAt(Date.now());
                    setEvents(prev => [...prev.slice(-7), row]);
                } catch (_) { }
            };
            es.onerror = () => {
                if (closed) return;
                try { es?.close(); } catch (_) { }
                es = null;
                scheduleReconnect();
            };
        };

        connect();
        return () => {
            closed = true;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            try { es?.close(); } catch (_) { }
        };
    }, []);
    return { events, status, lastEventAt, retryMs };
}

function brainEventLabel(row) {
    const k = row.kind;
    const p = row.payload || {};
    if (k === "tool_call") return `→ ${p.name || "tool"}`;
    if (k === "tool_result") return `← ${p.name || "tool"}`;
    if (k === "user_input") return `INPUT: ${(p.text || "").slice(0, 60)}`;
    if (k === "llm_response") {
        const blocks = p.content || [];
        const text = blocks.find(b => b.type === "text")?.text || "";
        return `THOUGHT: ${text.slice(0, 80)}`;
    }
    return k.toUpperCase().replace(/_/g, " ");
}

function useClock() {
    const [now, setNow] = React.useState(() => new Date());
    React.useEffect(() => {
        const t = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(t);
    }, []);
    return now;
}

function useHealth() {
    const [state, setState] = React.useState(() => {
        try {
            const raw = localStorage.getItem("cc:lastHealth");
            const parsed = raw ? JSON.parse(raw) : null;
            const hasData = !!(parsed && typeof parsed === "object");
            return {
                data: hasData ? parsed : null,
                lastOkMs: hasData ? Date.now() : 0,
                stale: false,
                lastErrorType: "",
            };
        } catch (_) {
            return { data: null, lastOkMs: 0, stale: false, lastErrorType: "" };
        }
    });
    React.useEffect(() => {
        let dead = false;
        const go = async () => {
            const { data: next, error } = await fetchJsonResult("/health", { timeoutMs: 2800 });
            if (dead) return;
            if (next) {
                const nowMs = Date.now();
                const cacheAgeSec = Number(next.cache_age_seconds ?? 0);
                const stale = cacheAgeSec > 20;
                setState({
                    data: next,
                    lastOkMs: nowMs,
                    stale,
                    lastErrorType: "",
                });
                try { localStorage.setItem("cc:lastHealth", JSON.stringify(next)); } catch (_) { }
                return;
            }
            setState(prev => ({
                ...prev,
                stale: isStaleByAge(prev.lastOkMs, 30000),
                lastErrorType: error?.type || "unknown",
            }));
        };
        go();
        const t = setInterval(go, 8000);
        return () => { dead = true; clearInterval(t); };
    }, []);
    return state;
}

function usePending() {
    const [state, setState] = React.useState(() => {
        try {
            const raw = localStorage.getItem("cc:lastPending");
            const parsed = raw ? Number(raw) : null;
            return {
                count: Number.isFinite(parsed) ? parsed : null,
                lastOkMs: Number.isFinite(parsed) ? Date.now() : 0,
                stale: false,
                lastErrorType: "",
            };
        } catch (_) {
            return { count: null, lastOkMs: 0, stale: false, lastErrorType: "" };
        }
    });
    React.useEffect(() => {
        let dead = false;
        const go = async () => {
            const { data: j, error } = await fetchJsonResult("/approvals/pending?limit=100", { timeoutMs: 2800 });
            if (dead) return;
            if (j) {
                const count = Array.isArray(j.items) ? j.items.length : 0;
                setState({ count, lastOkMs: Date.now(), stale: false, lastErrorType: "" });
                try { localStorage.setItem("cc:lastPending", String(count)); } catch (_) { }
                return;
            }
            setState(prev => ({
                ...prev,
                stale: isStaleByAge(prev.lastOkMs, 30000),
                lastErrorType: error?.type || "unknown",
            }));
        };
        go();
        const t = setInterval(go, 8000);
        return () => { dead = true; clearInterval(t); };
    }, []);
    return state;
}

// ── market data sources ───────────────────────────────────────────────────────
const CG = "https://api.coingecko.com/api/v3";
const BINANCE = "https://api.binance.com/api/v3";
const METALS = "/hud/metals";
const METALS_TIMEOUT_MS = 2800;
const METALS_POLL_MS = 15000;
const ASSET_PRICE_POLL_MS = METALS_POLL_MS;
const ASSET_CHART_LIVE_POLL_MS = METALS_POLL_MS * 2;
const ASSET_CHART_WINDOW_POLL_MS = 60000;
const POLL_JITTER_MS = 900;

function scheduleCadencedPoll(run, intervalMs, jitterMs = POLL_JITTER_MS) {
    let dead = false;
    let timer = null;
    const loop = async () => {
        if (dead) return;
        await run();
        if (dead) return;
        timer = setTimeout(loop, intervalMs + Math.floor(Math.random() * jitterMs));
    };
    timer = setTimeout(loop, intervalMs);
    return () => {
        dead = true;
        if (timer) clearTimeout(timer);
    };
}

// commodity metal assets — use metals.live, not Binance
const COMMODITY_META = {
    "commodity-gold": { metalKey: "gold", name: "Gold", symbol: "XAU", unit: "US$/oz" },
    "commodity-silver": { metalKey: "silver", name: "Silver", symbol: "XAG", unit: "US$/oz" },
    "commodity-platinum": { metalKey: "platinum", name: "Platinum", symbol: "XPT", unit: "US$/oz" },
    "commodity-palladium": { metalKey: "palladium", name: "Palladium", symbol: "XPD", unit: "US$/oz" },
};
const COMMODITY_IDS = new Set(Object.keys(COMMODITY_META));

const WINDOWS = [
    { label: "LIVE", mode: "live" },
    { label: "1m", mode: "binance", interval: "1m", limit: 120 },
    { label: "5m", mode: "binance", interval: "5m", limit: 120 },
    { label: "15m", mode: "binance", interval: "15m", limit: 96 },
    { label: "1h", mode: "binance", interval: "1h", limit: 72 },
    { label: "4h", mode: "binance", interval: "4h", limit: 84 },
    { label: "1D", mode: "binance", interval: "1d", limit: 90 },
];

// derive Binance symbol from CoinGecko coin symbol, e.g. btc → BTCUSDT
function binanceSymbol(symbol) {
    return symbol.toUpperCase() + "USDT";
}

// Downsample array to max N points for smooth rendering
function downsample(arr, max) {
    if (arr.length <= max) return arr;
    const step = (arr.length - 1) / (max - 1);
    return Array.from({ length: max }, (_, i) => arr[Math.round(i * step)]);
}

// Catmull-Rom smooth SVG path
function smoothPath(values, W, H) {
    if (values.length < 2) return { line: "", fill: "" };
    const pts = downsample(values, 80);
    const maxV = Math.max(...pts), minV = Math.min(...pts);
    const range = maxV - minV || 1;
    const xy = pts.map((v, i) => [
        (i / (pts.length - 1)) * W,
        H - ((v - minV) / range) * (H - 10) - 5,
    ]);
    const t = 0.38;
    let d = `M${xy[0][0].toFixed(1)},${xy[0][1].toFixed(1)}`;
    for (let i = 0; i < xy.length - 1; i++) {
        const p0 = xy[Math.max(0, i - 1)];
        const p1 = xy[i];
        const p2 = xy[i + 1];
        const p3 = xy[Math.min(xy.length - 1, i + 2)];
        const cp1x = p1[0] + (p2[0] - p0[0]) * t / 3;
        const cp1y = p1[1] + (p2[1] - p0[1]) * t / 3;
        const cp2x = p2[0] - (p3[0] - p1[0]) * t / 3;
        const cp2y = p2[1] - (p3[1] - p1[1]) * t / 3;
        d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
    }
    return { line: d, fill: `${d} L${W},${H} L0,${H} Z` };
}

// live tick buffer: coinId → [price, ...]
const _liveTicks = new Map();

// shared metals cache so multiple components don't hammer the API
let _metalsCache = null;
let _metalsCacheTs = 0;
let _metalsPromise = null;
let _metalsEndpointBlockedUntil = 0;
const METALS_FALLBACK = {
    gold: 2320.2,
    silver: 27.4,
    platinum: 978.0,
    palladium: 1048.0,
};

function getDriftedMetalsFallback() {
    const base = _metalsCache ?? METALS_FALLBACK;
    const drift = (v, pct) => Math.max(0, v * (1 + ((Math.random() - 0.5) * pct)));
    return {
        gold: drift(base.gold, 0.0014),
        silver: drift(base.silver, 0.0021),
        platinum: drift(base.platinum, 0.0018),
        palladium: drift(base.palladium, 0.0019),
    };
}

function parseMetalsPayload(raw) {
    const first = Array.isArray(raw) ? raw[0] : raw;
    if (!first || typeof first !== "object") return null;
    const gold = parseFloat(first.gold);
    const silver = parseFloat(first.silver);
    const platinum = parseFloat(first.platinum);
    const palladium = parseFloat(first.palladium);
    if ([gold, silver, platinum, palladium].every((v) => Number.isNaN(v))) {
        return null;
    }
    return {
        gold: Number.isNaN(gold) ? METALS_FALLBACK.gold : gold,
        silver: Number.isNaN(silver) ? METALS_FALLBACK.silver : silver,
        platinum: Number.isNaN(platinum) ? METALS_FALLBACK.platinum : platinum,
        palladium: Number.isNaN(palladium) ? METALS_FALLBACK.palladium : palladium,
    };
}

async function fetchJsonWithTimeout(url, timeoutMs) {
    const { data, error } = await fetchJsonResult(url, { timeoutMs });
    if (error) throw error;
    return data;
}

function fetchMetals() {
    const now = Date.now();
    if (now < _metalsEndpointBlockedUntil) {
        const fallback = getDriftedMetalsFallback();
        _metalsCache = fallback;
        _metalsCacheTs = now;
        return Promise.resolve(fallback);
    }
    if (_metalsCache && now - _metalsCacheTs < METALS_POLL_MS - 1000) {
        return Promise.resolve(_metalsCache);
    }
    if (_metalsPromise) return _metalsPromise;
    _metalsPromise = fetchJsonWithTimeout(METALS, METALS_TIMEOUT_MS)
        .then((j) => {
            const parsed = parseMetalsPayload(j);
            if (!parsed) throw new Error("invalid_metals_payload");
            _metalsCache = parsed;
            _metalsCacheTs = Date.now();
            _metalsPromise = null;
            return parsed;
        })
        .catch((err) => {
            _metalsPromise = null;
            const normalized = normalizeFetchError(err, METALS);
            if (normalized.type === FETCH_ERROR_TYPES.HTTP && [404, 501, 503].includes(normalized.status)) {
                // Endpoint is missing/unavailable on this runtime: back off aggressively.
                _metalsEndpointBlockedUntil = Date.now() + (5 * 60 * 1000);
            }
            if (_metalsCache) {
                return _metalsCache;
            }
            const fallback = getDriftedMetalsFallback();
            _metalsCache = fallback;
            _metalsCacheTs = Date.now();
            return fallback;
        });
    return _metalsPromise;
}

// price hook — branches on commodity vs crypto
function useAssetPrice(coinId, coinSymbol) {
    const [price, setPrice] = React.useState(null);
    const [delta, setDelta] = React.useState(0);
    const [loading, setLoading] = React.useState(true);
    const [flash, setFlash] = React.useState(null);
    const prevRef = React.useRef(null);

    React.useEffect(() => {
        if (!coinId || !coinSymbol) return;
        setPrice(null); setDelta(0); setLoading(true); prevRef.current = null;
        let active = true;

        if (COMMODITY_IDS.has(coinId)) {
            const meta = COMMODITY_META[coinId];
            const poll = async () => {
                try {
                    const data = await fetchMetals();
                    const p = parseFloat(data[meta.metalKey]);
                    if (isNaN(p) || !active) return;
                    if (prevRef.current !== null && p !== prevRef.current) {
                        setFlash(p > prevRef.current ? "up" : "down");
                        setTimeout(() => setFlash(null), 800);
                    }
                    prevRef.current = p;
                    const ticks = _liveTicks.get(coinId) ?? [];
                    ticks.push(p); if (ticks.length > 300) ticks.shift();
                    _liveTicks.set(coinId, ticks);
                    if (active) { setPrice(p); setDelta(0); setLoading(false); }
                } catch (_) { if (active) setLoading(false); }
            };
            poll();
            const stop = scheduleCadencedPoll(poll, ASSET_PRICE_POLL_MS);
            return () => { active = false; stop(); };
        }

        // crypto via Binance
        const sym = binanceSymbol(coinSymbol);
        const poll = async () => {
            try {
                const r = await fetch(`${BINANCE}/ticker/24hr?symbol=${sym}`);
                if (!r.ok || !active) return;
                const j = await r.json();
                const p = parseFloat(j.lastPrice);
                const d = parseFloat(j.priceChangePercent);
                if (prevRef.current !== null && p !== prevRef.current) {
                    setFlash(p > prevRef.current ? "up" : "down");
                    setTimeout(() => setFlash(null), 800);
                }
                prevRef.current = p;
                const ticks = _liveTicks.get(coinId) ?? [];
                ticks.push(p); if (ticks.length > 300) ticks.shift();
                _liveTicks.set(coinId, ticks);
                if (active) { setPrice(p); setDelta(d); setLoading(false); }
            } catch (_) { if (active) setLoading(false); }
        };
        poll();
        const stop = scheduleCadencedPoll(poll, ASSET_PRICE_POLL_MS);
        return () => { active = false; stop(); };
    }, [coinId, coinSymbol]);

    return { price, delta, loading, flash };
}

// chart-only hook — Binance klines or live buffer
function useAssetChart(coinId, coinSymbol, win) {
    const [sparkline, setSparkline] = React.useState([]);

    React.useEffect(() => {
        if (!coinId || !coinSymbol) return;
        setSparkline([]);
        let dead = false;
        const sym = binanceSymbol(coinSymbol);

        const load = async () => {
            try {
                if (COMMODITY_IDS.has(coinId)) {
                    if (!dead) setSparkline([...(_liveTicks.get(coinId) ?? [])]);
                    return;
                }
                if (win.mode === "live") {
                    const ticks = _liveTicks.get(coinId) ?? [];
                    if (ticks.length >= 3) {
                        if (!dead) setSparkline([...ticks]);
                        return;
                    }
                    // seed LIVE with recent 1m klines until ticks accumulate
                    const r = await fetch(`${BINANCE}/klines?symbol=${sym}&interval=1m&limit=60`);
                    if (!r.ok || dead) return;
                    const j = await r.json();
                    const seeded = j.map(k => parseFloat(k[4]));
                    // merge: seed + any live ticks collected so far
                    const merged = [...seeded, ...(_liveTicks.get(coinId) ?? [])];
                    if (!dead) setSparkline(merged);
                    return;
                }
                const r = await fetch(`${BINANCE}/klines?symbol=${sym}&interval=${win.interval}&limit=${win.limit}`);
                if (!r.ok) throw new Error(r.status);
                const j = await r.json();
                if (!dead) setSparkline(j.map(k => parseFloat(k[4])));
            } catch (_) { }
        };

        load();
        const stop = scheduleCadencedPoll(
            load,
            win.mode === "live" ? ASSET_CHART_LIVE_POLL_MS : ASSET_CHART_WINDOW_POLL_MS
        );
        return () => { dead = true; stop(); };
    }, [coinId, coinSymbol, win]);

    return sparkline;
}

// ── news hook ─────────────────────────────────────────────────────────────────
const NEWS_SOURCES = [
    { label: "Markets", sub: "investing" },
    { label: "World", sub: "worldnews" },
    { label: "Crypto", sub: "CryptoCurrency" },
    { label: "Tech", sub: "technology" },
];

function useNews(subreddit) {
    const [items, setItems] = React.useState([]);
    const [newIds, setNewIds] = React.useState(new Set());
    const [loading, setLoading] = React.useState(true);
    const [lastAt, setLastAt] = React.useState(null);
    const [stale, setStale] = React.useState(false);
    const seenRef = React.useRef(new Set());
    const lastOkRef = React.useRef(0);

    React.useEffect(() => {
        let dead = false;
        setLoading(true);
        seenRef.current = new Set();

        const load = async () => {
            try {
                const r = await fetch(
                    `https://www.reddit.com/r/${subreddit}/new.json?limit=25`,
                    { headers: { Accept: "application/json" } }
                );
                if (!r.ok) throw new Error("reddit");
                const j = await r.json();
                if (!dead) {
                    const posts = (j.data?.children ?? [])
                        .map(c => c.data)
                        .filter(d => !d.stickied)
                        .slice(0, 20);

                    const fresh = new Set(
                        posts.filter(p => !seenRef.current.has(p.id)).map(p => p.id)
                    );
                    posts.forEach(p => seenRef.current.add(p.id));

                    setItems(posts);
                    setNewIds(fresh);
                    setLastAt(new Date());
                    lastOkRef.current = Date.now();
                    setStale(false);
                    setLoading(false);

                    // clear "new" highlights after 6s
                    if (fresh.size) setTimeout(() => setNewIds(new Set()), 6000);
                }
            } catch (_) {
                if (!dead) {
                    setLoading(false);
                    setStale(isStaleByAge(lastOkRef.current, 180000));
                }
            }
        };

        load();
        const t = setInterval(load, 90 * 1000);
        return () => { dead = true; clearInterval(t); };
    }, [subreddit]);

    return { items, newIds, loading, lastAt, stale };
}

function timeAgo(utcSec) {
    const s = Math.floor(Date.now() / 1000 - utcSec);
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    if (s < 86400) return `${Math.floor(s / 3600)}h`;
    return `${Math.floor(s / 86400)}d`;
}

// persistent image cache keyed by post ID — survives feed refreshes
const _thumbCache = new Map();

function newsThumb(item) {
    if (_thumbCache.has(item.id)) return _thumbCache.get(item.id);
    const preview = item.preview?.images?.[0]?.resolutions?.slice(-1)[0]?.url?.replaceAll("&amp;", "&")
        || item.preview?.images?.[0]?.source?.url?.replaceAll("&amp;", "&");
    const url = preview || (item.thumbnail?.startsWith("http") ? item.thumbnail : null);
    // return null for text posts — no placeholder shown
    _thumbCache.set(item.id, url);
    return url;
}

function NewsCard() {
    const [srcIdx, setSrcIdx] = React.useState(0);
    const { items, newIds, loading, stale } = useNews(NEWS_SOURCES[srcIdx].sub);

    return React.createElement(
        "div", { className: "cc-card cc-card-news", "data-accent": "purple" },

        React.createElement(
            "div", { className: "cc-news-header" },
            React.createElement(
                "div", { style: { display: "flex", alignItems: "center", gap: 8 } },
                React.createElement("div", { className: "cc-section-title" }, "News Feed"),
                React.createElement("span", { className: "cc-live-dot" }),
                stale && React.createElement("span", { className: "cc-stale-pill" }, "stale")
            ),
            React.createElement(
                "div", { className: "cc-news-sources" },
                ...NEWS_SOURCES.map((s, i) =>
                    React.createElement("button", {
                        key: s.sub,
                        className: `cc-news-src${srcIdx === i ? " active" : ""}`,
                        onClick: () => setSrcIdx(i),
                    }, s.label)
                )
            )
        ),

        loading
            ? React.createElement("div", { className: "cc-loading-wrap" },
                React.createElement("div", { className: "cc-spinner" }))
            : React.createElement(
                "div", { className: "cc-news-scroll" },
                ...items.map(item => {
                    const thumb = newsThumb(item);
                    const initial = (item.domain ?? "?")[0].toUpperCase();
                    const isNew = newIds.has(item.id);
                    return React.createElement(
                        "a", {
                        key: item.id,
                        className: `cc-news-item${isNew ? " cc-news-item-new" : ""}`,
                        href: item.url,
                        target: "_blank",
                        rel: "noreferrer",
                    },
                        React.createElement(
                            "div", { className: "cc-news-row" },
                            thumb && React.createElement("img", {
                                className: "cc-news-thumb",
                                src: thumb,
                                alt: "",
                                loading: "lazy",
                                referrerPolicy: "no-referrer",
                                onError: e => { e.target.style.display = "none"; },
                            }),
                            React.createElement(
                                "div", { className: "cc-news-body" },
                                React.createElement("div", { className: "cc-news-title" }, item.title),
                                React.createElement(
                                    "div", { className: "cc-news-meta" },
                                    React.createElement("span", { className: "cc-news-domain" }, item.domain),
                                    React.createElement("span", null, timeAgo(item.created_utc)),
                                    React.createElement("span", { className: "cc-news-score" }, `▲ ${item.score.toLocaleString()}`)
                                )
                            )
                        )
                    );
                })
            )
    );
}

// keyword aliases: common terms → coin symbols / commodity ids to boost in results
const KEYWORD_ALIASES = {
    gold: ["commodity-gold", "paxg", "xaut"],
    silver: ["commodity-silver"],
    platinum: ["commodity-platinum"],
    palladium: ["commodity-palladium"],
    metals: ["commodity-gold", "commodity-silver"],
    oil: ["oilbtc", "crude"],
    btc: ["bitcoin"], bitcoin: ["btc"],
    eth: ["ethereum"], ethereum: ["eth"],
    sol: ["solana"], solana: ["sol"],
    bnb: ["binancecoin"], binance: ["bnb"],
    xrp: ["ripple"], ripple: ["xrp"],
    ada: ["cardano"], cardano: ["ada"],
    doge: ["dogecoin"], dogecoin: ["doge"],
    dot: ["polkadot"], polkadot: ["dot"],
    link: ["chainlink"], chainlink: ["link"],
    avax: ["avalanche-2"], avalanche: ["avax"],
    matic: ["matic-network"], polygon: ["matic"],
    ltc: ["litecoin"], litecoin: ["ltc"],
};

// hardcoded fallback — always available even if CoinGecko rate-limits
const FALLBACK_COINS = [
    // commodities first so they rank high when searching by keyword
    { id: "commodity-gold", name: "Gold", symbol: "XAU", market_cap_rank: 0 },
    { id: "commodity-silver", name: "Silver", symbol: "XAG", market_cap_rank: 0 },
    { id: "commodity-platinum", name: "Platinum", symbol: "XPT", market_cap_rank: 0 },
    { id: "commodity-palladium", name: "Palladium", symbol: "XPD", market_cap_rank: 0 },
    { id: "bitcoin", name: "Bitcoin", symbol: "btc", market_cap_rank: 1 },
    { id: "ethereum", name: "Ethereum", symbol: "eth", market_cap_rank: 2 },
    { id: "tether", name: "Tether", symbol: "usdt", market_cap_rank: 3 },
    { id: "binancecoin", name: "BNB", symbol: "bnb", market_cap_rank: 4 },
    { id: "solana", name: "Solana", symbol: "sol", market_cap_rank: 5 },
    { id: "ripple", name: "XRP", symbol: "xrp", market_cap_rank: 6 },
    { id: "usd-coin", name: "USD Coin", symbol: "usdc", market_cap_rank: 7 },
    { id: "cardano", name: "Cardano", symbol: "ada", market_cap_rank: 8 },
    { id: "avalanche-2", name: "Avalanche", symbol: "avax", market_cap_rank: 9 },
    { id: "dogecoin", name: "Dogecoin", symbol: "doge", market_cap_rank: 10 },
    { id: "polkadot", name: "Polkadot", symbol: "dot", market_cap_rank: 11 },
    { id: "chainlink", name: "Chainlink", symbol: "link", market_cap_rank: 12 },
    { id: "matic-network", name: "Polygon", symbol: "matic", market_cap_rank: 13 },
    { id: "litecoin", name: "Litecoin", symbol: "ltc", market_cap_rank: 14 },
    { id: "pax-gold", name: "PAX Gold", symbol: "paxg", market_cap_rank: 50 },
    { id: "tether-gold", name: "Tether Gold", symbol: "xaut", market_cap_rank: 55 },
    { id: "shiba-inu", name: "Shiba Inu", symbol: "shib", market_cap_rank: 15 },
    { id: "tron", name: "TRON", symbol: "trx", market_cap_rank: 16 },
    { id: "near", name: "NEAR Protocol", symbol: "near", market_cap_rank: 17 },
    { id: "stellar", name: "Stellar", symbol: "xlm", market_cap_rank: 18 },
];

let _marketList = null;
let _marketListTs = 0;
let _marketListPromise = null;
const MARKET_LIST_STORAGE_KEY = "cc:market-list:v1";
const MARKET_LIST_TTL_MS = 60 * 60 * 1000;

try {
    const raw = localStorage.getItem(MARKET_LIST_STORAGE_KEY);
    if (raw) {
        const parsed = JSON.parse(raw);
        const ts = Number(parsed?.ts || 0);
        const items = parsed?.items;
        if (Array.isArray(items) && items.length > 0) {
            _marketList = items;
            _marketListTs = ts > 0 ? ts : Date.now();
        }
    }
} catch (_) { }

function getMarketList() {
    const now = Date.now();
    if (_marketList && now - _marketListTs < MARKET_LIST_TTL_MS) return Promise.resolve(_marketList);
    if (_marketListPromise) return _marketListPromise;
    _marketListPromise = new Promise(res => setTimeout(res, 2000))
        .then(() => Promise.all([
            fetchJsonResult(`${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&sparkline=false`, { timeoutMs: 6000 }),
            fetchJsonResult(`${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=2&sparkline=false`, { timeoutMs: 6000 }),
        ]))
        .then(([p1r, p2r]) => {
            if (p1r.error) throw p1r.error;
            if (p2r.error) throw p2r.error;
            const p1 = p1r.data;
            const p2 = p2r.data;
            return [...(Array.isArray(p1) ? p1 : []), ...(Array.isArray(p2) ? p2 : [])];
        })
        .then(j => {
            _marketList = j;
            _marketListTs = Date.now();
            _marketListPromise = null;
            try {
                localStorage.setItem(MARKET_LIST_STORAGE_KEY, JSON.stringify({
                    ts: _marketListTs,
                    items: j,
                }));
            } catch (_) { }
            return j;
        })
        .catch(() => {
            _marketListPromise = null;
            setTimeout(() => { if (!_marketList) getMarketList(); }, 30000);
            return _marketList ?? FALLBACK_COINS;
        });
    return _marketListPromise;
}

function searchCoins(list, q) {
    const aliases = KEYWORD_ALIASES[q] ?? [];
    const boost = new Set(aliases);
    const score = c => {
        const sym = c.symbol.toLowerCase();
        const name = c.name.toLowerCase();
        if (sym === q || boost.has(sym) || boost.has(c.id)) return 0;
        if (sym.startsWith(q) || name.startsWith(q)) return 1;
        if (sym.includes(q) || name.includes(q)) return 2;
        return 99;
    };
    return list
        .map(c => ({ c, s: score(c) }))
        .filter(x => x.s < 99)
        .sort((a, b) => a.s - b.s || (a.c.market_cap_rank ?? 999) - (b.c.market_cap_rank ?? 999))
        .map(x => x.c)
        .slice(0, 8);
}

function useAssetSearch(query) {
    const [results, setResults] = React.useState([]);
    const [searching, setSearching] = React.useState(false);

    React.useEffect(() => {
        const q = query.trim().toLowerCase();
        if (q.length < 2) { setResults([]); setSearching(false); return; }

        // search fallback immediately so UI is never blank
        const instant = searchCoins(FALLBACK_COINS, q);
        setResults(instant);
        setSearching(true);

        let dead = false;
        getMarketList().then(list => {
            if (dead) return;
            const full = searchCoins(list.length ? list : FALLBACK_COINS, q);
            setResults(full);
            setSearching(false);
        });
        return () => { dead = true; };
    }, [query]);

    return { results, searching };
}

// ── watchlist ─────────────────────────────────────────────────────────────────
const WATCHLIST_KEY = "cc-watchlist-v1";
const DEFAULT_WATCHLIST = [
    { id: "bitcoin", name: "Bitcoin", symbol: "btc" },
    { id: "ethereum", name: "Ethereum", symbol: "eth" },
    { id: "commodity-gold", name: "Gold", symbol: "XAU" },
];

function useWatchlist() {
    const [list, setList] = React.useState(() => {
        try { return JSON.parse(localStorage.getItem(WATCHLIST_KEY)) || DEFAULT_WATCHLIST; }
        catch (_) { return DEFAULT_WATCHLIST; }
    });
    const save = items => { setList(items); localStorage.setItem(WATCHLIST_KEY, JSON.stringify(items)); };
    const add = coin => { if (!list.find(c => c.id === coin.id)) save([...list, { id: coin.id, name: coin.name, symbol: coin.symbol }]); };
    const remove = id => save(list.filter(c => c.id !== id));
    return { list, add, remove };
}

// compact row tile — click to select asset in main chart
function WatchTile({ coin, onRemove, onSelect }) {
    const { price, delta, loading, flash } = useAssetPrice(coin.id, coin.symbol);
    const up = (delta ?? 0) >= 0;
    const isCommodity = COMMODITY_IDS.has(coin.id);
    return React.createElement(
        "div", {
        className: "cc-watch-tile",
        onClick: () => onSelect({ id: coin.id, name: coin.name, symbol: coin.symbol }),
        title: `View ${coin.name} chart`,
    },
        // name + symbol
        React.createElement(
            "div", { className: "cc-watch-tile-top" },
            React.createElement("span", { className: "cc-watch-name" }, coin.name),
            React.createElement("span", { className: "cc-watch-sym" }, coin.symbol.toUpperCase())
        ),
        // price
        loading
            ? React.createElement("div", { className: "cc-spinner", style: { width: 9, height: 9, flexShrink: 0 } })
            : React.createElement("div", {
                className: `cc-watch-price${flash ? ` cc-price-flash-${flash}` : ""}`,
            }, price != null ? fmtPrice(price) : "—"),
        // delta or unit
        !loading && price != null && !isCommodity
            ? React.createElement("div", {
                className: `cc-delta ${up ? "up" : "down"}`,
                style: { fontSize: 7, padding: "1px 4px" },
            }, up ? "▲" : "▼", ` ${Math.abs(delta).toFixed(2)}%`)
            : !loading && isCommodity
                ? React.createElement("span", { style: { fontSize: 8, color: "var(--text3)", fontFamily: "var(--mono)" } }, "oz")
                : null,
        // remove button
        React.createElement("button", {
            className: "cc-watch-remove",
            style: { position: "static", marginLeft: "auto" },
            onClick: e => { e.stopPropagation(); onRemove(coin.id); },
            title: "Remove",
        }, "×")
    );
}

function WatchlistCard({ health, pending, pendingState, openMarkets, onSelectAsset }) {
    const { list, add, remove } = useWatchlist();
    const [addOpen, setAddOpen] = React.useState(false);
    const [query, setQuery] = React.useState("");
    const [focused, setFocused] = React.useState(false);
    const blurTimer = React.useRef(null);
    const { results, searching } = useAssetSearch(query);
    const dropOpen = focused && query.trim().length >= 2;

    const pick = coin => {
        add(coin);
        setQuery("");
        setFocused(false);
        setAddOpen(false);
    };

    const status = health?.status ?? "unknown";

    return React.createElement(
        "div", { className: "cc-card cc-card-watchlist", "data-accent": "cyan" },

        // compact header
        React.createElement(
            "div", { className: "cc-watch-header" },
            React.createElement(
                "div", { style: { display: "flex", alignItems: "center", gap: 6 } },
                React.createElement("span", { className: "cc-section-title" }, "Watchlist"),
                React.createElement("span", { className: "cc-live-dot" })
            ),
            React.createElement(
                "div", { className: "cc-watch-meta" },
                React.createElement("span", { className: "cc-watch-meta-item" },
                    `${openMarkets}/${MARKETS.length} mkts`),
                pending != null && React.createElement("span", { className: "cc-watch-meta-item" },
                    `${pending} pending`),
                pendingState?.stale && React.createElement("span", { className: "cc-stale-pill" }, "pending stale"),
                React.createElement("span", {
                    className: `cc-status-pill ${status}`,
                    style: { fontSize: 8, padding: "1px 6px" },
                },
                    React.createElement("span", { className: `cc-status-dot ${status}` }),
                    status === "ok" ? "OK" : "—"
                )
            )
        ),

        // vertical tiles list + add button at bottom
        React.createElement(
            "div", { style: { display: "flex", flexDirection: "column", gap: 4, flex: 1, minHeight: 0, overflow: "hidden" } },
            React.createElement(
                "div", { className: "cc-watch-tiles" },
                ...list.map(coin =>
                    React.createElement(WatchTile, {
                        key: coin.id, coin,
                        onRemove: remove,
                        onSelect: onSelectAsset,
                    })
                )
            ),
            // + button opens search popup
            React.createElement(
                "div", { className: "cc-watch-add-wrap" },
                React.createElement("button", {
                    className: "cc-watch-add-btn",
                    style: { width: "100%", height: 22, borderRadius: 5, fontSize: 13 },
                    onClick: () => { setAddOpen(v => !v); setQuery(""); },
                    title: "Add asset",
                }, "+"),
                addOpen && React.createElement(
                    "div", { className: "cc-watch-add-popup" },
                    React.createElement("input", {
                        className: "cc-search-input",
                        style: { width: "100%", borderRadius: 0, borderColor: "transparent", borderBottomColor: "rgba(0,220,255,0.15)", padding: "8px 12px", fontSize: 11 },
                        placeholder: "BTC, ETH, gold, SOL…",
                        autoFocus: true,
                        value: query,
                        onChange: e => { setQuery(e.target.value); clearTimeout(blurTimer.current); },
                        onFocus: () => { setFocused(true); clearTimeout(blurTimer.current); },
                        onBlur: () => { blurTimer.current = setTimeout(() => { setFocused(false); setAddOpen(false); }, 300); },
                        onKeyDown: e => {
                            if (e.key === "Enter" && results.length > 0) { e.preventDefault(); pick(results[0]); }
                            if (e.key === "Escape") { setAddOpen(false); setQuery(""); }
                        },
                    }),
                    dropOpen && (
                        results.length === 0
                            ? React.createElement("div", { style: { padding: "8px 12px", fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" } }, searching ? "Searching…" : "No results")
                            : results.map(coin =>
                                React.createElement("div", {
                                    key: coin.id, className: "cc-search-item",
                                    onMouseDown: e => { e.preventDefault(); pick(coin); }
                                },
                                    React.createElement("div", { className: "cc-search-item-left" },
                                        React.createElement("span", { className: "cc-search-item-name" }, coin.name),
                                        React.createElement("span", { className: "cc-search-item-sym" }, coin.symbol)
                                    ),
                                    coin.market_cap_rank
                                        ? React.createElement("span", { className: "cc-search-item-rank" }, `#${coin.market_cap_rank}`)
                                        : null
                                )
                            )
                    )
                )
            )
        )
    );
}

function useBars(init, ms = 2000) {
    const [bars, setBars] = React.useState(init);
    React.useEffect(() => {
        const t = setInterval(() => {
            setBars(prev => prev.map(b => Math.max(3, Math.min(28, b + (Math.random() - 0.5) * 8))));
        }, ms);
        return () => clearInterval(t);
    }, [ms]);
    return bars;
}

const HUD_VIEWS = [
    { id: "cc", label: "Command Center" },
    { id: "jarvis", label: "Jarvis" },
    { id: "globe", label: "Strategic Globe" },
    { id: "approvals", label: "Approvals" },
];

const WAKE_PHRASES = ["hey jarvis", "jarvis wake up", "wake up jarvis", "ok jarvis"];

const CHAT_HISTORY_STORAGE_KEY = "cc:chatHistory";
const CHAT_HISTORY_MAX = 120; // keep last N messages in localStorage

// Strip markdown formatting so TTS reads cleanly
function cleanForSpeech(text) {
    return text
        .replace(/```[\s\S]*?```/g, 'code block')  // fenced code blocks
        .replace(/`([^`]+)`/g, '$1')               // inline code
        .replace(/^#{1,6}\s+/gm, '')               // headers
        .replace(/\*{1,3}([^*\n]+)\*{1,3}/g, '$1') // bold / italic
        .replace(/^[\s]*[-*•]\s+/gm, ', ')         // bullet lists → natural pause
        .replace(/^\d+\.\s+/gm, '')               // numbered lists
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // [text](url) → text
        .replace(/[()"'\[\]{}\\|<>@#$%^&*+=]/g, ' ')
        .replace(/\s{2,}/g, ' ')
        .trim();
}

function useVoice() {
    const sessionStartTs = React.useRef(Date.now());
    const [state, setState] = React.useState("idle");
    const [micError, setMicError] = React.useState(null);
    const [wakeEnabled, setWakeEnabled] = React.useState(false);
    const [transcript, setTranscript] = React.useState("");
    const [reply, setReply] = React.useState("");
    const wakeDeadRef = React.useRef(false);
    const wakeRecogRef = React.useRef(null);
    const [history, setHistory] = React.useState(() => {
        // Restore previous session from localStorage on first render
        try {
            const raw = localStorage.getItem(CHAT_HISTORY_STORAGE_KEY);
            if (raw) return JSON.parse(raw);
        } catch (_) { }
        return [];
    });
    const [wakeActive, setWakeActive] = React.useState(false);
    const [voiceMuted, setVoiceMuted] = React.useState(false);
    const recogRef = React.useRef(null);
    const abortRef = React.useRef(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const supported = !!SpeechRecognition;
    const [micPermission, setMicPermission] = React.useState("unknown"); // unknown | granted | denied | prompt

    // Check mic permission state on mount and keep it updated
    React.useEffect(() => {
        if (!supported) { setMicPermission("unsupported"); return; }
        if (!navigator.permissions) return;
        navigator.permissions.query({ name: "microphone" }).then(status => {
            setMicPermission(status.state);
            status.onchange = () => setMicPermission(status.state);
        }).catch(() => { /* permissions API not available */ });
    }, [supported]);

    // Persist history to localStorage whenever it changes
    React.useEffect(() => {
        try {
            const trimmed = history.slice(-CHAT_HISTORY_MAX);
            localStorage.setItem(CHAT_HISTORY_STORAGE_KEY, JSON.stringify(trimmed));
        } catch (_) { }
    }, [history]);


    // Only keep the last N messages for model context
    const MODEL_CONTEXT_LIMIT = 16;
    const pushHistory = React.useCallback((role, text) => {
        setHistory(h => {
            const next = [...h, { role, text, ts: Date.now() }];
            // Save full history to localStorage, but only send last N to model
            try {
                localStorage.setItem(CHAT_HISTORY_STORAGE_KEY, JSON.stringify(next));
            } catch (_) { }
            return next;
        });
    }, []);

    const clearHistory = React.useCallback(() => {
        setHistory([]);
        try { localStorage.removeItem(CHAT_HISTORY_STORAGE_KEY); } catch (_) { }
    }, []);

    const speak = React.useCallback((text) => {
        const synth = window.speechSynthesis;
        if (!synth) { setState("idle"); return; }
        synth.cancel();
        const utt = new SpeechSynthesisUtterance(cleanForSpeech(text));
        // Lower pitch and rate for a deeper, grittier effect
        utt.rate = 0.92; // slower, more dramatic
        utt.pitch = 0.72; // deeper
        const voices = synth.getVoices();
        // Prefer a British English male voice (Ghost-like)
        const preferred = voices.find(v =>
            (v.lang === "en-GB" && v.name.toLowerCase().includes("daniel")) ||
            (v.lang === "en-GB" && v.name.toLowerCase().includes("oliver")) ||
            (v.lang === "en-GB" && v.gender === "male") ||
            (v.lang === "en-GB")
        ) || voices.find(v => v.lang.startsWith("en") && v.gender === "male") || voices[0];
        if (preferred) utt.voice = preferred;
        utt.onend = () => setState("idle");
        utt.onerror = () => setState("idle");
        synth.speak(utt);
        setState("speaking");
    }, []);

    const ask = React.useCallback(async (text) => {
        if (!text.trim()) return;
        // Interrupt any in-flight request or speech
        if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
        window.speechSynthesis?.cancel();
        if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } recogRef.current = null; }
        const ctrl = new AbortController();
        abortRef.current = ctrl;
        setState("thinking");
        setTranscript(text);
        setReply("");
        pushHistory("user", text);
        // Only send the last MODEL_CONTEXT_LIMIT messages to the model
        const contextHistory = history.slice(-MODEL_CONTEXT_LIMIT);
        try {
            const res = await fetch("/hud/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text,
                    context: {
                        view: "jarvis",
                        wake_enabled: wakeEnabled,
                        chat_history: contextHistory,
                    },
                }),
                signal: ctrl.signal,
            });
            const j = await res.json();
            abortRef.current = null;
            const r = j.reply || j.error || "No response";
            setReply(r);
            pushHistory("jarvis", r);
            if (!voiceMuted) speak(r); else setState("idle");
        } catch (err) {
            if (err.name === "AbortError") return; // superseded by newer message
            const msg = "Connection error — is the server running?";
            setReply(msg);
            pushHistory("jarvis", msg);
            setState("idle");
        }
    }, [speak, pushHistory, voiceMuted, wakeEnabled, history]);

    const startListening = React.useCallback(async () => {
        if (!supported) return;
        // Pause the wake listener so it doesn't conflict
        try { wakeRecogRef.current?.stop(); } catch (_) { }
        if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } }
        if (navigator.mediaDevices?.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                setMicPermission("granted");
                setWakeEnabled(true);
            } catch (_) {
                setMicPermission("denied");
                setMicError("Mic blocked — allow microphone in browser settings");
                setState("idle");
                return;
            }
        }
        const r = new SpeechRecognition();
        r.lang = "en-US"; r.interimResults = false; r.maxAlternatives = 1; r.continuous = false;
        recogRef.current = r;
        setState("active");
        setMicError(null);
        setTranscript(""); setReply("");
        r.onresult = e => { const t = e.results[0][0].transcript.trim(); if (t) ask(t); };
        r.onerror = (e) => {
            if (e.error === "not-allowed" || e.error === "service-not-allowed") {
                setMicPermission("denied");
                setMicError("Mic blocked — allow microphone in browser settings");
            } else if (e.error === "no-speech") {
                setMicError("No speech detected — try again");
            } else {
                setMicError(`Voice error: ${e.error}`);
            }
            setState("idle");
        };
        r.onend = () => { if (recogRef.current === r) { recogRef.current = null; } };
        try { r.start(); } catch (err) { setMicError("Could not start microphone"); setState("idle"); }
    }, [supported, ask]);

    // Continuous wake-word listener (does not run while main mic is active)
    React.useEffect(() => {
        if (!supported || !wakeEnabled) return;
        wakeDeadRef.current = false;
        const startWake = () => {
            if (wakeDeadRef.current) return;
            // Don't start wake listener if main mic is already active
            if (recogRef.current) { setTimeout(startWake, 800); return; }
            const r = new SpeechRecognition();
            r.lang = "en-US"; r.continuous = false; r.interimResults = false;
            wakeRecogRef.current = r;
            r.onresult = e => {
                const t = (e.results[0]?.[0]?.transcript ?? "").toLowerCase();
                if (WAKE_PHRASES.some(p => t.includes(p))) {
                    startListening();
                } else {
                    setTimeout(startWake, 300);
                }
            };
            r.onerror = () => { if (!wakeDeadRef.current) { setWakeActive(false); setTimeout(startWake, 2000); } };
            r.onend = () => { if (!wakeDeadRef.current) { setWakeActive(false); setTimeout(startWake, 400); } };
            try { r.start(); setWakeActive(true); } catch (_) { setWakeActive(false); setTimeout(startWake, 2000); }
        };
        const t = setTimeout(startWake, 2500);
        return () => {
            wakeDeadRef.current = true;
            setWakeActive(false);
            clearTimeout(t);
            try { wakeRecogRef.current?.stop(); } catch (_) { }
        };
    }, [supported, wakeEnabled]); // eslint-disable-line react-hooks/exhaustive-deps

    const stopListening = React.useCallback(() => {
        if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } recogRef.current = null; }
        window.speechSynthesis?.cancel();
        setState("idle");
    }, []);

    const toggleMute = React.useCallback(() => {
        setVoiceMuted(m => {
            if (!m) window.speechSynthesis?.cancel();
            return !m;
        });
    }, []);

    return { state, transcript, reply, history, clearHistory, sessionStartTs, micError, wakeActive, voiceMuted, micPermission, toggleMute, supported, startListening, stopListening, ask };
}

function JarvisEyeSVG({ state, clipSuffix = "" }) {
    // 16 rays at 22.5° intervals — longer and more aggressive
    const rays = Array.from({ length: 16 }, (_, i) => {
        const angle = (i * 22.5 * Math.PI) / 180;
        const inner = i % 2 === 0 ? 46 : 50;   // alternating long/short for spiky look
        const outer = i % 2 === 0 ? 62 : 57;
        const x1 = 50 + Math.cos(angle) * inner;
        const y1 = 50 + Math.sin(angle) * inner;
        const x2 = 50 + Math.cos(angle) * outer;
        const y2 = 50 + Math.sin(angle) * outer;
        return React.createElement("line", { key: i, className: "eye-ray", x1, y1, x2, y2 });
    });

    // Scarier eyelid shapes — aggressive downward inner corner, sharpened
    // Upper lid: asymmetric cubic — inner corner drops down (threatening squint)
    const upperLid = "M 30,49 C 38,30 58,34 70,49";
    // Lower lid: flatter, tighter
    const lowerLid = "M 30,49 C 40,62 60,60 70,49";
    // Eye white shape (matches lid curves)
    const eyeWhite = `${upperLid} ${lowerLid.replace("M 30,49", "L")} Z`;
    const clipId = `eye-clip${clipSuffix}`;

    // Vein lines inside eye white radiating from iris edge
    const veins = [
        "M 42,48 L 33,44", "M 44,51 L 36,56", "M 56,48 L 65,44", "M 57,51 L 64,56",
        "M 50,41 L 50,34", "M 50,53 L 50,60",
    ];

    return React.createElement(
        "svg", { viewBox: "0 0 100 100", xmlns: "http://www.w3.org/2000/svg", width: "100%", height: "100%" },
        React.createElement("defs", null,
            React.createElement("clipPath", { id: clipId },
                React.createElement("path", { d: `${upperLid} ${lowerLid.replace("M 30,49", "L")} Z` })
            ),
            React.createElement("radialGradient", { id: `iris-grad${clipSuffix}`, cx: "50%", cy: "40%", r: "60%" },
                React.createElement("stop", { offset: "0%", stopColor: "#ff6b1a", stopOpacity: 0.9 }),
                React.createElement("stop", { offset: "55%", stopColor: "#b8460a", stopOpacity: 1 }),
                React.createElement("stop", { offset: "100%", stopColor: "#5a1a00", stopOpacity: 1 }),
            )
        ),

        // Outer ominous glow halo
        React.createElement("circle", { className: "eye-halo", cx: 50, cy: 50, r: 52 }),
        React.createElement("circle", { className: "eye-ping", cx: 50, cy: 50, r: 50 }),

        // Rays
        React.createElement("g", { className: "eye-rays" }, ...rays),

        // Triangle — sharper, taller
        React.createElement("polygon", { className: "eye-triangle", points: "50,4 2,96 98,96" }),

        // Eye white — slightly yellowed/bloodshot
        React.createElement("path", { className: "eye-white", d: `${upperLid} ${lowerLid.replace("M 30,49", "L")} Z` }),

        // Blood veins
        ...veins.map((d, i) => React.createElement("path", {
            key: `v${i}`, d,
            stroke: "rgba(180,30,10,0.35)", strokeWidth: 0.6, fill: "none",
            clipPath: `url(#${clipId})`,
            className: "eye-vein",
        })),

        // Iris + effects (clipped)
        React.createElement("g", { clipPath: `url(#${clipId})` },
            React.createElement("circle", {
                className: "eye-iris", cx: 50, cy: 47, r: 10,
                fill: `url(#iris-grad${clipSuffix})`
            }),
            // Dark limbal ring
            React.createElement("circle", {
                cx: 50, cy: 47, r: 10,
                fill: "none", stroke: "rgba(0,0,0,0.55)", strokeWidth: 1.8, clipPath: `url(#${clipId})`
            }),
            // Ripple rings for speaking
            React.createElement("circle", { className: "eye-ripple eye-ripple-1", cx: 50, cy: 47, r: 10 }),
            React.createElement("circle", { className: "eye-ripple eye-ripple-2", cx: 50, cy: 47, r: 10 }),
            React.createElement("circle", { className: "eye-ripple eye-ripple-3", cx: 50, cy: 47, r: 10 }),
            // Vertical slit pupil
            React.createElement("ellipse", { className: "eye-pupil", cx: 50, cy: 47, rx: 2.2, ry: 7 }),
        ),

        // Eyelid group (blink)
        React.createElement("g", { className: "eye-lid-group" },
            // Upper lid fill mask
            React.createElement("path", { fill: "#07080e", d: "M 30,49 C 38,30 58,34 70,49 L 70,36 C 58,20 38,16 30,36 Z" }),
            React.createElement("path", { className: "eye-lid-upper", d: upperLid }),
            React.createElement("path", { className: "eye-lid-lower", d: lowerLid }),
        ),
    );
}

function JarvisTab({ voice }) {
    const { state, history, clearHistory, sessionStartTs, micError, wakeActive, voiceMuted, micPermission, toggleMute, supported, startListening, stopListening, ask } = voice;
    const [input, setInput] = React.useState("");
    const [showPast, setShowPast] = React.useState(false);
    const logRef = React.useRef(null);
    const inputRef = React.useRef(null);

    // Split: messages from before this page load vs. this session
    const pastMsgs = history.filter(m => m.ts < sessionStartTs.current);
    const currentMsgs = history.filter(m => m.ts >= sessionStartTs.current);

    // Auto-scroll to bottom only for new current-session messages
    React.useEffect(() => {
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    }, [currentMsgs.length, state]);

    const handleSend = () => {
        const t = input.trim();
        if (!t) return;
        setInput("");
        ask(t);
        // Return focus to the input box after sending
        requestAnimationFrame(() => inputRef.current?.focus());
    };

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const stateLabel = { idle: "Standby", active: "Listening…", thinking: "Thinking…", speaking: "Speaking…" }[state] ?? "Standby";

    return React.createElement(
        "div", { className: "jarvis-tab" },

        // Background eye — large, state-driven opacity/glow behind everything
        React.createElement(
            "div", { className: `jarvis-eye-bg jarvis-eye ${state}`, "aria-hidden": "true" },
            React.createElement(JarvisEyeSVG, { state, clipSuffix: "bg" })
        ),

        // Compact status strip
        React.createElement(
            "div", { className: "jarvis-tab-header" },
            React.createElement("span", { className: "jarvis-state-label" }, stateLabel),
            React.createElement(
                "div", { className: "jarvis-tab-wake" },
                React.createElement("span", { className: `jarvis-wake-dot${wakeActive ? " on" : ""}` }),
                React.createElement("span", { className: "jarvis-wake-label" },
                    supported
                        ? wakeActive ? `Listening for "Hey Jarvis"` : (micPermission === "granted" ? "Wake listening armed" : "Click mic once to enable voice")
                        : "Speech not supported"
                )
            ),
        ),

        // Conversation log
        React.createElement(
            "div", { className: "jarvis-log", ref: logRef },

            // Past session history (collapsed by default)
            pastMsgs.length > 0 && React.createElement(
                "div", { className: "jarvis-history-divider", onClick: () => setShowPast(v => !v) },
                React.createElement("span", { className: "jarvis-history-toggle" },
                    showPast ? "▲" : "▼"
                ),
                React.createElement("span", null, `${pastMsgs.length} previous message${pastMsgs.length === 1 ? "" : "s"}`),
                !showPast && React.createElement("span", { className: "jarvis-history-hint" }, "tap to expand")
            ),
            showPast && pastMsgs.map((entry, i) =>
                React.createElement(
                    "div", { key: `past-${i}`, className: `jarvis-msg jarvis-msg-${entry.role} jarvis-msg-past` },
                    React.createElement("span", { className: "jarvis-msg-role" }, entry.role === "user" ? "You" : "Jarvis"),
                    React.createElement("span", { className: "jarvis-msg-text" }, entry.text),
                    React.createElement("span", { className: "jarvis-msg-ts" },
                        new Date(entry.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                    )
                )
            ),

            // Current session messages
            currentMsgs.length === 0 && pastMsgs.length === 0 && React.createElement(
                "div", { className: "jarvis-log-empty" },
                "No conversation yet. Say \"Hey Jarvis\" or type below."
            ),
            currentMsgs.map((entry, i) =>
                React.createElement(
                    "div", { key: `cur-${i}`, className: `jarvis-msg jarvis-msg-${entry.role}` },
                    React.createElement("span", { className: "jarvis-msg-role" }, entry.role === "user" ? "You" : "Jarvis"),
                    React.createElement("span", { className: "jarvis-msg-text" }, entry.text),
                    React.createElement("span", { className: "jarvis-msg-ts" },
                        new Date(entry.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                    )
                )
            ),
            state === "thinking" && React.createElement(
                "div", { className: "jarvis-msg jarvis-msg-jarvis jarvis-msg-thinking" },
                React.createElement("span", { className: "jarvis-msg-role" }, "Jarvis"),
                React.createElement("span", { className: "jarvis-thinking-dots" },
                    React.createElement("span"), React.createElement("span"), React.createElement("span")
                )
            )
        ),

        // Mic error banner
        micError && React.createElement(
            "div", { className: "jarvis-mic-banner jarvis-mic-denied" }, micError
        ),
        micPermission === "prompt" && React.createElement(
            "div", { className: "jarvis-mic-banner jarvis-mic-prompt" },
            React.createElement("button", {
                className: "jarvis-mic-grant-btn",
                onClick: startListening,
            }, "Grant microphone access"),
            React.createElement("span", null, " — required for voice commands")
        ),

        // Input bar
        React.createElement(
            "div", { className: "jarvis-input-bar" },
            supported && (state === "active" || state === "speaking"
                ? React.createElement("button", {
                    className: "jarvis-mic-btn jarvis-stop-btn",
                    onClick: stopListening,
                    title: "Stop",
                }, "■")
                : React.createElement("button", {
                    className: "jarvis-mic-btn",
                    onClick: startListening,
                    disabled: state === "thinking",
                    title: "Click to speak",
                }, "🎙")
            ),
            React.createElement("textarea", {
                className: "jarvis-input",
                ref: inputRef,
                value: input,
                onChange: e => setInput(e.target.value),
                onKeyDown: handleKey,
                placeholder: "Ask Jarvis anything…",
                rows: 1,
                disabled: state === "thinking",
            }),
            React.createElement(
                "button", {
                className: "jarvis-send-btn",
                onClick: handleSend,
                disabled: !input.trim() || state === "thinking",
            }, "Send"
            ),
            React.createElement(
                "button", {
                className: `jarvis-mute-btn${voiceMuted ? " muted" : ""}`,
                onClick: toggleMute,
                title: voiceMuted ? "Voice off — click to unmute" : "Voice on — click to mute",
            }, voiceMuted ? "🔇" : "🔊"
            )
        )
    );
}

function EyeOfJarvis({ voice }) {
    const { state, transcript, reply, supported, startListening, stopListening } = voice;
    const showOverlay = transcript || reply || state === "thinking";
    const isActive = state !== "idle";

    // Escape key stops mic from anywhere in the app
    React.useEffect(() => {
        const onKey = (e) => { if (e.key === "Escape" && isActive) stopListening(); };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [isActive, stopListening]);

    const handleClick = supported
        ? (isActive ? stopListening : startListening)
        : undefined;

    return React.createElement(
        React.Fragment, null,
        React.createElement(
            "button", {
            className: `jarvis-eye ${state}`,
            onClick: handleClick,
            title: isActive ? "Stop (or press Esc)" : supported ? "Click or say \"Hey Jarvis\"" : "Speech not supported",
            "aria-label": isActive ? "Stop Jarvis" : "Activate Jarvis",
        },
            React.createElement(JarvisEyeSVG, { state, clipSuffix: "sm" })
        ),
        showOverlay && React.createElement(
            "div", { className: "cc-voice-overlay" },
            transcript && React.createElement("div", { className: "cc-voice-transcript" }, `"${transcript}"`),
            state === "thinking" && React.createElement("div", { className: "cc-voice-thinking" }, "Thinking…"),
            reply && state !== "thinking" && React.createElement("div", { className: "cc-voice-reply" }, reply),
        )
    );
}

const NAV_ICONS = {
    cc: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("rect", { x: 2, y: 2, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 11, y: 2, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 2, y: 11, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 11, y: 11, width: 7, height: 7, rx: 1 })),
    jarvis: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.4 }, React.createElement("polygon", { points: "10,2 1,18 19,18" }), React.createElement("ellipse", { cx: 10, cy: 11, rx: 4, ry: 2.5 }), React.createElement("circle", { cx: 10, cy: 11, r: 1.4, fill: "currentColor" })),
    globe: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("circle", { cx: 10, cy: 10, r: 8 }), React.createElement("ellipse", { cx: 10, cy: 10, rx: 4, ry: 8 }), React.createElement("line", { x1: 2, y1: 10, x2: 18, y2: 10 })),
    approvals: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("rect", { x: 3, y: 3, width: 14, height: 14, rx: 2 }), React.createElement("polyline", { points: "6,10 9,13 14,7" })),
};

// ── components ────────────────────────────────────────────────────────────────
function Sidebar({ view, onView, voice, collapsed }) {
    return React.createElement(
        "nav", { className: `cc-sidebar${collapsed ? " collapsed" : ""}` },
        React.createElement("div", { className: "cc-sidebar-logo" }, "JARVIS"),
        React.createElement("div", { className: "cc-sidebar-eye-wrap" },
            React.createElement(EyeOfJarvis, { voice })
        ),
        React.createElement(
            "ul", { className: "cc-sidebar-nav" },
            ...HUD_VIEWS.map((v, i) =>
                React.createElement(
                    "li", { key: v.id, style: { "--i": i } },
                    React.createElement(
                        "button", {
                        className: `cc-sidebar-item${view === v.id ? " active" : ""}`,
                        onClick: () => onView(v.id),
                    },
                        React.createElement("span", { className: "cc-sidebar-icon" }, NAV_ICONS[v.id]),
                        React.createElement("span", { className: "cc-sidebar-label" }, v.label)
                    )
                )
            )
        )
    );
}

function TopBar({ now, health, healthState, pending, pendingState, brainStream, onOpenPayment }) {
    const status = health?.status ?? "unknown";
    const monitors = health?.monitors?.configured ?? 0;
    const staleData = Boolean(healthState?.stale || pendingState?.stale);
    const streamAgeSec = brainStream?.lastEventAt ? Math.max(0, Math.round((Date.now() - brainStream.lastEventAt) / 1000)) : null;
    const streamLabel = brainStream?.status === "live"
        ? (streamAgeSec !== null && streamAgeSec > 9 ? `Stream stale ${streamAgeSec}s` : "Stream live")
        : brainStream?.status === "reconnecting"
            ? `Stream retry ${Math.round((brainStream?.retryMs || 0) / 1000)}s`
            : "Stream connecting";
    return React.createElement(
        "header", { className: "cc-menubar" },
        React.createElement("span", { className: "cc-menubar-item" }, `${monitors} monitors`),
        pending !== null && React.createElement("span", { className: "cc-menubar-item" },
            pending > 0 ? `${pending} pending` : "queue clear"
        ),
        React.createElement(
            "span", { className: `cc-status-pill ${status}` },
            React.createElement("span", { className: `cc-status-dot ${status}` }),
            status === "ok" ? "Online" : status === "degraded" ? "Degraded" : "Unknown"
        ),
        React.createElement(
            "span", { className: `cc-stream-pill ${brainStream?.status || "connecting"}` },
            React.createElement("span", { className: `cc-stream-dot ${brainStream?.status || "connecting"}` }),
            streamLabel
        ),
        staleData && React.createElement("span", { className: "cc-stale-pill" }, "stale data"),
        React.createElement("span", { className: "cc-menubar-clock" }, `${fmtTime(now)} ${localTZName()}`),
        React.createElement("button", { type: "button", className: "cc-menubar-action", onClick: onOpenPayment }, "Payment"),
    );
}

function PaymentRequestModal({ open, onClose, onQueued }) {
    const [amount, setAmount] = React.useState("");
    const [currency, setCurrency] = React.useState("USD");
    const [recipient, setRecipient] = React.useState("");
    const [merchant, setMerchant] = React.useState("");
    const [reason, setReason] = React.useState("");
    const [cardholder, setCardholder] = React.useState("");
    const [cardNumber, setCardNumber] = React.useState("");
    const [expMonth, setExpMonth] = React.useState("");
    const [expYear, setExpYear] = React.useState("");
    const [billingZip, setBillingZip] = React.useState("");
    const [temporaryCard, setTemporaryCard] = React.useState(false);
    const [cvv, setCvv] = React.useState("");
    const [busy, setBusy] = React.useState(false);
    const [statusText, setStatusText] = React.useState("");

    React.useEffect(() => {
        if (!open) {
            setBusy(false);
            setStatusText("");
        }
    }, [open]);

    React.useEffect(() => {
        if (!open) return;
        const onKey = (event) => {
            if (event.key === "Escape") onClose();
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [open, onClose]);

    const resetForm = () => {
        setAmount("");
        setCurrency("USD");
        setRecipient("");
        setMerchant("");
        setReason("");
        setCardholder("");
        setCardNumber("");
        setExpMonth("");
        setExpYear("");
        setBillingZip("");
        setTemporaryCard(false);
        setCvv("");
        setStatusText("");
    };

    const closeModal = () => {
        resetForm();
        onClose();
    };

    const submit = async () => {
        if (busy) return;
        const amountNum = Number(amount);
        const currencyNorm = String(currency || "").trim().toUpperCase();
        const recipientNorm = String(recipient || "").trim();
        const merchantNorm = String(merchant || "").trim();
        const cardholderNorm = String(cardholder || "").trim();
        const cardDigits = String(cardNumber || "").replace(/\D/g, "");
        const expMonthNum = Number(expMonth);
        const expYearNum = Number(expYear);
        const billingZipNorm = String(billingZip || "").trim();
        const cvvDigits = String(cvv || "").replace(/\D/g, "");

        if (!Number.isFinite(amountNum) || amountNum <= 0) {
            setStatusText("Amount must be a positive number.");
            return;
        }
        if (currencyNorm.length !== 3) {
            setStatusText("Currency must be a 3-letter code.");
            return;
        }
        if (!recipientNorm) {
            setStatusText("Recipient is required.");
            return;
        }
        if (!merchantNorm) {
            setStatusText("Merchant is required.");
            return;
        }
        if (!cardholderNorm) {
            setStatusText("Cardholder name is required.");
            return;
        }
        if (cardDigits.length < 12 || cardDigits.length > 19) {
            setStatusText("Card number must be between 12 and 19 digits.");
            return;
        }
        if (!Number.isInteger(expMonthNum) || expMonthNum < 1 || expMonthNum > 12) {
            setStatusText("Expiration month must be 1-12.");
            return;
        }
        if (!Number.isInteger(expYearNum) || expYearNum < 2024 || expYearNum > 2099) {
            setStatusText("Expiration year is invalid.");
            return;
        }
        if (!billingZipNorm) {
            setStatusText("Billing ZIP is required.");
            return;
        }
        if (!temporaryCard && !cvvDigits) {
            setStatusText("CVV is required unless Temporary card is enabled.");
            return;
        }
        if (cvvDigits && !/^\d{3,4}$/.test(cvvDigits)) {
            setStatusText("CVV must be 3 or 4 digits when provided.");
            return;
        }

        setBusy(true);
        setStatusText("Queueing payment approval...");

        const payload = {
            kind: "payments",
            action: "execute_payment",
            reason: reason || "payment request from command center",
            budget_impact: amountNum,
            risk_tier: amountNum > 100 ? "high" : amountNum > 10 ? "medium" : "low",
            payload: {
                amount: amountNum,
                currency: currencyNorm,
                recipient: recipientNorm,
                merchant: merchantNorm,
                reason,
                payment_method: {
                    type: "card",
                    cardholder_name: cardholderNorm,
                    card_last4: cardDigits.slice(-4),
                    card_network: detectCardNetwork(cardDigits),
                    exp_month: expMonthNum,
                    exp_year: expYearNum,
                    billing_zip: billingZipNorm,
                    temporary_card: temporaryCard,
                    cvv_provided: !!cvvDigits,
                },
            },
        };

        const { data, error } = await fetchJsonResult("/approvals/request", {
            method: "POST",
            timeoutMs: 5000,
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify(payload),
        });

        if (error) {
            setBusy(false);
            if (error.type === FETCH_ERROR_TYPES.HTTP) {
                setStatusText(`Request failed (HTTP ${error.status ?? "?"}).`);
            } else if (error.type === FETCH_ERROR_TYPES.TIMEOUT) {
                setStatusText("Request timed out. Try again.");
            } else {
                setStatusText("Request failed. Check connection.");
            }
            return;
        }

        const approvalId = data?.approval?.id || "unknown";
        setStatusText(`Queued approval ${approvalId} for ${merchantNorm}.`);
        setBusy(false);
        if (typeof onQueued === "function") onQueued();
        setTimeout(() => closeModal(), 650);
    };

    if (!open) return null;

    return React.createElement(
        "div",
        {
            className: "cc-modal-backdrop",
            onMouseDown: (event) => {
                if (event.target === event.currentTarget) closeModal();
            },
        },
        React.createElement(
            "div",
            { className: "cc-modal cc-payment-modal" },
            React.createElement(
                "div",
                { className: "cc-modal-header" },
                React.createElement("div", { className: "cc-section-title" }, "Payment Request"),
                React.createElement(
                    "button",
                    { type: "button", className: "cc-modal-close", onClick: closeModal, title: "Close" },
                    "x"
                )
            ),
            React.createElement(
                "div",
                { className: "cc-payment-grid" },
                React.createElement("label", { className: "cc-pay-label" }, "Amount"),
                React.createElement("input", { className: "cc-pay-input", type: "number", min: "0.01", step: "0.01", value: amount, onChange: e => setAmount(e.target.value), placeholder: "40.00" }),
                React.createElement("label", { className: "cc-pay-label" }, "Currency"),
                React.createElement("input", { className: "cc-pay-input", value: currency, maxLength: 3, onChange: e => setCurrency(e.target.value), placeholder: "USD" }),

                React.createElement("label", { className: "cc-pay-label" }, "Recipient"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide", value: recipient, onChange: e => setRecipient(e.target.value), placeholder: "merchant@example.com" }),

                React.createElement("label", { className: "cc-pay-label" }, "Merchant"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide", value: merchant, onChange: e => setMerchant(e.target.value), placeholder: "Lupa" }),

                React.createElement("label", { className: "cc-pay-label" }, "Reason"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide", value: reason, onChange: e => setReason(e.target.value), placeholder: "Reservation deposit" }),

                React.createElement("label", { className: "cc-pay-label" }, "Cardholder Name"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide", value: cardholder, onChange: e => setCardholder(e.target.value), placeholder: "Nickos" }),

                React.createElement("label", { className: "cc-pay-label" }, "Card Number"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide", value: cardNumber, onChange: e => setCardNumber(e.target.value), placeholder: "4242 4242 4242 4242", inputMode: "numeric", autoComplete: "cc-number" }),

                React.createElement("label", { className: "cc-pay-label" }, "Exp Month"),
                React.createElement("input", { className: "cc-pay-input", value: expMonth, onChange: e => setExpMonth(e.target.value), placeholder: "12", inputMode: "numeric" }),
                React.createElement("label", { className: "cc-pay-label" }, "Exp Year"),
                React.createElement("input", { className: "cc-pay-input", value: expYear, onChange: e => setExpYear(e.target.value), placeholder: "2028", inputMode: "numeric" }),

                React.createElement("label", { className: "cc-pay-label" }, "Billing ZIP"),
                React.createElement("input", { className: "cc-pay-input", value: billingZip, onChange: e => setBillingZip(e.target.value), placeholder: "10001" }),

                React.createElement("label", { className: "cc-pay-label" }, "Temporary Card"),
                React.createElement(
                    "label",
                    { className: "cc-pay-checkbox" },
                    React.createElement("input", { type: "checkbox", checked: temporaryCard, onChange: e => setTemporaryCard(e.target.checked) }),
                    React.createElement("span", null, temporaryCard ? "Yes" : "No")
                ),

                React.createElement("label", { className: "cc-pay-label" }, temporaryCard ? "CVV (optional)" : "CVV (required)"),
                React.createElement("input", { className: "cc-pay-input", value: cvv, onChange: e => setCvv(e.target.value), placeholder: "123", inputMode: "numeric", autoComplete: "cc-csc" })
            ),

            statusText && React.createElement("div", { className: "cc-pay-status" }, statusText),

            React.createElement(
                "div",
                { className: "cc-payment-actions" },
                React.createElement(
                    "button",
                    { type: "button", className: "cc-runtime-btn", onClick: closeModal, disabled: busy },
                    "Cancel"
                ),
                React.createElement(
                    "button",
                    { type: "button", className: "cc-runtime-btn start", onClick: submit, disabled: busy },
                    busy ? "Queueing..." : "Queue Approval"
                )
            )
        )
    );
}

const MARKET_STRIP = [
    { id: "nyse", label: "NYSE" },
    { id: "lse", label: "LSE" },
    { id: "tse", label: "TSE" },
    { id: "hkex", label: "HK" },
    { id: "asx", label: "ASX" },
];

function MarketHoursStrip({ now }) {
    return React.createElement(
        "div", { style: { display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 } },
        ...MARKET_STRIP.map(ms => {
            const m = MARKETS.find(x => x.id === ms.id);
            const { open } = m ? marketStatus(m, now) : { open: false };
            return React.createElement(
                "div", {
                key: ms.id,
                style: {
                    display: "flex", alignItems: "center", gap: 4,
                    fontFamily: "var(--mono)", fontSize: 9,
                    color: open ? "var(--green)" : "var(--text3)",
                    letterSpacing: "0.06em",
                }
            },
                React.createElement("span", {
                    style: {
                        width: 5, height: 5, borderRadius: "50%", flexShrink: 0,
                        background: open ? "var(--green)" : "rgba(255,255,255,0.15)",
                        boxShadow: open ? "0 0 5px var(--green)" : "none",
                    }
                }),
                ms.label
            );
        })
    );
}

function ClockCard({ now }) {
    const tz = localTZName();
    return React.createElement(
        "div", { className: "cc-card cc-card-clock", "data-accent": "cyan" },
        React.createElement("div", { className: "cc-label" }, tz || "Local Time"),
        React.createElement("div", { className: "cc-clock-time" }, fmtTime(now)),
        React.createElement("div", { className: "cc-clock-date" }, fmtDate(now)),
        React.createElement("div", { className: "cc-clock-local" }, `UTC ${fmtUTC(now)}`),
        React.createElement(MarketHoursStrip, { now })
    );
}

function AssetStatCard({ asset, loading, flash }) {
    const price = asset?.price ?? 0;
    const delta = asset?.delta ?? 0;
    const up = delta >= 0;
    return React.createElement(
        "div", { className: "cc-card cc-card-btc-stat", "data-accent": "orange" },
        React.createElement("div", { className: "cc-label" }, asset ? `${asset.symbol.toUpperCase()} / USD` : "Asset"),
        loading
            ? React.createElement("div", { className: "cc-loading-wrap", style: { flex: 1 } }, React.createElement("div", { className: "cc-spinner" }))
            : React.createElement(
                React.Fragment, null,
                React.createElement("div", {
                    className: `cc-stat-value${flash ? ` cc-price-flash-${flash}` : ""}`,
                    style: { transition: "color 0.3s" }
                }, fmtPrice(price)),
                React.createElement(
                    "div", { className: `cc-delta ${up ? "up" : "down"}` },
                    up ? "▲" : "▼", ` ${Math.abs(delta).toFixed(2)}%`
                )
            )
    );
}

function MarketsStatCard({ openMarkets }) {
    const open = openMarkets ?? 0;
    return React.createElement(
        "div", { className: "cc-card cc-card-markets", "data-accent": "green" },
        React.createElement("div", { className: "cc-label" }, "Markets Open"),
        React.createElement("div", { className: "cc-open-count" }, `${open} / ${MARKETS.length}`),
        React.createElement("div", { className: "cc-stat-sub" }, "exchanges active")
    );
}

function PendingCard({ pending }) {
    const n = pending ?? 0;
    return React.createElement(
        "div", { className: "cc-card cc-card-pending", "data-accent": n > 0 ? "red" : "green" },
        React.createElement("div", { className: "cc-label" }, "Approvals"),
        React.createElement("div", { className: "cc-stat-value" }, String(n).padStart(2, "0")),
        React.createElement("div", { className: "cc-stat-sub" }, n > 0 ? "awaiting action" : "queue clear")
    );
}

function RuntimeControlCard({ health }) {
    const serverStopped = health?.monitors?.stopped;
    const [localStopped, setLocalStopped] = React.useState(null);
    const [busy, setBusy] = React.useState("");
    const [statusText, setStatusText] = React.useState("");
    const [lastActionText, setLastActionText] = React.useState("");

    React.useEffect(() => {
        if (typeof serverStopped === "boolean") {
            setLocalStopped(serverStopped);
        }
    }, [serverStopped]);

    const resolvedStopped = localStopped !== null
        ? localStopped
        : (typeof serverStopped === "boolean" ? serverStopped : null);
    const runtimeKnown = resolvedStopped !== null;
    const isStopped = resolvedStopped === true;

    const callRuntimeAction = async (action) => {
        if (busy) return;
        setBusy(action);
        setStatusText(action === "stop" ? "Stopping Jarvis..." : "Starting Jarvis...");
        try {
            const { data, error } = await fetchJsonResult(`/runtime/${action}`, {
                method: "POST",
                timeoutMs: 4000,
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: "{}",
            });
            if (error) throw error;
            const payload = data ?? {};
            const stoppedNow = payload?.status === "stopped";
            setLocalStopped(stoppedNow);
            const noChange = action === "stop"
                ? payload?.already_stopped === true
                : payload?.was_stopped === false;
            if (noChange) {
                setStatusText(stoppedNow ? "Jarvis was already stopped." : "Jarvis was already running.");
            } else {
                setStatusText(stoppedNow ? "Jarvis stopped successfully." : "Jarvis started successfully.");
            }
            setLastActionText(
                `${action.toUpperCase()} @ ${fmtTime(new Date())}${payload?.sentinel ? ` • ${payload.sentinel}` : ""}`
            );
        } catch (err) {
            const normalized = normalizeFetchError(err, `/runtime/${action}`);
            if (normalized.type === FETCH_ERROR_TYPES.TIMEOUT) {
                setStatusText("Action timed out. Try again.");
            } else if (normalized.type === FETCH_ERROR_TYPES.HTTP) {
                setStatusText(`Action failed (HTTP ${normalized.status ?? "?"}).`);
            } else {
                setStatusText("Action failed. Check server connection.");
            }
            setLastActionText(`LAST ERROR: ${normalized.type.toUpperCase()} @ ${fmtTime(new Date())}`);
        } finally {
            setBusy("");
        }
    };

    return React.createElement(
        "div", { className: "cc-card cc-card-runtime", "data-accent": isStopped ? "red" : "green" },
        React.createElement("div", { className: "cc-label" }, "Runtime Control"),
        React.createElement(
            "div", { className: "cc-runtime-state" },
            React.createElement("span", { className: `cc-runtime-dot ${isStopped ? "stopped" : "running"}` }),
            React.createElement(
                "span",
                { className: "cc-runtime-text" },
                runtimeKnown ? (isStopped ? "Stopped" : "Running") : "Syncing..."
            )
        ),
        React.createElement(
            "div", { className: "cc-runtime-actions" },
            React.createElement(
                "button",
                {
                    type: "button",
                    className: "cc-runtime-btn start",
                    onClick: () => callRuntimeAction("resume"),
                    disabled: busy.length > 0 || !runtimeKnown || !isStopped,
                },
                busy === "resume" ? "Starting..." : "Start"
            ),
            React.createElement(
                "button",
                {
                    type: "button",
                    className: "cc-runtime-btn stop",
                    onClick: () => callRuntimeAction("stop"),
                    disabled: busy.length > 0 || !runtimeKnown || isStopped,
                },
                busy === "stop" ? "Stopping..." : "Stop"
            )
        ),
        React.createElement(
            "div",
            { className: "cc-runtime-hint" },
            statusText || "Use Start/Stop to control monitor execution."
        ),
        lastActionText && React.createElement(
            "div",
            { className: "cc-runtime-hint", style: { marginTop: 6, color: "var(--text3)", fontSize: 10 } },
            lastActionText
        )
    );
}

function MarketListCard({ now }) {
    return React.createElement(
        "div", { className: "cc-card cc-card-mktlist", "data-accent": "purple" },
        React.createElement("div", { className: "cc-section-title" }, "Exchange Status"),
        React.createElement(
            "div", { className: "cc-mkt-scroll" },
            ...MARKETS.map(m => {
                const st = marketStatus(m, now);
                return React.createElement(
                    "div", { key: m.id, className: "cc-mkt-row" },
                    React.createElement(
                        "div", { className: "cc-mkt-left" },
                        React.createElement("span", { className: "cc-mkt-name" }, m.name),
                        React.createElement("span", { className: "cc-mkt-city" }, m.city)
                    ),
                    React.createElement(
                        "div", { className: "cc-mkt-right" },
                        React.createElement("span", { className: st.open ? "cc-mkt-status-open" : "cc-mkt-status-closed" },
                            st.open ? "Open" : "Closed"
                        ),
                        st.deltaMs > 0 && React.createElement("span", { className: "cc-mkt-countdown" },
                            st.open ? `closes ${fmtCountdown(st.deltaMs)}` : `opens ${fmtCountdown(st.deltaMs)}`
                        )
                    )
                );
            })
        )
    );
}

function AssetChartCard({ coinMeta, onSelect, price, delta, loading }) {
    const isCommodity = COMMODITY_IDS.has(coinMeta.id);
    const [winIdx, setWinIdx] = React.useState(0);
    // commodities have no Binance klines — force LIVE window
    const effectiveWinIdx = isCommodity ? 0 : winIdx;
    const sparkline = useAssetChart(coinMeta.id, coinMeta.symbol, WINDOWS[effectiveWinIdx]);

    const [query, setQuery] = React.useState("");
    const [focused, setFocused] = React.useState(false);
    const blurTimer = React.useRef(null);
    const { results, searching } = useAssetSearch(query);
    const open = focused && query.trim().length >= 2;

    const up = (delta ?? 0) >= 0;
    const lineColor = up ? "#30d158" : "#ff453a";
    const W = 200, H = 72;
    const { line: linePath, fill: fillPath } = smoothPath(sparkline, W, H);

    const pickResult = (coin) => {
        onSelect({ id: coin.id, name: coin.name, symbol: coin.symbol });
        setQuery("");
        setFocused(false);
    };

    return React.createElement(
        "div", { className: "cc-card cc-card-chart", "data-accent": "orange" },

        // search bar
        React.createElement(
            "div", { className: "cc-search-wrap" },
            React.createElement("input", {
                className: "cc-search-input",
                placeholder: "BTC, ETH, gold, SOL…",
                value: query,
                onChange: e => { setQuery(e.target.value); clearTimeout(blurTimer.current); },
                onFocus: () => { setFocused(true); clearTimeout(blurTimer.current); },
                onBlur: () => { blurTimer.current = setTimeout(() => setFocused(false), 300); },
                onKeyDown: e => { if (e.key === "Enter" && results.length > 0) { e.preventDefault(); pickResult(results[0]); } },
            }),
            searching
                ? React.createElement("span", { className: "cc-search-icon loading" },
                    React.createElement("div", { className: "cc-spinner", style: { width: 12, height: 12 } }))
                : React.createElement("span", { className: "cc-search-icon" }, "⌕")
        ),

        // dropdown
        open && React.createElement(
            "div", { className: "cc-search-dropdown" },
            searching
                ? React.createElement("div", { className: "cc-loading-wrap", style: { padding: "14px 0" } }, React.createElement("div", { className: "cc-spinner" }))
                : results.length === 0
                    ? React.createElement("div", { style: { padding: "10px 12px", fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" } }, "No results")
                    : results.map(coin =>
                        React.createElement(
                            "div", {
                            key: coin.id, className: "cc-search-item",
                            onMouseDown: e => { e.preventDefault(); pickResult(coin); }
                        },
                            React.createElement(
                                "div", { className: "cc-search-item-left" },
                                React.createElement("span", { className: "cc-search-item-name" }, coin.name),
                                React.createElement("span", { className: "cc-search-item-sym" }, coin.symbol)
                            ),
                            coin.market_cap_rank
                                ? React.createElement("span", { className: "cc-search-item-rank" }, `#${coin.market_cap_rank}`)
                                : null
                        )
                    )
        ),

        // window selector (hidden for commodities — live only)
        !isCommodity && React.createElement(
            "div", { className: "cc-chart-windows" },
            ...WINDOWS.map((w, i) =>
                React.createElement("button", {
                    key: w.label,
                    className: `cc-chart-win${winIdx === i ? " active" : ""}`,
                    onClick: () => setWinIdx(i),
                }, w.label)
            )
        ),

        // asset info + chart
        loading
            ? React.createElement("div", { className: "cc-loading-wrap" }, React.createElement("div", { className: "cc-spinner" }))
            : React.createElement(
                React.Fragment, null,
                React.createElement(
                    "div", { className: "cc-asset-header" },
                    React.createElement("span", { className: "cc-asset-name" }, coinMeta.name),
                    React.createElement("span", { className: "cc-asset-symbol" }, coinMeta.symbol.toUpperCase())
                ),
                React.createElement("div", { className: "cc-asset-price" }, fmtPrice(price ?? 0)),
                React.createElement(
                    "div", { className: `cc-delta ${up ? "up" : "down"}`, style: { marginBottom: 4 } },
                    up ? "▲" : "▼", ` ${Math.abs(delta).toFixed(2)}%  ${WINDOWS[winIdx].label}`

                ),
                sparkline.length > 1
                    ? React.createElement(
                        "div", { className: "cc-sparkline" },
                        React.createElement(
                            "svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" },
                            React.createElement("defs", null,
                                React.createElement("linearGradient", { id: "assetG", x1: "0%", y1: "0%", x2: "0%", y2: "100%" },
                                    React.createElement("stop", { offset: "0%", stopColor: lineColor, stopOpacity: "0.28" }),
                                    React.createElement("stop", { offset: "100%", stopColor: lineColor, stopOpacity: "0" })
                                )
                            ),
                            React.createElement("path", { d: fillPath, fill: "url(#assetG)" }),
                            React.createElement("path", { d: linePath, fill: "none", stroke: lineColor, strokeWidth: "1.5" })
                        )
                    )
                    : React.createElement("div", { style: { flex: 1, color: "var(--text3)", fontSize: 11, fontFamily: "var(--mono)" } }, "No chart data")
            )
    );
}

function BrainActivityCard({ events, streamStatus }) {
    const kindColor = k => ({ tool_call: "var(--cyan)", tool_result: "var(--teal)", user_input: "var(--orange)", llm_response: "var(--purple)" }[k] ?? "var(--text3)");
    const latest = events[events.length - 1];

    return React.createElement(
        "div", { className: "cc-card cc-card-brain", "data-accent": "purple" },
        React.createElement(
            "div", { className: "cc-brain-header" },
            React.createElement("span", { className: "cc-label" }, "Brain"),
            streamStatus === "live"
                ? React.createElement("span", { className: "cc-live-dot" })
                : React.createElement("span", { className: "cc-stale-pill" }, streamStatus ?? "…")
        ),
        events.length === 0
            ? React.createElement("div", { className: "cc-brain-empty" }, "Idle")
            : React.createElement(
                "div", { className: "cc-brain-list" },
                events.slice().reverse().slice(0, 5).map((row, i) =>
                    React.createElement(
                        "div", { key: row.id ?? i, className: "cc-brain-row" },
                        React.createElement("span", { className: "cc-brain-kind", style: { color: kindColor(row.kind) } },
                            new Date(row.ts * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })
                        ),
                        React.createElement("span", { className: "cc-brain-label" }, brainEventLabel(row))
                    )
                )
            )
    );
}

function HealthCard({ health, healthState }) {
    const status = health?.status ?? null;
    const aiReady = health?.ai?.ready;
    const chat = health?.chat?.configured;
    const monitors = health?.monitors?.configured ?? 0;
    const stopped = health?.monitors?.stopped;
    const total = health?.event_bus?.total_events ?? 0;
    const unproc = health?.event_bus?.unprocessed_events ?? 0;
    const procPct = total > 0 ? Math.round(((total - unproc) / total) * 100) : 100;
    const accent = status === "ok" ? "green" : status === "degraded" ? "red" : "cyan";

    const dot = (color) => React.createElement("span", {
        style: {
            display: "inline-block", width: 6, height: 6, borderRadius: "50%",
            background: color, boxShadow: `0 0 5px ${color}`, flexShrink: 0,
        }
    });
    const row = (label, val, color) => React.createElement(
        "div", { className: "cc-health-compact-row" },
        React.createElement("span", { className: "cc-health-key" }, label),
        React.createElement("span", { className: "cc-health-val", style: { color } }, val)
    );

    return React.createElement(
        "div", { className: "cc-card cc-card-health", "data-accent": accent },
        React.createElement("div", { className: "cc-label" }, "System Health"),

        React.createElement(
            "div", { className: "cc-health-compact" },

            // status pill
            React.createElement(
                "div", { className: "cc-health-status-row" },
                dot(status === "ok" ? "var(--green)" : status === "degraded" ? "var(--red)" : "var(--text3)"),
                React.createElement("span", {
                    style: {
                        fontFamily: "var(--mono)", fontSize: 12, fontWeight: 500,
                        color: status === "ok" ? "var(--green)" : status === "degraded" ? "var(--red)" : "var(--text2)"
                    }
                }, status ? status.toUpperCase() : "CONNECTING…")
            ),

            row("AI", aiReady === true ? "Ready" : aiReady === false ? "Not ready" : "—",
                aiReady === true ? "var(--green)" : aiReady === false ? "var(--red)" : "var(--text2)"),
            row("Chat", chat === true ? "On" : chat === false ? "Off" : "—",
                chat === true ? "var(--green)" : "var(--text2)"),
            row("Monitors", `${monitors} ${stopped === false ? "▶" : stopped === true ? "■" : ""}`,
                stopped === false ? "var(--green)" : "var(--text2)"),
            row("Feed", healthState?.stale ? "Stale" : (health?.source === "health_cache" ? "Cache" : "Live"),
                healthState?.stale ? "var(--orange)" : "var(--text2)"),
        ),

        React.createElement("div", { className: "cc-progress", style: { marginTop: "auto" } },
            React.createElement("div", {
                className: "cc-progress-fill",
                style: { width: `${procPct}%`, background: procPct > 90 ? "var(--green)" : "var(--orange)" },
            })
        )
    );
}

function EventsCard({ health }) {
    const total = health?.event_bus?.total_events ?? 0;
    const unproc = health?.event_bus?.unprocessed_events ?? 0;
    const proc = health?.event_bus?.processed_events ?? 0;
    const bars = useBars([10, 14, 9, 18, 13, 16, 11, 20]);

    return React.createElement(
        "div", { className: "cc-card cc-card-events", "data-accent": "teal" },
        React.createElement("div", { className: "cc-label" }, "Event Bus"),
        React.createElement(
            "div", { style: { display: "flex", gap: 16, marginTop: 2 } },
            React.createElement(
                "div", null,
                React.createElement("div", { style: { fontSize: 22, fontWeight: 300, letterSpacing: "-0.02em" } }, total.toLocaleString()),
                React.createElement("div", { style: { fontSize: 10, color: "var(--text2)", marginTop: 2 } }, "Total")
            ),
            React.createElement(
                "div", null,
                React.createElement("div", { style: { fontSize: 22, fontWeight: 300, letterSpacing: "-0.02em", color: unproc > 0 ? "var(--orange)" : "var(--text)" } },
                    unproc
                ),
                React.createElement("div", { style: { fontSize: 10, color: "var(--text2)", marginTop: 2 } }, "Unprocessed")
            )
        ),
        React.createElement(
            "div", { className: "cc-bars" },
            ...bars.map((h, i) => React.createElement("div", {
                key: i, className: "cc-bar",
                style: { height: `${Math.round((h / 28) * 30)}px`, background: "rgba(90,200,245,0.55)" },
            }))
        )
    );
}

function MonitorsCard({ health }) {
    const configured = health?.monitors?.configured ?? 0;
    const stopped = health?.monitors?.stopped ?? null;
    const sources = health?.monitors?.sources ?? [];
    const bars = useBars([8, 14, 12, 18, 10, 16, 14, 20]);

    return React.createElement(
        "div", { className: "cc-card cc-card-monitors", "data-accent": "green" },
        React.createElement("div", { className: "cc-label" }, "Monitors"),
        React.createElement(
            "div", { style: { display: "flex", alignItems: "baseline", gap: 8, marginTop: 2 } },
            React.createElement("span", { style: { fontSize: 28, fontWeight: 300, letterSpacing: "-0.02em" } }, configured),
            React.createElement("span", { style: { fontSize: 12, color: "var(--text2)" } }, "active")
        ),
        React.createElement(
            "div", { className: "cc-badge-row" },
            stopped === false
                ? React.createElement("span", { className: "cc-badge green" }, "Running")
                : React.createElement("span", { className: "cc-badge dim" }, "Stopped"),
            sources.slice(0, 2).map(s =>
                React.createElement("span", { key: s, className: "cc-badge teal" }, s)
            )
        ),
        React.createElement(
            "div", { className: "cc-bars" },
            ...bars.map((h, i) => React.createElement("div", {
                key: i, className: "cc-bar",
                style: { height: `${Math.round((h / 28) * 30)}px`, background: "rgba(48,209,88,0.5)" },
            }))
        )
    );
}

// ── bottom chrome bar ────────────────────────────────────────────────────────
function ChromeBottom({ health, pending, btcPrice, openMarkets, brainEvents }) {
    const monitors = health?.monitors?.configured ?? "—";
    const totalEvents = health?.event_bus?.total_events ?? "—";
    const unproc = health?.event_bus?.unprocessed_events ?? "—";
    const baseInfo =
        `SYSTEM: ${(health?.status ?? "STANDBY").toUpperCase()}  •  MONITORS: ${monitors}  •  ` +
        `EVENTS: ${totalEvents}  •  UNPROCESSED: ${unproc}  •  PENDING: ${pending ?? "—"}  •  ` +
        `MARKETS OPEN: ${openMarkets} / ${MARKETS.length}  •  ASSET: ${fmtPrice(btcPrice)}  •  `;
    const activity = brainEvents.length > 0
        ? brainEvents.map(brainEventLabel).join("  •  ") + "  •  "
        : "AWAITING BRAIN ACTIVITY  •  ";
    const text = `[+]  ${baseInfo}${activity}[+]  ${baseInfo}${activity}`;
    return React.createElement(
        "div", { className: "cc-chrome-bottom" },
        React.createElement("span", { className: "cc-chrome-cross" }, "[+]"),
        React.createElement(
            "div", { className: "cc-chrome-scroll" },
            React.createElement("span", { className: "cc-chrome-scroll-inner" }, text)
        ),
        React.createElement("span", { className: "cc-chrome-cross" }, "[+]")
    );
}

// ── root ──────────────────────────────────────────────────────────────────────
function App() {
    const now = useClock();
    const healthState = useHealth();
    const pendingState = usePending();
    const health = healthState.data;
    const pending = pendingState.count;
    const brainStream = useBrainStream();
    const brainEvents = brainStream.events;
    const voice = useVoice();
    const [paymentOpen, setPaymentOpen] = React.useState(false);
    const [view, setView] = React.useState("cc");
    // Stop speech when navigating away from Jarvis tab
    React.useEffect(() => {
        if (view !== "jarvis") voice.stopListening();
    }, [view]); // eslint-disable-line react-hooks/exhaustive-deps
    const [coinMeta, setCoinMeta] = React.useState({ id: "bitcoin", name: "Bitcoin", symbol: "btc" });
    const { price, delta, loading: assetLoading, flash: assetFlash } = useAssetPrice(coinMeta.id, coinMeta.symbol);
    const displayAsset = price !== null ? { name: coinMeta.name, symbol: coinMeta.symbol, price, delta } : null;

    const openMarkets = React.useMemo(
        () => MARKETS.filter(m => marketStatus(m, now).open).length,
        [Math.floor(now.getTime() / 60000)]
    );

    const iframeStyle = {
        position: "fixed", top: 40, left: 168, right: 0, bottom: 24,
        width: "calc(100% - 168px)", height: "calc(100vh - 64px)",
        border: "none", zIndex: 1,
    };

    return React.createElement(
        React.Fragment, null,
        React.createElement(TopBar, {
            now, health, healthState, pending, pendingState, brainStream,
            onOpenPayment: () => setPaymentOpen(true),
        }),
        React.createElement(Sidebar, { view, onView: setView, voice, collapsed: view === "jarvis" }),
        React.createElement(ChromeBottom, { health, pending, btcPrice: price ?? 0, openMarkets, brainEvents }),
        React.createElement(PaymentRequestModal, {
            open: paymentOpen,
            onClose: () => setPaymentOpen(false),
            onQueued: () => {
                setPaymentOpen(false);
            },
        }),
        view === "jarvis" && React.createElement(JarvisTab, { voice }),
        view === "globe" && React.createElement("iframe", { src: "/hud/globe", style: iframeStyle, title: "Strategic Globe" }),
        view === "approvals" && React.createElement("iframe", { src: "/", style: iframeStyle, title: "Approvals" }),
        view === "cc" && React.createElement(
            "div", { className: "cc-body" },
            React.createElement(ClockCard, { now }),
            React.createElement(AssetStatCard, { asset: displayAsset, loading: assetLoading, flash: assetFlash }),
            React.createElement(WatchlistCard, { health, pending, pendingState, openMarkets, onSelectAsset: setCoinMeta }),
            React.createElement(NewsCard),
            React.createElement(DatasetsCard),
            React.createElement(AssetChartCard, { coinMeta, onSelect: setCoinMeta, price, delta, loading: assetLoading }),
            React.createElement(BrainActivityCard, { events: brainEvents, streamStatus: brainStream.status }),
            React.createElement(HealthCard, { health, healthState }),
            React.createElement(RuntimeControlCard, { health }),
            React.createElement(MonitorsCard, { health })
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) createRoot(rootEl).render(React.createElement(App));
