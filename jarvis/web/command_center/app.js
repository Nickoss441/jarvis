// ── Datasets Panel ──────────────────────────────────────────────────────────
function fmtSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function DatasetsCard() {
    const [files, setFiles] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState("");
    const [uploading, setUploading] = React.useState(false);
    const [collapsed, setCollapsed] = React.useState({});
    const [downloadProgress, setDownloadProgress] = React.useState(null); // {name, percent}
    const fileInputRef = React.useRef(null);

    const fetchFiles = async () => {
        setLoading(true); setError("");
        try {
            const { data, error } = await fetchJsonResult("/local/files", { timeoutMs: 5000 });
            if (error) throw error;
            // Support both old (string[]) and new ({path,name,size}[]) formats
            const raw = Array.isArray(data.files) ? data.files : [];
            setFiles(raw.map(f => typeof f === "string" ? { path: f, name: f, size: null } : f));
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

    // Download with progress using XHR
    const handleDownload = (filePath, fname) => {
        const url = `/local/file?path=${encodeURIComponent(filePath)}`;
        setDownloadProgress({ name: fname, percent: 0 });
        const xhr = new XMLHttpRequest();
        xhr.open("GET", url, true);
        xhr.responseType = "blob";
        xhr.onprogress = (event) => {
            if (event.lengthComputable) {
                const percent = Math.round((event.loaded / event.total) * 100);
                setDownloadProgress({ name: fname, percent });
            }
        };
        xhr.onload = () => {
            if (xhr.status === 200) {
                const urlBlob = window.URL.createObjectURL(xhr.response);
                const a = document.createElement("a");
                a.href = urlBlob;
                a.download = fname;
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(urlBlob);
                }, 500);
            }
            setDownloadProgress(null);
        };
        xhr.onerror = () => {
            setError("Download failed");
            setDownloadProgress(null);
        };
        xhr.send();
    };

    // Group files by their parent folder (or "" for root)
    // Memoize expensive file grouping to prevent re-render stalls
    const { grouped, folderKeys } = React.useMemo(() => {
        const result = {};
        for (const f of files) {
            const parts = f.path.split("/");
            const folder = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
            if (!result[folder]) result[folder] = [];
            result[folder].push(f);
        }
        return { grouped: result, folderKeys: Object.keys(result).sort() };
    }, [files]);

    const toggleFolder = (key) => setCollapsed(c => ({ ...c, [key]: !c[key] }));

    const renderFolder = (folderKey) => {
        const label = folderKey || "/ (root)";
        const isOpen = !collapsed[folderKey];
        return React.createElement("div", { key: folderKey, style: { marginBottom: 4 } },
            folderKeys.length > 1 && React.createElement(
                "div", {
                onClick: () => toggleFolder(folderKey),
                style: {
                    cursor: "pointer", color: "#22d3ee", fontSize: 12, fontFamily: "'JetBrains Mono',monospace",
                    display: "flex", alignItems: "center", gap: 6, padding: "2px 0", userSelect: "none"
                }
            },
                React.createElement("span", null, isOpen ? "▾" : "▸"),
                React.createElement("span", null, "📁 " + label),
                React.createElement("span", { style: { color: "var(--text3)", marginLeft: 4 } },
                    "(" + grouped[folderKey].length + " file" + (grouped[folderKey].length !== 1 ? "s" : "") + ")")
            ),
            isOpen && grouped[folderKey].map(f =>
                React.createElement(
                    "div", {
                    key: f.path, className: "cc-dataset-row",
                    style: { paddingLeft: folderKeys.length > 1 ? 16 : 0 }
                },
                    React.createElement("span", { className: "cc-dataset-fname" }, f.name),
                    f.size != null && React.createElement("span", {
                        style: { color: "var(--text3)", fontSize: 11, marginLeft: 6, fontFamily: "'JetBrains Mono',monospace" }
                    }, fmtSize(f.size)),
                    React.createElement("button", {
                        className: "cc-runtime-btn", style: { fontSize: 11, marginLeft: "auto" },
                        onClick: () => handleDownload(f.path, f.name)
                    }, "Download")
                )
            )
        );
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
        downloadProgress && React.createElement(
            "div",
            { style: { margin: "8px 0", padding: 4, background: "rgba(34,211,238,0.08)", borderRadius: 6, fontFamily: "'JetBrains Mono',monospace", fontSize: 13, color: "#22d3ee" } },
            `Downloading ${downloadProgress.name}: ${downloadProgress.percent}%`,
            React.createElement("div", { className: "cc-progress-bar" },
                React.createElement("div", {
                    className: "cc-progress-bar-inner",
                    style: {
                        "--fill-scale": String(Math.max(0, Math.min(1, Number(downloadProgress.percent || 0) / 100)))
                    }
                })
            )
        ),
        React.createElement("div", { style: { color: "#22d3ee", fontSize: 12, marginBottom: 8, marginTop: 2 } },
            "For large files (>200KB), drag and drop them directly into D:\\jarvis-data. They will appear here after you refresh."
        ),
        error && React.createElement("div", { style: { color: "#ff453a", fontSize: 12, marginBottom: 8 } }, error),
        React.createElement(
            "div", { className: "cc-datasets-list" },
            files.length === 0 && !loading
                ? React.createElement("div", { style: { color: "var(--text3)", fontSize: 12 } }, "No files found.")
                : folderKeys.map(renderFolder)
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
    {
        id: "hkex", name: "HKEX", city: "Hong Kong", tz: "Asia/Hong_Kong", days: [1, 2, 3, 4, 5],
        sessions: [
            { openH: 9, openM: 30, closeH: 12, closeM: 0 },
            { openH: 13, openM: 0, closeH: 16, closeM: 0 },
        ],
    },
    {
        id: "sse", name: "SSE", city: "Shanghai", tz: "Asia/Shanghai", days: [1, 2, 3, 4, 5],
        sessions: [
            { openH: 9, openM: 30, closeH: 11, closeM: 30 },
            { openH: 13, openM: 0, closeH: 15, closeM: 0 },
        ],
    },
    {
        id: "tse", name: "TSE", city: "Tokyo", tz: "Asia/Tokyo", days: [1, 2, 3, 4, 5],
        sessions: [
            { openH: 9, openM: 0, closeH: 11, closeM: 30 },
            { openH: 12, openM: 30, closeH: 15, closeM: 30 },
        ],
    },
    { id: "asx", name: "ASX", city: "Sydney", tz: "Australia/Sydney", openH: 10, openM: 0, closeH: 16, closeM: 0, days: [1, 2, 3, 4, 5] },
];

// ── helpers ───────────────────────────────────────────────────────────────────

// Randomize color palette for this session (once per page load)
function initSessionColorPalette() {
    // Base colors + randomization hue shift (±15%)
    const colorPalettes = [
        // Warm session (more gold/orange)
        { cyan: "#26d3ee", green: "#24c65e", purple: "#a955f7", orange: "#f5a60b", teal: "#2dd4bf" },
        // Cool session (more cyan/teal)
        { cyan: "#20d5f0", green: "#22c55e", purple: "#9945ff", orange: "#fb923c", teal: "#2dd4bf" },
        // Neutral session (balanced)
        { cyan: "#22d3ee", green: "#22c55e", purple: "#a855f7", orange: "#f59e0b", teal: "#14b8a6" },
        // Purple-dominant session
        { cyan: "#1fb5e6", green: "#10b981", purple: "#b945f7", orange: "#fbbf24", teal: "#2dd4bf" },
        // Green-dominant session
        { cyan: "#22d3ee", green: "#34d399", purple: "#9f5cff", orange: "#f97316", teal: "#2dd4bf" },
    ];

    const selected = colorPalettes[Math.floor(Math.random() * colorPalettes.length)];
    const root = document.documentElement;
    root.style.setProperty('--cyan', selected.cyan);
    root.style.setProperty('--green', selected.green);
    root.style.setProperty('--purple', selected.purple);
    root.style.setProperty('--orange', selected.orange);
    root.style.setProperty('--teal', selected.teal);
}

// Debounce utility for high-frequency event handlers
function debounce(fn, delay = 250) {
    let timeoutId = null;
    return function (...args) {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            fn.apply(this, args);
            timeoutId = null;
        }, delay);
    };
}

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
    const ms = now.getTime();

    const sessions = Array.isArray(m.sessions) && m.sessions.length > 0
        ? m.sessions
        : [{ openH: m.openH, openM: m.openM, closeH: m.closeH, closeM: m.closeM }];

    if (m.days.includes(lp.dow)) {
        for (const s of sessions) {
            const openUTC = wallToUTC(now, m.tz, 0, s.openH, s.openM);
            const closeUTC = wallToUTC(now, m.tz, 0, s.closeH, s.closeM);
            if (ms >= openUTC && ms < closeUTC) {
                return { open: true, deltaMs: closeUTC - ms };
            }
        }
    }

    // next open
    let nextOpenMs = null;
    for (let off = 0; off < 8; off++) {
        const probeDow = (lp.dow + off) % 7;
        if (!m.days.includes(probeDow)) continue;
        for (const s of sessions) {
            const probeOpen = wallToUTC(now, m.tz, off, s.openH, s.openM);
            if (probeOpen > ms && (nextOpenMs === null || probeOpen < nextOpenMs)) {
                nextOpenMs = probeOpen;
            }
        }
    }
    return { open: false, deltaMs: nextOpenMs !== null ? (nextOpenMs - ms) : 0 };
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

const TABLER_SKIN_KEY = "cc:tablerSkin";
const TABLER_SKIN_CLASS = "tabler-skin";
const TABLER_STYLESHEET_ID = "cc-tabler-css";
const TABLER_CSS_URL = "https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0-beta20/dist/css/tabler.min.css";

function applyTablerSkin(enabled) {
    const on = !!enabled;
    document.body.classList.toggle(TABLER_SKIN_CLASS, on);
    const existing = document.getElementById(TABLER_STYLESHEET_ID);
    if (on) {
        if (!existing) {
            const link = document.createElement("link");
            link.id = TABLER_STYLESHEET_ID;
            link.rel = "stylesheet";
            link.href = TABLER_CSS_URL;
            document.head.appendChild(link);
        }
    } else if (existing) {
        existing.remove();
    }
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
    "commodity-oil": { metalKey: "oil", name: "Crude Oil (WTI)", symbol: "WTI", unit: "US$/bbl" },
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
    oil: 78.4,
};

function getDriftedMetalsFallback() {
    const base = _metalsCache ?? METALS_FALLBACK;
    const drift = (v, pct) => Math.max(0, v * (1 + ((Math.random() - 0.5) * pct)));
    return {
        gold: drift(base.gold, 0.0014),
        silver: drift(base.silver, 0.0021),
        platinum: drift(base.platinum, 0.0018),
        palladium: drift(base.palladium, 0.0019),
        oil: drift(base.oil, 0.0032),
    };
}

function parseMetalsPayload(raw) {
    const first = Array.isArray(raw) ? raw[0] : raw;
    if (!first || typeof first !== "object") return null;
    const gold = parseFloat(first.gold);
    const silver = parseFloat(first.silver);
    const platinum = parseFloat(first.platinum);
    const palladium = parseFloat(first.palladium);
    const oil = parseFloat(first.oil);
    if ([gold, silver, platinum, palladium, oil].every((v) => Number.isNaN(v))) {
        return null;
    }
    return {
        gold: Number.isNaN(gold) ? METALS_FALLBACK.gold : gold,
        silver: Number.isNaN(silver) ? METALS_FALLBACK.silver : silver,
        platinum: Number.isNaN(platinum) ? METALS_FALLBACK.platinum : platinum,
        palladium: Number.isNaN(palladium) ? METALS_FALLBACK.palladium : palladium,
        oil: Number.isNaN(oil) ? METALS_FALLBACK.oil : oil,
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
                ...(items.length > 0 ? items.map(item => {
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
                            thumb
                                ? React.createElement("img", {
                                    className: "cc-news-thumb",
                                    src: thumb,
                                    alt: "",
                                    loading: "lazy",
                                    referrerPolicy: "no-referrer",
                                    onError: e => { e.target.style.display = "none"; },
                                })
                                : React.createElement("div", { className: "cc-news-thumb cc-news-thumb-fallback" }, initial),
                            React.createElement(
                                "div", { className: "cc-news-body" },
                                React.createElement("div", { className: "cc-news-title" }, item.title),
                                React.createElement(
                                    "div", { className: "cc-news-meta" },
                                    React.createElement("span", { className: "cc-news-domain" }, item.domain),
                                    React.createElement("span", null, timeAgo(item.created_utc)),
                                    React.createElement("span", { className: "cc-news-score" }, `▲ ${(item.score ?? 0).toLocaleString()}`)
                                )
                            )
                        )
                    );
                }) : [
                    React.createElement("div", { key: "empty", className: "cc-empty-state" }, "No feed items yet.")
                ])
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
    { id: "commodity-oil", name: "Crude Oil (WTI)", symbol: "WTI", market_cap_rank: 0 },
    { id: "commodity-brent", name: "Brent Crude", symbol: "Brent", market_cap_rank: 0 },
    { id: "commodity-natural-gas", name: "Natural Gas", symbol: "NG", market_cap_rank: 0 },
    { id: "commodity-copper", name: "Copper", symbol: "HG", market_cap_rank: 0 },
    { id: "commodity-wheat", name: "Wheat", symbol: "WHEAT", market_cap_rank: 0 },
    { id: "commodity-corn", name: "Corn", symbol: "CORN", market_cap_rank: 0 },
    { id: "commodity-soybean", name: "Soybean", symbol: "SOY", market_cap_rank: 0 },
    { id: "index-sp500", name: "S&P 500", symbol: "SPX", market_cap_rank: 0 },
    { id: "index-nasdaq", name: "NASDAQ 100", symbol: "NDX", market_cap_rank: 0 },
    { id: "index-dow", name: "Dow Jones", symbol: "DJI", market_cap_rank: 0 },
    { id: "index-ftse100", name: "FTSE 100", symbol: "FTSE", market_cap_rank: 0 },
    { id: "index-dax", name: "DAX", symbol: "DAX", market_cap_rank: 0 },
    { id: "index-nikkei", name: "Nikkei 225", symbol: "N225", market_cap_rank: 0 },
    { id: "index-hsi", name: "Hang Seng Index", symbol: "HSI", market_cap_rank: 0 },
    { id: "index-eurostoxx", name: "Euro Stoxx 50", symbol: "SX5E", market_cap_rank: 0 },
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
// Memoized to prevent re-renders when sibling tiles update
const WatchTile = React.memo(function WatchTile({ coin, onRemove, onSelect }) {
    const { price, delta, loading, flash } = useAssetPrice(coin.id, coin.symbol);
    const up = (delta ?? 0) >= 0;
    const isCommodity = COMMODITY_IDS.has(coin.id);
    return React.createElement(
        "div", {
        className: "cc-watch-tile",
        onClick: () => onSelect({ id: coin.id, name: coin.name, symbol: coin.symbol }),
        title: `View ${coin.name} chart`,
    },
        React.createElement(
            "div", { className: "cc-watch-tile-top" },
            React.createElement("span", { className: "cc-watch-name" }, coin.name),
            React.createElement("span", { className: "cc-watch-sym" }, coin.symbol.toUpperCase())
        ),
        loading
            ? React.createElement("div", { className: "cc-spinner", style: { width: 9, height: 9, flexShrink: 0 } })
            : React.createElement("div", {
                className: `cc-watch-price${flash ? ` cc-price-flash-${flash}` : ""}`,
            }, price != null ? fmtPrice(price) : "—"),
        !loading && price != null && !isCommodity
            ? React.createElement("div", {
                className: `cc-delta ${up ? "up" : "down"}`,
                style: { fontSize: 7, padding: "1px 4px" },
            }, up ? "▲" : "▼", ` ${Math.abs(delta ?? 0).toFixed(2)}%`)
            : !loading && isCommodity
                ? React.createElement("span", { style: { fontSize: 8, color: "var(--text3)", fontFamily: "var(--mono)" } }, "oz")
                : null,
        React.createElement("button", {
            className: "cc-watch-remove",
            style: { position: "static", marginLeft: "auto" },
            onClick: e => { e.stopPropagation(); onRemove(coin.id); },
            title: "Remove",
        }, "×")
    );
});

function WatchlistCard({ health, pending, pendingState, openMarkets, onSelectAsset }) {
    const { list, add, remove } = useWatchlist();
    const [addOpen, setAddOpen] = React.useState(false);
    const [query, setQuery] = React.useState("");
    const [focused, setFocused] = React.useState(false);
    const blurTimer = React.useRef(null);
    const { results, searching } = useAssetSearch(query);
    const dropOpen = focused && query.trim().length >= 2;

    // Debounced search to prevent animation blocking on rapid input
    const debouncedSetQuery = React.useMemo(() => debounce((value) => setQuery(value), 200), []);

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
                        onChange: e => { debouncedSetQuery(e.target.value); clearTimeout(blurTimer.current); },
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
    { id: "jarvis", label: "Jarvis" },
    { id: "cc", label: "Command Center" },
    { id: "globe", label: "Strategic Globe" },
    { id: "approvals", label: "Approvals" },
];

const AGENTS = [
    { id: "jarvis", label: "Jarvis", emoji: "🤖" },
    { id: "eva", label: "EVA", emoji: "✦" },
];

const AGENT_STORAGE_KEY = "cc:currentAgent";

const AGENT_WAKE_PHRASES = {
    "jarvis": ["hey jarvis", "jarvis wake up", "wake up jarvis", "ok jarvis"],
    "eva": ["hey eva", "eva wake up", "wake up eva", "ok eva"],
};

// Get wake phrases for current agent (default: Jarvis)
function getWakePhrases() {
    try {
        const agent = localStorage.getItem(AGENT_STORAGE_KEY) || "jarvis";
        return AGENT_WAKE_PHRASES[agent] || AGENT_WAKE_PHRASES["jarvis"];
    } catch (_) {
        return AGENT_WAKE_PHRASES["jarvis"];
    }
}

// Legacy constant for backward compatibility
const WAKE_PHRASES = AGENT_WAKE_PHRASES["jarvis"];

const CHAT_HISTORY_STORAGE_KEY = "cc:chatHistory";
const CHAT_HISTORY_MAX = 120; // keep last N messages in localStorage
const HUD_HISTORY_SYNC_MS = 4000;
const JARVIS_TTS_VOICE_KEY = "cc:jarvisVoice";
const JARVIS_TTS_PREFERRED_NAMES = [
    "Microsoft Aria Online",
    "Microsoft Jenny Online",
    "Microsoft Sonia Online",
    "Google UK English Female",
    "Google US English",
    "Microsoft Ava Online",
    "Microsoft Ryan Online",
    "Microsoft Guy Online",
    "Daniel",
    "Google UK English Male",
];
const EVA_TTS_PREFERRED_NAMES = [
    "Microsoft Aria Online",
    "Microsoft Jenny Online",
    "Microsoft Sonia Online",
    "Microsoft Ava Online",
    "Google UK English Female",
    "Google US English",
    "Samantha",
    "Victoria",
    "Karen",
];

function getCurrentAgentId() {
    try {
        const saved = localStorage.getItem(AGENT_STORAGE_KEY);
        return AGENTS.some(agent => agent.id === saved) ? saved : "jarvis";
    } catch (_) {
        return "jarvis";
    }
}

function getPreferredVoiceSex(agentId = getCurrentAgentId()) {
    return agentId === "eva" ? "female" : "male";
}

function getAgentDisplayName(agentId = getCurrentAgentId()) {
    const agent = AGENTS.find(item => item.id === agentId);
    return agent ? agent.label : "Jarvis";
}

function detectDeviceProfile() {
    const ua = String(navigator.userAgent || "").toLowerCase();
    const width = window.innerWidth || 0;
    const coarsePointer = typeof window.matchMedia === "function"
        ? window.matchMedia("(pointer: coarse)").matches
        : false;
    const touchPoints = Number(navigator.maxTouchPoints || 0);
    const isPhoneUa = /iphone|ipod|android.+mobile|windows phone|mobile/.test(ua);
    const isTabletUa = /ipad|tablet|android(?!.*mobile)|kindle|silk/.test(ua);

    // Treat narrow viewports as responsive phone/tablet layouts even on desktop browsers.
    if (width <= 767) {
        return "phone";
    }
    if (width <= 1100) {
        return "tablet";
    }

    if (isPhoneUa || ((coarsePointer || touchPoints > 1) && width <= 767)) {
        return "phone";
    }
    if (isTabletUa || ((coarsePointer || touchPoints > 1) && width <= 1100)) {
        return "tablet";
    }
    return "desktop";
}

function useDeviceProfile() {
    const [device, setDevice] = React.useState(() => detectDeviceProfile());

    React.useEffect(() => {
        const update = () => setDevice(detectDeviceProfile());
        window.addEventListener("resize", update);
        window.addEventListener("orientationchange", update);
        return () => {
            window.removeEventListener("resize", update);
            window.removeEventListener("orientationchange", update);
        };
    }, []);

    return device;
}

function normalizeHistoryEntry(entry) {
    if (!entry || typeof entry !== "object") return null;
    const role = typeof entry.role === "string" ? entry.role : "user";
    const text = typeof entry.text === "string" ? entry.text.trim() : "";
    const ts = Number.isFinite(entry.ts) ? entry.ts : Date.now();
    if (!text) return null;
    return { role, text, ts };
}

function historiesEqual(left, right) {
    if (left === right) return true;
    if (!Array.isArray(left) || !Array.isArray(right)) return false;
    if (left.length !== right.length) return false;
    for (let index = 0; index < left.length; index += 1) {
        const a = left[index];
        const b = right[index];
        if (!a || !b) return false;
        if (a.role !== b.role || a.text !== b.text || a.ts !== b.ts) return false;
    }
    return true;
}

// Get the current agent name (default: Jarvis)
function getCurrentAgent() {
    try {
        const agent = AGENTS.find(a => a.id === getCurrentAgentId());
        return agent ? agent.label.toUpperCase() : AGENTS[0].label.toUpperCase();
    } catch (_) {
        return AGENTS[0].label.toUpperCase();
    }
}

// Get the current agent emoji + label
function getCurrentAgentDisplay() {
    try {
        const agent = AGENTS.find(a => a.id === getCurrentAgentId());
        return agent ? `${agent.emoji} ${agent.label}` : AGENTS[0].label;
    } catch (_) {
        return AGENTS[0].label;
    }
}

// Detect if user is trying to switch agents
function detectAgentSwitch(text) {
    const lower = text.toLowerCase().trim();
    // Patterns: "switch to eva", "use jarvis", "activate eva", "enable jarvis"
    for (const agent of AGENTS) {
        const patterns = [
            `switch to ${agent.label.toLowerCase()}`,
            `use ${agent.label.toLowerCase()}`,
            `activate ${agent.label.toLowerCase()}`,
            `enable ${agent.label.toLowerCase()}`,
            `switch ${agent.label.toLowerCase()}`,
            `go to ${agent.label.toLowerCase()}`,
            `change to ${agent.label.toLowerCase()}`,
        ];
        if (patterns.some(p => lower.includes(p))) {
            return agent.id;
        }
    }
    return null;
}

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

function pickAgentVoice(voices, preferredName = "", agentId = getCurrentAgentId()) {
    if (!Array.isArray(voices) || voices.length === 0) return null;

    const preferred = String(preferredName || "").trim().toLowerCase();
    if (preferred) {
        const exact = voices.find(v => String(v.name || "").toLowerCase() === preferred);
        if (exact) return exact;
    }

    const preferredNames = agentId === "eva" ? EVA_TTS_PREFERRED_NAMES : JARVIS_TTS_PREFERRED_NAMES;
    const preferredSex = getPreferredVoiceSex(agentId);

    const scored = voices
        .map(v => {
            const name = String(v.name || "");
            const lower = name.toLowerCase();
            const lang = String(v.lang || "").toLowerCase();
            let score = 0;
            // Prefer high-quality English neural voices over gender-specific matching.
            if (lang.startsWith("en")) score += 42;
            else if (lang.startsWith("en-us") || lang.startsWith("en-gb")) score += 38;

            if (lower.includes("neural") || lower.includes("natural")) score += 80;
            if (lower.includes("online")) score += 40;
            if (preferredSex === "female" && (lower.includes("aria") || lower.includes("jenny") || lower.includes("sonia") || lower.includes("ava") || lower.includes("samantha") || lower.includes("victoria") || lower.includes("karen"))) score += 30;
            if (preferredSex === "male" && (lower.includes("ryan") || lower.includes("guy") || lower.includes("daniel") || lower.includes("david") || lower.includes("mark"))) score += 30;
            if (preferredSex === "female" && (lower.includes("female") || lower.includes("woman") || lower.includes("girl"))) score += 24;
            if (preferredSex === "male" && (lower.includes("male") || lower.includes("man") || lower.includes("boy"))) score += 24;
            if (v.localService) score += 8;

            for (let i = 0; i < preferredNames.length; i += 1) {
                if (lower.includes(preferredNames[i].toLowerCase())) {
                    score += 60 - i;
                    break;
                }
            }

            return { v, score };
        })
        .sort((a, b) => b.score - a.score);

    return scored[0]?.v || voices[0] || null;
}

function useVoice(device = "desktop") {
    const isMobileDevice = device === "phone" || device === "tablet";
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
    const [lastWakeHeard, setLastWakeHeard] = React.useState("");
    const recogRef = React.useRef(null);
    const abortRef = React.useRef(null);
    const selectedVoiceRef = React.useRef(null);
    const selectedVoiceNameRef = React.useRef("");
    const onInterimRef = React.useRef(null); // JarvisTab registers setDisplayInput here
    const startListeningRef = React.useRef(null);

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const supported = !!SpeechRecognition;
    const [micPermission, setMicPermission] = React.useState("unknown"); // unknown | granted | denied | prompt
    const [currentAgentId, setCurrentAgentId] = React.useState(() => getCurrentAgentId());

    // Monitor agent switches and update voice accordingly
    React.useEffect(() => {
        const handleStorageChange = () => {
            const newAgent = getCurrentAgentId();
            setCurrentAgentId(newAgent);
        };
        window.addEventListener("storage", handleStorageChange);
        return () => window.removeEventListener("storage", handleStorageChange);
    }, []);

    // Resolve and remember the best available TTS voice for this browser.
    React.useEffect(() => {
        const synth = window.speechSynthesis;
        if (!synth) return;

        try {
            selectedVoiceNameRef.current = localStorage.getItem(JARVIS_TTS_VOICE_KEY) || "";
        } catch (_) { }

        const applyVoice = () => {
            const voices = synth.getVoices();
            const chosen = pickAgentVoice(voices, selectedVoiceNameRef.current, currentAgentId);
            if (!chosen) return;
            selectedVoiceRef.current = chosen;
            selectedVoiceNameRef.current = chosen.name;
            try { localStorage.setItem(JARVIS_TTS_VOICE_KEY, chosen.name); } catch (_) { }
        };

        // Try immediately, then again when browser finishes loading voices.
        applyVoice();
        if (typeof synth.addEventListener === "function") {
            synth.addEventListener("voiceschanged", applyVoice);
            return () => synth.removeEventListener("voiceschanged", applyVoice);
        }
        const prev = synth.onvoiceschanged;
        synth.onvoiceschanged = () => {
            applyVoice();
            if (typeof prev === "function") prev();
        };
        return () => { synth.onvoiceschanged = prev || null; };
    }, [currentAgentId]);

    // On mobile, wait for an explicit user tap before requesting microphone access.
    // Auto-request on page load is unreliable and often blocked by mobile browsers.
    React.useEffect(() => {
        if (!supported) { setMicPermission("unsupported"); return; }
        if (isMobileDevice) {
            setMicPermission("prompt");
            setWakeEnabled(false);
            setMicError(null);
            return;
        }
        let dead = false;
        async function requestMic() {
            if (!navigator.mediaDevices?.getUserMedia) return;
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                if (!dead) {
                    setMicPermission("granted");
                    setWakeEnabled(true);
                }
            } catch (err) {
                if (!dead) {
                    const name = String(err?.name || "");
                    if (name === "NotFoundError") {
                        setMicPermission("denied");
                        setMicError("No microphone detected");
                    } else if (name === "NotAllowedError" || name === "SecurityError") {
                        setMicPermission("denied");
                        setMicError("Mic blocked — allow microphone in browser settings");
                    } else {
                        setMicPermission("prompt");
                        setMicError("Microphone permission required");
                    }
                    setWakeEnabled(false);
                }
            }
        }
        requestMic();
        return () => { dead = true; };
    }, [supported, isMobileDevice]);

    // Persist history to localStorage whenever it changes
    React.useEffect(() => {
        try {
            const trimmed = history.slice(-CHAT_HISTORY_MAX);
            localStorage.setItem(CHAT_HISTORY_STORAGE_KEY, JSON.stringify(trimmed));
        } catch (_) { }
    }, [history]);

    React.useEffect(() => {
        let disposed = false;

        async function syncSharedHistory() {
            try {
                const res = await fetch("/hud/conversation-state", { cache: "no-store" });
                if (!res.ok) return;
                const payload = await res.json();
                const next = Array.isArray(payload.items)
                    ? payload.items.map(normalizeHistoryEntry).filter(Boolean).slice(-CHAT_HISTORY_MAX)
                    : [];
                if (!disposed && next.length > 0) {
                    setHistory(prev => historiesEqual(prev, next) ? prev : next);
                }
            } catch (_) { }
        }

        syncSharedHistory();
        const intervalId = window.setInterval(syncSharedHistory, HUD_HISTORY_SYNC_MS);
        const onFocus = () => { syncSharedHistory(); };
        window.addEventListener("focus", onFocus);
        return () => {
            disposed = true;
            window.clearInterval(intervalId);
            window.removeEventListener("focus", onFocus);
        };
    }, []);


    // Only keep the last N messages for model context
    const MODEL_CONTEXT_LIMIT = 16;

    // Synthesize a short bubble pop using Web Audio API
    const playBubble = React.useCallback((role) => {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            // User: lower, softer. Jarvis: slightly higher, crisper.
            osc.type = "sine";
            osc.frequency.setValueAtTime(role === "user" ? 480 : 620, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(role === "user" ? 320 : 800, ctx.currentTime + 0.06);
            gain.gain.setValueAtTime(0.18, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.12);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.13);
            osc.onended = () => ctx.close();
        } catch (_) { }
    }, []);

    const pushHistory = React.useCallback((role, text) => {
        playBubble(role);
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
        const cleaned = cleanForSpeech(text);
        if (!cleaned) { setState("idle"); return; }
        const currentAgentId = getCurrentAgentId();
        const preferredVoice = getPreferredVoiceSex(currentAgentId);

        // Try ElevenLabs via backend first
        setState("speaking");
        fetch("/hud/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: cleaned, agent: currentAgentId, voice: currentAgentId }),
        })
            .then(res => {
                if (!res.ok) throw new Error("tts_failed");
                return res.arrayBuffer();
            })
            .then(buf => {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                return ctx.decodeAudioData(buf).then(decoded => {
                    const src = ctx.createBufferSource();
                    src.buffer = decoded;
                    src.connect(ctx.destination);
                    src.onended = () => {
                        setState("idle");
                        ctx.close();
                        setTimeout(() => startListeningRef.current?.(), 600);
                    };
                    src.start(0);
                });
            })
            .catch(() => {
                // Fallback to browser speechSynthesis if ElevenLabs unavailable
                const synth = window.speechSynthesis;
                if (!synth) { setState("idle"); return; }
                synth.cancel();
                const utt = new SpeechSynthesisUtterance(cleaned);
                utt.rate = 1.0;
                utt.pitch = 1.0;
                utt.volume = 1.0;
                const voice = pickAgentVoice(synth.getVoices(), selectedVoiceNameRef.current, currentAgentId) || selectedVoiceRef.current;
                if (voice) {
                    selectedVoiceRef.current = voice;
                    selectedVoiceNameRef.current = voice.name;
                    utt.voice = voice;
                    utt.lang = voice.lang || "en-GB";
                    try { localStorage.setItem(JARVIS_TTS_VOICE_KEY, voice.name); } catch (_) { }
                }
                utt.onend = () => { setState("idle"); setTimeout(() => startListeningRef.current?.(), 600); };
                utt.onerror = () => setState("idle");
                synth.speak(utt);
            });
    }, []);

    const ask = React.useCallback(async (text) => {
        if (!text.trim()) return;

        // Check for agent switching commands first
        const switchAgent = detectAgentSwitch(text);
        if (switchAgent) {
            try { localStorage.setItem(AGENT_STORAGE_KEY, switchAgent); } catch (_) { }
            setCurrentAgentId(switchAgent);
            const agent = AGENTS.find(a => a.id === switchAgent);
            const msg = `Switched to ${agent?.label || switchAgent}. Standing by.`;
            pushHistory("user", text);
            pushHistory(switchAgent, msg);
            if (!voiceMuted) speak(msg); else setState("idle");
            return;
        }

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
            const activeAgentId = getCurrentAgentId();
            const res = await fetch("/hud/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text,
                    context: {
                        agent: activeAgentId,
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
            const replyAgentId = typeof j.agent === "string" ? j.agent : activeAgentId;
            setReply(r);
            pushHistory(replyAgentId, r);
            if (!voiceMuted) speak(r); else setState("idle");
        } catch (err) {
            if (err.name === "AbortError") return; // superseded by newer message
            const msg = "Connection error — is the server running?";
            setReply(msg);
            pushHistory(getCurrentAgentId(), msg);
            setState("idle");
        }
    }, [speak, pushHistory, voiceMuted, wakeEnabled, history]);

    const startListening = React.useCallback(async () => {
        if (!supported) {
            setMicPermission("unsupported");
            setMicError("Speech recognition is not available on this browser");
            return;
        }
        // Pause the wake listener so it doesn't conflict
        try { wakeRecogRef.current?.stop(); } catch (_) { }
        if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } }
        if (navigator.mediaDevices?.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                stream.getTracks().forEach(track => track.stop());
                setMicPermission("granted");
                setWakeEnabled(!isMobileDevice);
            } catch (err) {
                const name = String(err?.name || "");
                setMicPermission("denied");
                if (name === "NotFoundError") {
                    setMicError("No microphone detected");
                } else {
                    setMicError("Mic blocked — allow microphone in browser settings");
                }
                setState("idle");
                return;
            }
        }
        const r = new SpeechRecognition();
        r.lang = "en-US"; r.interimResults = true; r.maxAlternatives = 1; r.continuous = !isMobileDevice;
        recogRef.current = r;
        setState("active");
        setMicError(null);
        setTranscript(""); setReply("");
        let silenceTimer = null;
        let accumulated = "";
        r.onresult = e => {
            // Accumulate all results into one transcript
            let full = "";
            for (let i = 0; i < e.results.length; i++) {
                full += e.results[i][0].transcript;
            }
            full = full.trim();
            accumulated = full;
            if (onInterimRef.current) onInterimRef.current(full);
            // Reset silence timer — send 2s after the user stops talking
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(() => {
                if (accumulated) {
                    if (onInterimRef.current) onInterimRef.current("");
                    try { r.stop(); } catch (_) { }
                    ask(accumulated);
                    accumulated = "";
                }
            }, 2000);
        };
        r.onerror = (e) => {
            clearTimeout(silenceTimer);
            if (onInterimRef.current) onInterimRef.current("");
            if (e.error === "not-allowed" || e.error === "service-not-allowed") {
                setMicPermission("denied");
                setMicError("Mic blocked — allow microphone in browser settings");
            } else if (e.error === "audio-capture") {
                setMicPermission("denied");
                setMicError("No microphone detected");
            } else if (e.error === "no-speech") {
                setMicError("No speech detected — try again");
            } else {
                setMicError(`Voice error: ${e.error}`);
            }
            setState("idle");
        };
        r.onend = () => { if (recogRef.current === r) { recogRef.current = null; if (onInterimRef.current) onInterimRef.current(""); } };
        try { r.start(); } catch (err) { setMicError("Could not start microphone"); setState("idle"); }
    }, [supported, ask, isMobileDevice]);

    // Continuous wake-word listener (does not run while main mic is active)
    // wakeActive = "wake mode is armed" (stays true while wakeEnabled, never flickers)
    React.useEffect(() => {
        if (!supported || !wakeEnabled || isMobileDevice) { setWakeActive(false); return; }
        wakeDeadRef.current = false;
        setWakeActive(true); // set once — stays true until wake mode is disabled
        const startWake = () => {
            if (wakeDeadRef.current) return;
            // Don't start wake listener if main mic is already active
            if (recogRef.current) { setTimeout(startWake, 800); return; }
            const r = new SpeechRecognition();
            r.lang = "en-US"; r.continuous = false; r.interimResults = false;
            wakeRecogRef.current = r;
            r.onresult = e => {
                const t = (e.results[0]?.[0]?.transcript ?? "").toLowerCase();
                setLastWakeHeard(t);
                const currentWakePhrases = getWakePhrases();
                if (currentWakePhrases.some(p => t.includes(p))) {
                    startListening();
                } else {
                    setTimeout(startWake, 300);
                }
            };
            r.onerror = (e) => { setLastWakeHeard(`⚠ ${e.error}`); if (!wakeDeadRef.current) setTimeout(startWake, 2000); };
            r.onend = () => { if (!wakeDeadRef.current) setTimeout(startWake, 400); };
            try { r.start(); } catch (_) { setTimeout(startWake, 2000); }
        };
        const t = setTimeout(startWake, 2500);
        return () => {
            wakeDeadRef.current = true;
            setWakeActive(false);
            clearTimeout(t);
            try { wakeRecogRef.current?.stop(); } catch (_) { }
        };
    }, [supported, wakeEnabled, isMobileDevice]); // eslint-disable-line react-hooks/exhaustive-deps

    const stopListening = React.useCallback(() => {
        if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } recogRef.current = null; }
        window.speechSynthesis?.cancel();
        setState("idle");
    }, []);

    const toggleMute = React.useCallback(() => {
        setVoiceMuted(m => {
            const next = !m;
            if (next) {
                // Muting: stop TTS and stop listening
                window.speechSynthesis?.cancel();
                if (recogRef.current) { try { recogRef.current.stop(); } catch (_) { } recogRef.current = null; }
                setWakeEnabled(false);
            } else {
                // Unmuting: re-enable wake listener if mic permission is granted
                if (micPermission === "granted" && !isMobileDevice) setWakeEnabled(true);
            }
            return next;
        });
    }, [micPermission, isMobileDevice]);

    startListeningRef.current = startListening;
    return { state, transcript, reply, history, clearHistory, sessionStartTs, micError, wakeActive, voiceMuted, micPermission, toggleMute, supported, startListening, stopListening, ask, onInterimRef, lastWakeHeard, isMobileDevice, currentAgentId };
}

function JarvisEyeSVG({ state, clipSuffix = "", tired = false, isBg = false, lidColor = "var(--bg)" }) {
    // Eye direction state (angle in degrees, 0 = right, 90 = down, 180 = left, 270 = up)
    const [eyeAngle, setEyeAngle] = React.useState(0);
    // Optionally: randomize or set by prop
    React.useEffect(() => {
        // Example: look in a random direction every 4 seconds
        const interval = setInterval(() => {
            setEyeAngle(Math.floor(Math.random() * 360));
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    // Helper to rotate a point around (50,47)
    function rotate(cx, cy, x, y, angleDeg) {
        const rad = (angleDeg * Math.PI) / 180;
        const dx = x - cx, dy = y - cy;
        const nx = cx + dx * Math.cos(rad) - dy * Math.sin(rad);
        const ny = cy + dx * Math.sin(rad) + dy * Math.cos(rad);
        return [nx, ny];
    }

    // 16 rays at 22.5° intervals — longer and more aggressive
    const rays = Array.from({ length: 16 }, (_, i) => {
        const angle = (i * 22.5 * Math.PI) / 180;
        const inner = i % 2 === 0 ? 46 : 50;
        const outer = i % 2 === 0 ? 62 : 57;
        const [x1, y1] = rotate(50, 47, 50 + Math.cos(angle) * inner, 47 + Math.sin(angle) * inner, eyeAngle);
        const [x2, y2] = rotate(50, 47, 50 + Math.cos(angle) * outer, 47 + Math.sin(angle) * outer, eyeAngle);
        return React.createElement("line", { key: i, className: "eye-ray", x1, y1, x2, y2 });
    });

    const upperLid = "M 30,49 C 38,34 58,36 70,49";
    const lowerLid = "M 30,49 C 40,62 60,60 70,49";
    const clipId = `eye-clip${clipSuffix}`;

    const baseVeins = [
        "M 42,48 L 33,44", "M 44,51 L 36,56", "M 56,48 L 65,44", "M 57,51 L 64,56",
        "M 50,42 L 50,35", "M 50,53 L 50,60",
    ];
    const tiredVeins = tired ? [
        "M 43,47 C 38,46 34,48 30,46", "M 45,50 C 40,53 37,57 34,59",
        "M 57,47 C 62,46 66,48 70,46", "M 55,50 C 60,53 64,56 66,59",
        "M 48,43 C 47,39 49,36 48,32", "M 52,53 C 53,57 51,59 52,63",
        "M 44,46 C 40,44 37,42 34,43", "M 56,52 C 60,54 63,56 66,57",
    ] : [];
    const veins = [...baseVeins, ...tiredVeins];

    // Eye iris and pupil position (move with eyeAngle)
    const irisRadius = 10;
    const irisCenter = rotate(50, 47, 50, 47, eyeAngle);
    const pupilCenter = irisCenter;

    // Scan line — horizontal bar across iris; CSS translateY drives the sweep
    const scanX1 = irisCenter[0] - irisRadius;
    const scanY1 = irisCenter[1];
    const scanX2 = irisCenter[0] + irisRadius;
    const scanY2 = irisCenter[1];

    return React.createElement(
        "svg", { viewBox: "0 0 100 100", xmlns: "http://www.w3.org/2000/svg", width: "100%", height: "100%" },
        React.createElement("defs", null,
            React.createElement("clipPath", { id: clipId },
                React.createElement("path", { d: `${upperLid} ${lowerLid.replace("M 30,49", "L 30,49")} Z` })
            ),
            React.createElement("radialGradient", { id: `iris-grad${clipSuffix}`, cx: "38%", cy: "30%", r: "65%" },
                React.createElement("stop", { offset: "0%", stopColor: "#ffcc88", stopOpacity: 1 }),
                React.createElement("stop", { offset: "18%", stopColor: "#ff8c42", stopOpacity: 1 }),
                React.createElement("stop", { offset: "55%", stopColor: "#d4620e", stopOpacity: 1 }),
                React.createElement("stop", { offset: "82%", stopColor: "#7a2808", stopOpacity: 1 }),
                React.createElement("stop", { offset: "100%", stopColor: "#200600", stopOpacity: 1 }),
            ),
            React.createElement("radialGradient", { id: `sclera-grad${clipSuffix}`, cx: "44%", cy: "38%", r: "60%" },
                React.createElement("stop", { offset: "0%", stopColor: "#f8f4ea", stopOpacity: 1 }),
                React.createElement("stop", { offset: "60%", stopColor: "#e8e2d2", stopOpacity: 1 }),
                React.createElement("stop", { offset: "100%", stopColor: "#b8ae98", stopOpacity: 1 }),
            ),
            React.createElement("radialGradient", {
                id: `cornea-grad${clipSuffix}`, cx: "36%", cy: "26%", r: "55%"
            },
                React.createElement("stop", { offset: "0%", stopColor: "rgba(255,255,255,0.28)" }),
                React.createElement("stop", { offset: "50%", stopColor: "rgba(255,255,255,0.05)" }),
                React.createElement("stop", { offset: "100%", stopColor: "rgba(0,0,0,0.14)" }),
            ),
            React.createElement("filter", { id: `iris-shadow${clipSuffix}`, x: "-30%", y: "-30%", width: "160%", height: "160%" },
                React.createElement("feDropShadow", { dx: "0", dy: "1.5", stdDeviation: "2", floodColor: "#000", floodOpacity: "0.7" }),
            ),
        ),

        React.createElement("circle", { className: "eye-halo", cx: 50, cy: 50, r: 52 }),
        React.createElement("circle", { className: "eye-ping", cx: 50, cy: 50, r: 50 }),
        React.createElement("g", { className: "eye-rays" }, ...rays),
        // 3D pyramid — perspective geometry: apex(50,5), base corners(4,87)(96,87), front-bottom(50,96)
        // Left face faces viewer (lit+dots), right face angles away (dark), base slab shows depth
        (() => {
            const APX = 50, APY = 5;
            const BL = { x: 4, y: 87 };  // back-left base corner
            const BR = { x: 96, y: 87 };  // back-right base corner
            const FT = { x: 50, y: 97 };  // front-bottom center (nearest viewer)
            const SL = { x: 5, y: 93 };  // slab front-left
            const SR = { x: 95, y: 93 };  // slab front-right

            // Stone course lines per face
            const numCourses = 12;
            const stoneLeft = [], stoneRight = [];
            for (let i = 1; i < numCourses; i++) {
                const t = i / numCourses;
                // Left face: lerp apex→BL (left edge) and apex→FT (right edge)
                const lx1 = APX + (BL.x - APX) * t, ly = APY + (BL.y - APY) * t;
                const lx2 = APX + (FT.x - APX) * t;
                // Right face: lerp apex→FT (left edge) and apex→BR (right edge)
                const rx1 = APX + (FT.x - APX) * t, ry = APY + (BR.y - APY) * t;
                const rx2 = APX + (BR.x - APX) * t;
                stoneLeft.push(React.createElement("line", { key: `sl${i}`, className: "eye-tri-stone", x1: lx1, y1: ly, x2: lx2, y2: ly }));
                stoneRight.push(React.createElement("line", { key: `sr${i}`, className: "eye-tri-stone", x1: rx1, y1: ry, x2: rx2, y2: ry }));
            }

            const leftPts = `${APX},${APY} ${BL.x},${BL.y} ${FT.x},${FT.y}`;
            const rightPts = `${APX},${APY} ${FT.x},${FT.y} ${BR.x},${BR.y}`;
            const slabPts = `${BL.x},${BL.y} ${BR.x},${BR.y} ${SR.x},${SR.y} ${SL.x},${SL.y}`;
            const outlinePts = `${APX},${APY} ${BL.x},${BL.y} ${FT.x},${FT.y} ${BR.x},${BR.y}`;

            return React.createElement("g", { className: "eye-triangle" },
                React.createElement("defs", null,
                    React.createElement("clipPath", { id: `tri-left${clipSuffix}` },
                        React.createElement("polygon", { points: leftPts })
                    ),
                    React.createElement("clipPath", { id: `tri-right${clipSuffix}` },
                        React.createElement("polygon", { points: rightPts })
                    ),
                    React.createElement("pattern", { id: `dots${clipSuffix}`, patternUnits: "userSpaceOnUse", width: "5", height: "5" },
                        React.createElement("circle", { cx: "2.5", cy: "2.5", r: "0.9", fill: "var(--eye-color)", opacity: "0.35" })
                    ),
                ),
                // Base slab — darkest, shows pyramid depth
                React.createElement("polygon", { className: "eye-tri-slab", points: slabPts }),
                // Left face — lit
                React.createElement("polygon", { className: "eye-tri-left", points: leftPts }),
                // Right face — shadowed
                React.createElement("polygon", { className: "eye-tri-right", points: rightPts }),
                // Dot grid overlay on left face
                React.createElement("polygon", { points: leftPts, fill: `url(#dots${clipSuffix})`, opacity: 0.7 }),
                // Stone courses
                React.createElement("g", { clipPath: `url(#tri-left${clipSuffix})` }, ...stoneLeft),
                React.createElement("g", { clipPath: `url(#tri-right${clipSuffix})` }, ...stoneRight),
                // Center ridge
                React.createElement("line", { className: "eye-tri-ridge", x1: APX, y1: APY, x2: FT.x, y2: FT.y }),
                // Outline edges
                React.createElement("polyline", { className: "eye-tri-outline", points: `${BL.x},${BL.y} ${APX},${APY} ${BR.x},${BR.y}`, fill: "none" }),
                React.createElement("line", { className: "eye-tri-outline", x1: APX, y1: APY, x2: FT.x, y2: FT.y, strokeWidth: 0 }),
                React.createElement("line", { className: "eye-tri-outline", x1: BL.x, y1: BL.y, x2: FT.x, y2: FT.y }),
                React.createElement("line", { className: "eye-tri-outline", x1: BR.x, y1: BR.y, x2: FT.x, y2: FT.y }),
                React.createElement("line", { className: "eye-tri-outline", x1: BL.x, y1: BL.y, x2: SL.x, y2: SL.y }),
                React.createElement("line", { className: "eye-tri-outline", x1: BR.x, y1: BR.y, x2: SR.x, y2: SR.y }),
                React.createElement("line", { className: "eye-tri-slab-edge", x1: SL.x, y1: SL.y, x2: SR.x, y2: SR.y }),
            );
        })(),
        React.createElement("circle", { className: "eye-orbit-ring", cx: 50, cy: 50, r: 44 }),

        // Static lid mask — only on small button eye, not the large bg eye
        !isBg && React.createElement("path", { fill: lidColor, d: `M 30,49 C 38,34 58,36 70,49 L 100,0 L 0,0 Z` }),

        // Sclera — 3D gradient
        React.createElement("path", {
            className: "eye-white",
            d: `${upperLid} ${lowerLid.replace("M 30,49", "L 30,49")} Z`,
            fill: `url(#sclera-grad${clipSuffix})`,
            style: tired ? { filter: "saturate(1.4) sepia(0.45) hue-rotate(-10deg) brightness(0.9)" } : undefined,
        }),

        ...veins.map((d, i) => React.createElement("path", {
            key: `v${i}`, d,
            stroke: tired && i >= 6 ? "rgba(220,20,0,0.7)" : "rgba(180,30,10,0.35)",
            strokeWidth: tired && i >= 6 ? 0.9 : 0.6,
            fill: "none",
            clipPath: `url(#${clipId})`,
            className: "eye-vein",
        })),

        // Iris + effects clipped to eye shape
        React.createElement("g", { clipPath: `url(#${clipId})`, style: { filter: `url(#iris-shadow${clipSuffix})` } },
            React.createElement("circle", { className: "eye-iris", cx: irisCenter[0], cy: irisCenter[1], r: irisRadius, fill: `url(#iris-grad${clipSuffix})` }),
            React.createElement("circle", { cx: irisCenter[0], cy: irisCenter[1], r: irisRadius, fill: "none", stroke: "rgba(0,0,0,0.65)", strokeWidth: 2.2 }),
            React.createElement("line", { className: "eye-scan-line", x1: scanX1, y1: scanY1, x2: scanX2, y2: scanY2 }),
            React.createElement("circle", { className: "eye-ripple eye-ripple-1", cx: irisCenter[0], cy: irisCenter[1], r: irisRadius }),
            React.createElement("circle", { className: "eye-ripple eye-ripple-2", cx: irisCenter[0], cy: irisCenter[1], r: irisRadius }),
            React.createElement("circle", { className: "eye-ripple eye-ripple-3", cx: irisCenter[0], cy: irisCenter[1], r: irisRadius }),
            React.createElement("ellipse", { className: "eye-pupil", cx: pupilCenter[0], cy: pupilCenter[1], rx: 2.2, ry: 7 }),
            React.createElement("ellipse", { className: "eye-glint", cx: irisCenter[0] - 3.5, cy: irisCenter[1] - 3.5, rx: 1.8, ry: 1.1 }),
            React.createElement("path", { d: `${upperLid} ${lowerLid.replace("M 30,49", "L 30,49")} Z`, fill: `url(#cornea-grad${clipSuffix})` }),
        ),

        // Blink — separate elements, each with its own transform-origin so no gap
        !isBg && React.createElement("path", { className: "eye-lid-upper-blink", fill: lidColor, d: `M 0,0 L 100,0 L 100,49 C 70,36 30,36 0,49 Z` }),
        !isBg && React.createElement("path", { className: "eye-lid-lower-blink", fill: lidColor, d: `M 0,100 L 100,100 L 100,49 C 70,62 30,62 0,49 Z` }),

        // Lid edge strokes — subtle crease lines on top
        React.createElement("g", { className: "eye-lid-stroke-group" },
            React.createElement("path", { className: "eye-lid-upper", d: upperLid }),
            React.createElement("path", { className: "eye-lid-lower", d: lowerLid }),
        ),
    );
}

function CameraTab({ onSendToJarvis }) {
    const videoRef = React.useRef(null);
    const canvasRef = React.useRef(null);
    const [camError, setCamError] = React.useState(null);
    const [description, setDescription] = React.useState("");
    const [focusRegions, setFocusRegions] = React.useState([]);
    const [people, setPeople] = React.useState([]);
    const [question, setQuestion] = React.useState("");
    const [loading, setLoading] = React.useState(false);
    const [autoInterval, setAutoInterval] = React.useState(5); // seconds, 0 = off
    const [stream, setStream] = React.useState(null);
    const intervalRef = React.useRef(null);

    // Start webcam on mount
    React.useEffect(() => {
        let dead = false;
        navigator.mediaDevices?.getUserMedia({ video: { facingMode: "user" } })
            .then(s => {
                if (dead) { s.getTracks().forEach(t => t.stop()); return; }
                setStream(s);
                if (videoRef.current) videoRef.current.srcObject = s;
            })
            .catch(err => setCamError("Camera blocked — allow camera access in browser settings"));
        return () => {
            dead = true;
            clearInterval(intervalRef.current);
        };
    }, []);

    // Stop stream on unmount
    React.useEffect(() => {
        return () => { stream?.getTracks().forEach(t => t.stop()); };
    }, [stream]);

    const captureFrame = () => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas || video.readyState < 2) return null;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        // Strip the "data:image/jpeg;base64," prefix
        return canvas.toDataURL("image/jpeg", 0.8).split(",")[1];
    };

    const analyze = React.useCallback(async (q, opts = {}) => {
        const fromAuto = !!opts.auto;
        const b64 = captureFrame();
        if (!b64) {
            setDescription("No camera frame available yet. Wait for video preview, then try again.");
            setFocusRegions([]);
            setPeople([]);
            return;
        }
        setLoading(true);
        try {
            const res = await fetch("/hud/vision/frame", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image_b64: b64, question: q || "Describe what you see in this image concisely." }),
            });
            let j = {};
            try { j = await res.json(); } catch (_) { }
            if (!res.ok) {
                const errMsg = j.error || `Vision request failed (${res.status})`;
                setDescription(`Vision error: ${errMsg}`);
                setFocusRegions([]);
                setPeople([]);
                return;
            }
            const desc = j.description || j.error || "No response";
            setDescription(desc);
            setFocusRegions(Array.isArray(j.focus_regions) ? j.focus_regions : []);
            setPeople(Array.isArray(j.people) ? j.people : []);

            const peopleSummary = Array.isArray(j.people)
                ? j.people
                    .map((p, idx) => {
                        const personId = p?.index || idx + 1;
                        const gender = p?.gender || "unknown";
                        const age = p?.age_range || "unknown";
                        const mood = p?.mood || "unknown";
                        const confidence = p?.confidence ? ` (${p.confidence})` : "";
                        return `Person ${personId}: ${gender}, ${age}, ${mood}${confidence}`;
                    })
                    .join("\n")
                : "";

            // Integrate camera analysis into Jarvis chat flow (manual analyze only)
            if (!fromAuto && typeof onSendToJarvis === "function" && desc && !String(desc).toLowerCase().startsWith("vision error:")) {
                const prompt = [
                    "Camera analysis result:",
                    desc,
                    peopleSummary ? `\nPerceived face attributes:\n${peopleSummary}` : "",
                    q ? `\nOperator question: ${q}` : "",
                    "\nUse this visual context in your response."
                ].join("\n");
                onSendToJarvis(prompt);
            }
        } catch (e) {
            setDescription("Connection error — is the server running?");
            setFocusRegions([]);
            setPeople([]);
        } finally {
            setLoading(false);
        }
    }, [onSendToJarvis]);

    // Auto-capture interval
    React.useEffect(() => {
        clearInterval(intervalRef.current);
        if (autoInterval > 0 && stream) {
            intervalRef.current = setInterval(() => analyze("", { auto: true }), autoInterval * 1000);
        }
        return () => clearInterval(intervalRef.current);
    }, [autoInterval, stream, analyze]);

    return React.createElement("div", { className: "cc-camera-tab" },
        // Header
        React.createElement("div", { className: "cc-camera-header" },
            React.createElement("span", { className: "cc-camera-title" }, "CAMERA FEED"),
            React.createElement("span", { className: "cc-camera-subtitle" }, "Auto-analyze every:"),
            React.createElement("select", {
                value: autoInterval,
                onChange: e => setAutoInterval(Number(e.target.value)),
                className: "cc-camera-select",
            },
                React.createElement("option", { value: 0 }, "Off"),
                React.createElement("option", { value: 3 }, "3s"),
                React.createElement("option", { value: 5 }, "5s"),
                React.createElement("option", { value: 10 }, "10s"),
                React.createElement("option", { value: 30 }, "30s"),
            ),
            loading && React.createElement("span", { className: "cc-camera-loading" }, "Analyzing…"),
        ),

        // Main area: video + description side by side
        React.createElement("div", { className: "cc-camera-main" },

            // Video
            React.createElement("div", { className: "cc-camera-video-wrap" },
                camError
                    ? React.createElement("div", { className: "cc-camera-error" }, camError)
                    : React.createElement("video", {
                        ref: videoRef, autoPlay: true, playsInline: true, muted: true,
                        className: "cc-camera-video",
                    }),
                !camError && React.createElement(
                    "div", { className: "cc-camera-overlay" },
                    focusRegions.map((region, idx) => {
                        const x = Math.max(0, Math.min(100, Number(region?.x || 0) * 100));
                        const y = Math.max(0, Math.min(100, Number(region?.y || 0) * 100));
                        const w = Math.max(0, Math.min(100, Number(region?.w || 0) * 100));
                        const h = Math.max(0, Math.min(100, Number(region?.h || 0) * 100));
                        const color = String(region?.color || "#22d3ee");
                        return React.createElement("div", {
                            key: `focus-${idx}`,
                            className: "cc-camera-focus-box",
                            style: {
                                left: `${x}%`,
                                top: `${y}%`,
                                width: `${w}%`,
                                height: `${h}%`,
                                borderColor: color,
                                boxShadow: `0 0 0 1px ${color}4d, 0 0 14px ${color}26`,
                            },
                        },
                            React.createElement("span", { className: "cc-camera-focus-label" }, region?.label || `Target ${idx + 1}`)
                        );
                    })
                ),
                React.createElement("canvas", { ref: canvasRef, style: { display: "none" } }),
            ),

            // Description panel
            React.createElement("div", { className: "cc-camera-insights" },
                React.createElement("div", { className: "cc-camera-insights-title" }, "What Jarvis sees:"),
                React.createElement("div", {
                    className: `cc-camera-description${description ? " has-content" : ""}`,
                }, description || (loading ? "Analyzing…" : "Press Analyze or set auto-interval to start.")),

                React.createElement("div", { className: "cc-camera-face-list" },
                    React.createElement("div", { className: "cc-camera-face-title" }, "Face Insights (perceived estimate):"),
                    people.length === 0
                        ? React.createElement("div", { className: "cc-camera-face-empty" }, "No clear face attributes yet.")
                        : people.map((person, idx) => React.createElement("div", {
                            key: `face-${person?.index || idx}`,
                            className: "cc-camera-face-item",
                        },
                            React.createElement("span", { className: "cc-camera-face-chip" }, `P${person?.index || idx + 1}`),
                            React.createElement("span", { className: "cc-camera-face-text" }, `${person?.gender || "unknown"} | ${person?.age_range || "unknown"} | ${person?.mood || "unknown"}`),
                            React.createElement("span", { className: "cc-camera-face-confidence" }, person?.confidence || "unknown")
                        )),
                ),

                // Question input
                React.createElement("div", { className: "cc-camera-controls" },
                    React.createElement("input", {
                        value: question,
                        onChange: e => setQuestion(e.target.value),
                        onKeyDown: e => { if (e.key === "Enter") analyze(question); },
                        placeholder: "Ask about what you see…",
                        className: "cc-camera-question",
                    }),
                    React.createElement(
                        "div", { className: "cc-camera-actions" },
                        React.createElement("button", {
                            onClick: () => analyze(question, { auto: false }),
                            disabled: loading || !stream,
                            className: "cc-camera-btn cc-camera-btn-primary",
                        }, loading ? "Analyzing…" : "Analyze Now"),
                        React.createElement("button", {
                            onClick: () => {
                                if (!description || typeof onSendToJarvis !== "function") return;
                                onSendToJarvis(["Camera analysis result:", description, "\nUse this visual context in your response."].join("\n"));
                            },
                            disabled: !description || loading || typeof onSendToJarvis !== "function",
                            className: "cc-camera-btn cc-camera-btn-secondary",
                        }, "Send to Jarvis Chat"),
                    ),
                ),
            ),
        ),
    );
}

const JARVIS_COMPOSER_ICONS = {
    attach: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("path", { d: "M7.2 10.9l4.8-4.8a2.7 2.7 0 1 1 3.8 3.8L9.5 16.2a4.2 4.2 0 1 1-5.9-5.9L9.7 4.2" })
    ),
    camera: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("rect", { x: 2, y: 5, width: 16, height: 12, rx: 2.2 }),
        React.createElement("circle", { cx: 10, cy: 11, r: 3.1 }),
        React.createElement("path", { d: "M6.2 5l1.2-2h5.2l1.2 2" })
    ),
    mic: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("rect", { x: 7, y: 3, width: 6, height: 10, rx: 3 }),
        React.createElement("path", { d: "M4.5 9.8a5.5 5.5 0 0 0 11 0M10 15.5V18M7.3 18h5.4" })
    ),
    stop: React.createElement("svg", { viewBox: "0 0 20 20", fill: "currentColor", className: "jarvis-pill-icon" },
        React.createElement("rect", { x: 6, y: 6, width: 8, height: 8, rx: 1.2 })
    ),
    volumeOn: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("path", { d: "M3 8h3l4-3v10l-4-3H3zM13 8.2a3.2 3.2 0 0 1 0 3.6M15.2 6.5a6 6 0 0 1 0 7" })
    ),
    volumeOff: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("path", { d: "M3 8h3l4-3v10l-4-3H3zM13 8l4 4M17 8l-4 4" })
    ),
    reset: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", className: "jarvis-pill-icon" },
        React.createElement("path", { d: "M4.5 6h11M7.5 6V4.5h5V6M7 6v9h6V6" }),
        React.createElement("path", { d: "M9 8.5v4.5M11 8.5v4.5" })
    ),
    loading: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", className: "jarvis-pill-icon jarvis-pill-icon-spin" },
        React.createElement("circle", { cx: 10, cy: 10, r: 7, stroke: "currentColor", strokeWidth: 2, opacity: 0.25 }),
        React.createElement("path", { d: "M10 3a7 7 0 0 1 7 7", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" })
    ),
};

function JarvisTab({ voice, onOpenCamera }) {
    const { state, history, clearHistory, sessionStartTs, micError, wakeActive, voiceMuted, micPermission, toggleMute, supported, startListening, stopListening, ask, onInterimRef, lastWakeHeard, isMobileDevice } = voice;
    const [input, setInput] = React.useState("");
    const [displayInput, setDisplayInput] = React.useState("");
    const [pendingAttachments, setPendingAttachments] = React.useState([]);
    const [imagePreviewMap, setImagePreviewMap] = React.useState({});
    const previewUrlsRef = React.useRef(new Set());

    // Let the voice hook write interim speech transcripts directly into the input box
    React.useEffect(() => {
        if (onInterimRef) onInterimRef.current = setDisplayInput;
        return () => { if (onInterimRef) onInterimRef.current = null; };
    }, [onInterimRef, setDisplayInput]);

    // Debounced input update to prevent animation blocking on rapid typing
    const debouncedSetInput = React.useMemo(() => debounce((value) => setInput(value), 150), []);
    const [showPast, setShowPast] = React.useState(false);
    const [resetting, setResetting] = React.useState(false);
    const [uploadingImage, setUploadingImage] = React.useState(false);
    const logRef = React.useRef(null);
    const inputRef = React.useRef(null);
    const uploadInputRef = React.useRef(null);

    React.useEffect(() => {
        return () => {
            for (const url of previewUrlsRef.current) {
                try { URL.revokeObjectURL(url); } catch (_) { }
            }
            previewUrlsRef.current.clear();
        };
    }, []);

    const handleResetMemory = async () => {
        setResetting(true);
        try {
            await fetch("/hud/reset-conversation", { method: "POST" });
            clearHistory();
        } catch (_) { }
        setResetting(false);
    };

    // Split: messages from before this page load vs. this session
    const pastMsgs = history.filter(m => m.ts < sessionStartTs.current);
    const currentMsgs = history.filter(m => m.ts >= sessionStartTs.current);

    // Auto-scroll to bottom only for new current-session messages
    React.useEffect(() => {
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    }, [currentMsgs.length, state]);

    const handleSend = async () => {
        const t = displayInput.trim();
        if (!t && pendingAttachments.length === 0) return;
        if (t === "/stop") {
            // Stop any in-flight chat or TTS
            window.speechSynthesis?.cancel();
            if (voice.abortRef && voice.abortRef.current) {
                try { voice.abortRef.current.abort(); } catch (_) { }
                voice.abortRef.current = null;
            }
            if (voice.stopListening) voice.stopListening();
            if (voice.setState) voice.setState("idle");
            return;
        }

        if (pendingAttachments.length === 0) {
            setDisplayInput("");
            setInput("");
            ask(t);
            requestAnimationFrame(() => inputRef.current?.focus());
            return;
        }

        setUploadingImage(true);
        try {
            const attachmentSections = [];
            const sentImagePreviews = {};

            for (const attachment of pendingAttachments) {
                if (attachment.kind === "image") {
                    const b64 = await toBase64(attachment.file);
                    const question = t
                        ? `User intent: ${t}. Analyze this image and suggest practical edits/fixes if relevant.`
                        : "Analyze this image and explain what it is. If helpful, suggest practical edits or fixes.";
                    const res = await fetch("/hud/vision/frame", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ image_b64: b64, question }),
                    });
                    const j = await res.json().catch(() => ({}));
                    if (!res.ok) {
                        const errMsg = j.error || `Vision request failed (${res.status})`;
                        throw new Error(`Image analysis failed for ${attachment.name}: ${errMsg}`);
                    }

                    const desc = j.description || "No analysis response.";
                    const peopleSummary = Array.isArray(j.people)
                        ? j.people
                            .map((p, idx) => {
                                const id = p?.index || idx + 1;
                                const gender = p?.gender || "unknown";
                                const age = p?.age_range || "unknown";
                                const mood = p?.mood || "unknown";
                                return `Person ${id}: ${gender}, ${age}, ${mood}`;
                            })
                            .join("\n")
                        : "";

                    attachmentSections.push([
                        `Uploaded image: ${attachment.name}`,
                        "Vision analysis:",
                        desc,
                        peopleSummary ? `\nFace insights:\n${peopleSummary}` : "",
                    ].join("\n"));
                    if (attachment.previewUrl) sentImagePreviews[attachment.name] = attachment.previewUrl;
                    continue;
                }

                attachmentSections.push([
                    `Attached file: ${attachment.name}`,
                    `Type: ${attachment.type || "unknown"}`,
                    `Size: ${fmtSize(attachment.size || 0)}`,
                    "Treat this file as user-provided context. If its internal contents are needed, ask the user what part to inspect next.",
                ].join("\n"));
            }

            const prompt = [
                t ? `User request:\n${t}` : "User request:\nHelp with the attached items.",
                "",
                "Attachments:",
                attachmentSections.join("\n\n"),
                "",
                "Respond with clear practical help using the attached context.",
            ].join("\n");

            if (Object.keys(sentImagePreviews).length > 0) {
                setImagePreviewMap(prev => ({ ...prev, ...sentImagePreviews }));
            }
            setPendingAttachments([]);
            setDisplayInput("");
            setInput("");
            ask(prompt);
        } catch (error) {
            ask(error instanceof Error ? error.message : "Attachment processing failed.");
            return;
        } finally {
            setUploadingImage(false);
        }
        // Return focus to the input box after sending
        requestAnimationFrame(() => inputRef.current?.focus());
    };

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const toBase64 = (file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const raw = typeof reader.result === "string" ? reader.result : "";
            const comma = raw.indexOf(",");
            resolve(comma >= 0 ? raw.slice(comma + 1) : raw);
        };
        reader.onerror = () => reject(new Error("Could not read file"));
        reader.readAsDataURL(file);
    });

    const imagePreviewsForEntry = React.useCallback((entryText) => {
        const lines = String(entryText || "").split("\n");
        const seen = new Set();
        const previews = [];
        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line.startsWith("Uploaded image:")) continue;
            const fileName = line.slice("Uploaded image:".length).trim();
            if (!fileName || seen.has(fileName) || !imagePreviewMap[fileName]) continue;
            seen.add(fileName);
            previews.push({ name: fileName, url: imagePreviewMap[fileName] });
        }
        return previews;
    }, [imagePreviewMap]);

    const handleAttachmentSelect = (e) => {
        const files = Array.from(e.target.files || []);
        if (files.length === 0) return;

        const nextAttachments = files.map((file, index) => {
            const isImage = typeof file.type === "string" && file.type.startsWith("image/");
            const previewUrl = isImage ? URL.createObjectURL(file) : "";
            if (previewUrl) previewUrlsRef.current.add(previewUrl);
            return {
                id: `${Date.now()}-${index}-${Math.random().toString(36).slice(2, 8)}`,
                file,
                name: file.name,
                type: file.type,
                size: file.size,
                kind: isImage ? "image" : "file",
                previewUrl,
            };
        });

        setPendingAttachments(prev => [...prev, ...nextAttachments]);
        e.target.value = "";
    };

    const removePendingAttachment = (attachmentId) => {
        setPendingAttachments(prev => {
            const attachment = prev.find(item => item.id === attachmentId);
            if (attachment?.previewUrl) {
                try { URL.revokeObjectURL(attachment.previewUrl); } catch (_) { }
                previewUrlsRef.current.delete(attachment.previewUrl);
            }
            return prev.filter(item => item.id !== attachmentId);
        });
    };

    const renderMessage = React.useCallback((entry, key) => {
        const previewItems = entry.role === "user" ? imagePreviewsForEntry(entry.text) : [];
        return React.createElement(
            "div", { key, className: `jarvis-msg jarvis-msg-${entry.role}` },
            React.createElement("span", { className: "jarvis-msg-role" }, entry.role === "user" ? "You" : getAgentDisplayName(entry.role)),
            React.createElement(
                "div", { className: "jarvis-msg-body" },
                previewItems.length > 0 && React.createElement(
                    "div", { className: "jarvis-msg-preview-list" },
                    previewItems.map((item) => React.createElement("img", {
                        key: item.name,
                        className: "jarvis-msg-preview",
                        src: item.url,
                        alt: item.name,
                        loading: "lazy",
                    }))
                ),
                React.createElement("span", { className: "jarvis-msg-text" }, entry.text)
            ),
            React.createElement("span", { className: "jarvis-msg-ts" },
                new Date(entry.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
            )
        );
    }, [imagePreviewsForEntry]);

    const stateLabel = { idle: "Standby", active: "Listening…", thinking: "Thinking…", speaking: "Speaking…" }[state] ?? "Standby";
    const isTired = new Date().getHours() < 6;
    const hasMessages = currentMsgs.length > 0 || pastMsgs.length > 0 || state === "thinking";

    return React.createElement(
        "div", { className: "jarvis-tab" },

        // ── Hero (visible when no conversation) ──
        React.createElement(
            "div", { className: `jarvis-hero${hasMessages ? " jarvis-hero--hidden" : ""}`, "aria-hidden": hasMessages },
            React.createElement(
                "div", { className: `jarvis-hero-eye jarvis-eye ${state}${isTired ? " tired" : ""}` },
                React.createElement(JarvisEyeSVG, { state, clipSuffix: "hero", tired: isTired, isBg: true })
            ),
            React.createElement("div", { className: "jarvis-hero-title" }, "JARVIS"),
            React.createElement(
                "div", { className: "jarvis-hero-status" },
                React.createElement("span", { className: `jarvis-wake-dot${wakeActive ? " on" : ""}` }),
                React.createElement("span", { className: "jarvis-hero-state" },
                    supported
                        ? (isMobileDevice ? "Tap the mic to speak" : (wakeActive ? `Listening for "Hey ${getAgentDisplayName()}"` : stateLabel))
                        : "Speech not supported"
                )
            )
        ),

        // ── Background watermark eye when chatting ──
        hasMessages && React.createElement(
            "div", { className: `jarvis-eye-bg jarvis-eye ${state}${isTired ? " tired" : ""}`, "aria-hidden": "true" },
            React.createElement(JarvisEyeSVG, { state, clipSuffix: "bg", tired: isTired, isBg: true })
        ),

        // ── Status badge shown while chatting ──
        hasMessages && React.createElement(
            "div", { className: "jarvis-status-badge" },
            React.createElement("span", { className: `jarvis-wake-dot${wakeActive ? " on" : ""}` }),
            React.createElement("span", { className: "jarvis-badge-state" }, stateLabel),
            React.createElement("span", { className: "jarvis-badge-persona" }, getCurrentAgentDisplay()),
            lastWakeHeard ? React.createElement("span", {
                style: { marginLeft: 8, fontSize: 10, color: lastWakeHeard.startsWith("⚠") ? "#f87171" : "#22d3ee", opacity: 0.7 }
            }, `"${lastWakeHeard}"`) : null
        ),

        // ── Conversation log ──
        hasMessages && React.createElement(
            "div", { className: "jarvis-log", ref: logRef },
            pastMsgs.length > 0 && React.createElement(
                "div", { className: "jarvis-history-divider", onClick: () => setShowPast(v => !v) },
                React.createElement("span", { className: "jarvis-history-toggle" }, showPast ? "▲" : "▼"),
                React.createElement("span", null, `${pastMsgs.length} previous message${pastMsgs.length === 1 ? "" : "s"}`),
                !showPast && React.createElement("span", { className: "jarvis-history-hint" }, "tap to expand")
            ),
            showPast && pastMsgs.map((entry, i) => {
                const node = renderMessage(entry, `past-${i}`);
                return React.cloneElement(node, { className: `${node.props.className} jarvis-msg-past` });
            }),
            currentMsgs.map((entry, i) => renderMessage(entry, `cur-${i}`)),
            state === "thinking" && React.createElement(
                "div", { className: "jarvis-msg jarvis-msg-jarvis jarvis-msg-thinking" },
                React.createElement("span", { className: "jarvis-msg-role" }, getAgentDisplayName()),
                React.createElement("span", { className: "jarvis-thinking-dots" },
                    React.createElement("span"), React.createElement("span"), React.createElement("span")
                )
            )
        ),

        // ── Mic banners ──
        micError && React.createElement("div", { className: "jarvis-mic-banner jarvis-mic-denied" }, micError),
        (micPermission === "prompt" || micPermission === "denied") && React.createElement(
            "div", { className: "jarvis-mic-banner jarvis-mic-prompt" },
            React.createElement("button", { className: "jarvis-mic-grant-btn", onClick: startListening },
                micPermission === "denied" ? "Retry microphone access" : "Grant microphone access"
            ),
            React.createElement("span", null, micPermission === "denied"
                ? " — if blocked, allow mic for this site then retry"
                : (isMobileDevice ? " — phone voice starts after you tap" : " — required for voice commands")
            )
        ),

        // ── Floating pill input ──
        React.createElement(
            "div", { className: "jarvis-compose-stack" },
            pendingAttachments.length > 0 && React.createElement(
                "div", { className: "jarvis-attachment-tray" },
                pendingAttachments.map((attachment) => React.createElement(
                    "div", { key: attachment.id, className: "jarvis-attachment-chip" },
                    attachment.previewUrl
                        ? React.createElement("img", { className: "jarvis-attachment-thumb", src: attachment.previewUrl, alt: attachment.name })
                        : React.createElement("div", { className: "jarvis-attachment-icon", "aria-hidden": "true" }, "FILE"),
                    React.createElement(
                        "div", { className: "jarvis-attachment-meta" },
                        React.createElement("span", { className: "jarvis-attachment-name" }, attachment.name),
                        React.createElement("span", { className: "jarvis-attachment-detail" }, `${attachment.kind === "image" ? "Image" : "File"} • ${fmtSize(attachment.size || 0)}`)
                    ),
                    React.createElement("button", {
                        type: "button",
                        className: "jarvis-attachment-remove",
                        onClick: () => removePendingAttachment(attachment.id),
                        title: `Remove ${attachment.name}`,
                    }, "×")
                ))
            ),
            React.createElement(
                "div", { className: "jarvis-input-pill" },
                React.createElement("input", {
                    ref: uploadInputRef, type: "file", multiple: true,
                    style: { display: "none" }, onChange: handleAttachmentSelect,
                }),
                React.createElement("button", {
                    className: "jarvis-pill-btn jarvis-pill-attach",
                    onClick: () => uploadInputRef.current?.click(),
                    disabled: uploadingImage || state === "thinking",
                    title: "Add attachment",
                }, uploadingImage ? JARVIS_COMPOSER_ICONS.loading : JARVIS_COMPOSER_ICONS.attach),
                React.createElement("button", {
                    className: "jarvis-pill-btn jarvis-pill-camera",
                    onClick: onOpenCamera,
                    title: "Open camera",
                }, JARVIS_COMPOSER_ICONS.camera),
                React.createElement("textarea", {
                    className: "jarvis-input",
                    ref: inputRef,
                    value: displayInput,
                    onChange: e => { setDisplayInput(e.target.value); debouncedSetInput(e.target.value); },
                    onKeyDown: handleKey,
                    placeholder: `Message ${getAgentDisplayName()}…`,
                    rows: 1,
                }),
                supported && (state === "active" || state === "speaking"
                    ? React.createElement("button", {
                        className: "jarvis-pill-btn jarvis-pill-stop",
                        onClick: stopListening, title: "Stop",
                    }, JARVIS_COMPOSER_ICONS.stop)
                    : React.createElement("button", {
                        className: "jarvis-pill-btn jarvis-pill-mic",
                        onClick: startListening,
                        disabled: state === "thinking", title: "Click to speak",
                    }, JARVIS_COMPOSER_ICONS.mic)
                ),
                React.createElement("button", {
                    className: `jarvis-pill-btn jarvis-pill-mute${voiceMuted ? " muted" : ""}`,
                    onClick: toggleMute,
                    title: voiceMuted ? "Unmute voice" : "Mute voice",
                }, voiceMuted ? JARVIS_COMPOSER_ICONS.volumeOff : JARVIS_COMPOSER_ICONS.volumeOn),
                React.createElement("button", {
                    className: "jarvis-pill-btn jarvis-pill-reset",
                    onClick: handleResetMemory,
                    disabled: resetting, title: "Reset memory",
                }, resetting ? JARVIS_COMPOSER_ICONS.loading : JARVIS_COMPOSER_ICONS.reset),
                React.createElement("button", {
                    className: "jarvis-pill-send",
                    onClick: handleSend,
                    disabled: (!displayInput.trim() && pendingAttachments.length === 0) || state === "thinking" || uploadingImage,
                    title: "Send",
                },
                    React.createElement("svg", { viewBox: "0 0 20 20", fill: "currentColor", width: 18, height: 18 },
                        React.createElement("path", { d: "M2.94 17.07L18 10 2.94 2.93l1.06 5.66L13 10l-9 1.41 1.06 5.66z" })
                    )
                )
            )
        )
    );
}

function EyeOfJarvis({ voice, showChatOverlay = true }) {
    const { state, transcript, reply, supported, startListening, stopListening } = voice;
    const showOverlay = showChatOverlay && (transcript || reply || state === "thinking");
    const isActive = state !== "idle";
    const [randomDelay] = React.useState(() => Math.random());

    // Escape key stops mic from anywhere in the app
    React.useEffect(() => {
        const onKey = (e) => { if (e.key === "Escape" && isActive) stopListening(); };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [isActive, stopListening]);

    const handleClick = supported
        ? (isActive ? stopListening : startListening)
        : undefined;
    const isTired = new Date().getHours() < 6;

    return React.createElement(
        React.Fragment, null,
        React.createElement(
            "button", {
            className: `jarvis-eye ${state}${isTired ? ' tired' : ''}`,
            onClick: handleClick,
            style: { '--random-delay': randomDelay },
            title: isActive ? "Stop (or press Esc)" : supported ? "Click or say \"Hey Jarvis\"" : "Speech not supported",
            "aria-label": isActive ? "Stop Jarvis" : "Activate Jarvis",
        },
            React.createElement(JarvisEyeSVG, { state, clipSuffix: "sm", tired: isTired })
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
    settings: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 },
        React.createElement("circle", { cx: 10, cy: 10, r: 7 }),
        React.createElement("path", { d: "M10 5v2M10 13v2M5 10h2M13 10h2M7.8 7.8l1.4 1.4M12.2 12.2l-1.4-1.4M7.8 12.2l1.4-1.4M12.2 7.8l-1.4 1.4" })
    ),
    cc: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("rect", { x: 2, y: 2, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 11, y: 2, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 2, y: 11, width: 7, height: 7, rx: 1 }), React.createElement("rect", { x: 11, y: 11, width: 7, height: 7, rx: 1 })),
    jarvis: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.4 }, React.createElement("polygon", { points: "10,2 1,18 19,18" }), React.createElement("ellipse", { cx: 10, cy: 11, rx: 4, ry: 2.5 }), React.createElement("circle", { cx: 10, cy: 11, r: 1.4, fill: "currentColor" })),
    camera: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("rect", { x: 1, y: 5, width: 18, height: 13, rx: 2 }), React.createElement("circle", { cx: 10, cy: 11.5, r: 3.5 }), React.createElement("path", { d: "M6 5l1.5-3h5L14 5" })),
    globe: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("circle", { cx: 10, cy: 10, r: 8 }), React.createElement("ellipse", { cx: 10, cy: 10, rx: 4, ry: 8 }), React.createElement("line", { x1: 2, y1: 10, x2: 18, y2: 10 })),
    approvals: React.createElement("svg", { viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.5 }, React.createElement("rect", { x: 3, y: 3, width: 14, height: 14, rx: 2 }), React.createElement("polyline", { points: "6,10 9,13 14,7" })),
};

// ── components ────────────────────────────────────────────────────────────────
function Sidebar({ view, onView, voice, collapsed, onOpenSettings, isPhone, phoneOpen, onTogglePhone }) {
    // Sidebar eye: inline SVG emblem, styled for glow and background
    // Sidebar animated eye: use EyeOfJarvis SVG, but with overlay/voice/chatbox logic disabled
    function SidebarAnimatedEye() {
        // Pass a dummy voice object that triggers animation (simulate 'listening' or 'thinking')
        const dummyVoice = {
            state: "thinking", // triggers scanline, color, and all visual effects
            transcript: null,
            reply: null,
            supported: false,
            startListening: () => { },
            stopListening: () => { }
        };
        return React.createElement(
            "div",
            { className: "cc-sidebar-eye-animated" },
            React.createElement(EyeOfJarvis, { voice: dummyVoice, showChatOverlay: false })
        );
    }
    return React.createElement(
        "nav", { className: `cc-sidebar${collapsed ? " collapsed" : ""}${isPhone && phoneOpen ? " phone-open" : ""}` },
        React.createElement("div", { className: "cc-sidebar-logo" }, "JARVIS"),
        React.createElement("div", { className: "cc-sidebar-eye-wrap" },
            React.createElement(SidebarAnimatedEye)
        ),
        React.createElement(
            "ul", { className: "cc-sidebar-nav" },
            ...HUD_VIEWS.map((v, i) =>
                React.createElement(
                    "li", { key: v.id, style: { "--i": i } },
                    React.createElement(
                        "button", {
                        className: `cc-sidebar-item${view === v.id ? " active" : ""}`,
                        onClick: () => {
                            onView(v.id);
                            if (isPhone) onTogglePhone(false);
                        },
                    },
                        React.createElement("span", { className: "cc-sidebar-icon" }, NAV_ICONS[v.id]),
                        React.createElement("span", { className: "cc-sidebar-label" }, v.label)
                    )
                )
            ),
            // Settings sprocket at the bottom
            React.createElement("li", { key: "settings", style: { marginTop: "auto" } },
                React.createElement(
                    "button", {
                    className: "cc-sidebar-item cc-sidebar-settings",
                    onClick: () => {
                        onOpenSettings();
                        if (isPhone) onTogglePhone(false);
                    },
                    title: "Settings",
                },
                    React.createElement("span", { className: "cc-sidebar-icon" }, NAV_ICONS.settings),
                    React.createElement("span", { className: "cc-sidebar-label" }, "Settings")
                )
            )
        )
    );
}
// ── Settings Modal ──────────────────────────────────────────────────────────
function SettingsModal({ open, onClose }) {
    const [rendered, setRendered] = React.useState(open);
    const [closing, setClosing] = React.useState(false);
    const borderDelay = React.useMemo(() => `-${(Math.random() * 3).toFixed(3)}s`, []);

    React.useEffect(() => {
        if (open) {
            setRendered(true);
            setClosing(false);
            return;
        }
        if (!rendered) return;
        setClosing(true);
        const timer = window.setTimeout(() => {
            setRendered(false);
            setClosing(false);
        }, 360);
        return () => window.clearTimeout(timer);
    }, [open, rendered]);

    React.useEffect(() => {
        if (!rendered) return;
        const onKey = (event) => { if (event.key === "Escape") onClose(); };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [rendered, onClose]);

    if (!rendered) return null;

    const modalState = closing ? "closing" : "opening";

    return React.createElement(
        "div",
        {
            className: "cc-modal-backdrop",
            onMouseDown: (event) => {
                if (event.target === event.currentTarget) onClose();
            },
        },
        React.createElement(
            "div",
            {
                className: "cc-modal cc-settings-modal",
                "data-state": modalState,
                style: { "--settings-border-delay": borderDelay },
            },
            React.createElement(
                "div",
                { className: "cc-modal-header" },
                React.createElement("div", { className: "cc-section-title" }, "Settings"),
                React.createElement(
                    "button",
                    { type: "button", className: "cc-modal-close", onClick: onClose, title: "Close" },
                    "x"
                )
            ),
            React.createElement("div", { className: "cc-settings-content", style: { padding: "16px 20px", display: "flex", flexDirection: "column", gap: 24 } },
                React.createElement(SettingsSection, { title: "Appearance" },
                    React.createElement(SettingsRow, { label: "Theme" }, React.createElement(ThemeToggle, null)),
                    React.createElement(SettingsRow, { label: "Tabler skin (beta)" }, React.createElement(TablerSkinToggle, null))
                ),
                React.createElement(SettingsSection, { title: "Voice" },
                    React.createElement(SettingsRow, { label: "Wake phrase" },
                        React.createElement("span", { style: { fontSize: 12, color: "var(--cyan)", fontFamily: "var(--mono)" } }, WAKE_PHRASES.join(" · "))
                    ),
                    React.createElement(SettingsRow, { label: "TTS voice" }, React.createElement(VoiceSelector, null)),
                    React.createElement(SettingsRow, { label: "Agent" }, React.createElement(AgentSelector, null))
                ),
                React.createElement(SettingsSection, { title: "Camera" },
                    React.createElement(SettingsRow, { label: "Default auto-interval" }, React.createElement(CameraIntervalSetting, null))
                ),
                React.createElement(SettingsSection, { title: "About" },
                    React.createElement(SettingsRow, { label: "Version" },
                        React.createElement("span", { style: { fontSize: 12, color: "var(--text2)" } }, "Jarvis HUD — build 2026")
                    )
                )
            )
        )
    );
}

function SettingsSection({ title, children }) {
    return React.createElement("div", null,
        React.createElement("div", { style: { fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", color: "var(--cyan)", marginBottom: 10, textTransform: "uppercase" } }, title),
        React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 10 } }, children)
    );
}

function SettingsRow({ label, children }) {
    return React.createElement("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 } },
        React.createElement("span", { style: { fontSize: 13, color: "var(--text2)" } }, label),
        children
    );
}

function ThemeToggle() {
    const [light, setLight] = React.useState(() => document.body.classList.contains("light"));
    const toggle = () => {
        const next = !light;
        setLight(next);
        document.body.classList.toggle("light", next);
        try { localStorage.setItem("cc:theme", next ? "light" : "dark"); } catch (_) { }
    };
    return React.createElement("button", {
        className: "btn btn-outline-info btn-sm cc-theme-toggle",
        onClick: toggle,
        style: {
            background: light ? "rgba(8,145,178,0.15)" : "rgba(34,211,238,0.1)",
            border: "1px solid var(--cyan)", borderRadius: 20, padding: "4px 14px",
            cursor: "pointer", color: "var(--cyan)", fontSize: 12, fontFamily: "var(--mono)",
            minWidth: 80, textAlign: "center",
        },
    }, light ? "☀ Light" : "☾ Dark");
}

function TablerSkinToggle() {
    const [enabled, setEnabled] = React.useState(() => document.body.classList.contains(TABLER_SKIN_CLASS));
    const toggle = () => {
        const next = !enabled;
        setEnabled(next);
        applyTablerSkin(next);
        try { localStorage.setItem(TABLER_SKIN_KEY, next ? "1" : "0"); } catch (_) { }
    };
    return React.createElement("button", {
        className: `btn btn-sm ${enabled ? "btn-info" : "btn-outline-info"}`,
        onClick: toggle,
        style: {
            minWidth: 110,
            fontFamily: "var(--mono)",
            fontSize: 12,
        },
    }, enabled ? "Enabled" : "Disabled");
}

function VoiceSelector() {
    const [voices, setVoices] = React.useState([]);
    const [selected, setSelected] = React.useState(() => { try { return localStorage.getItem("cc:jarvisVoice") || ""; } catch (_) { return ""; } });
    React.useEffect(() => {
        const load = () => setVoices(window.speechSynthesis ? window.speechSynthesis.getVoices() : []);
        load();
        if (window.speechSynthesis) window.speechSynthesis.addEventListener("voiceschanged", load);
        return () => { if (window.speechSynthesis) window.speechSynthesis.removeEventListener("voiceschanged", load); };
    }, []);
    const onChange = e => {
        setSelected(e.target.value);
        try { localStorage.setItem("cc:jarvisVoice", e.target.value); } catch (_) { }
    };
    if (!voices.length) return React.createElement("span", { style: { fontSize: 12, color: "var(--text3)" } }, "No voices available");
    return React.createElement("select", {
        className: "form-select form-select-sm",
        value: selected, onChange,
        style: { background: "var(--bg2)", color: "var(--text)", border: "1px solid var(--border2)", borderRadius: 6, fontSize: 12, padding: "4px 8px", maxWidth: 220 },
    }, voices.map(v => React.createElement("option", { key: v.name, value: v.name }, v.name)));
}

function AgentWakePhrasesDisplay() {
    const [phrases, setPhrases] = React.useState(() => getWakePhrases());

    React.useEffect(() => {
        const handleStorageChange = () => {
            setPhrases(getWakePhrases());
        };
        window.addEventListener("storage", handleStorageChange);
        // Also update when agent selector changes (same window)
        const interval = setInterval(() => {
            const newPhrases = getWakePhrases();
            if (newPhrases !== phrases) {
                setPhrases(newPhrases);
            }
        }, 500);
        return () => {
            window.removeEventListener("storage", handleStorageChange);
            clearInterval(interval);
        };
    }, [phrases]);

    return React.createElement("span", { style: { fontSize: 12, color: "var(--cyan)", fontFamily: "var(--mono)" } }, phrases.join(" · "));
}

function AgentSelector() {
    const [selected, setSelected] = React.useState(() => {
        try {
            const saved = localStorage.getItem(AGENT_STORAGE_KEY);
            return (saved && AGENTS.find(a => a.id === saved)) ? saved : AGENTS[0].id;
        } catch (_) {
            return AGENTS[0].id;
        }
    });
    const onChange = e => {
        setSelected(e.target.value);
        try { localStorage.setItem(AGENT_STORAGE_KEY, e.target.value); } catch (_) { }
    };
    return React.createElement("select", {
        className: "form-select form-select-sm",
        value: selected, onChange,
        style: { background: "var(--bg2)", color: "var(--text)", border: "1px solid var(--border2)", borderRadius: 6, fontSize: 12, padding: "4px 8px", maxWidth: 220 },
    }, AGENTS.map(agent => React.createElement("option", { key: agent.id, value: agent.id }, `${agent.emoji} ${agent.label}`)));
}

function CameraIntervalSetting() {
    const [val, setVal] = React.useState(() => { try { return localStorage.getItem("cc:camInterval") || "5"; } catch (_) { return "5"; } });
    const onChange = e => {
        setVal(e.target.value);
        try { localStorage.setItem("cc:camInterval", e.target.value); } catch (_) { }
    };
    return React.createElement("select", {
        className: "form-select form-select-sm",
        value: val, onChange,
        style: { background: "var(--bg2)", color: "var(--text)", border: "1px solid var(--border2)", borderRadius: 6, fontSize: 12, padding: "4px 8px" },
    },
        React.createElement("option", { value: "0" }, "Off"),
        React.createElement("option", { value: "3" }, "3 seconds"),
        React.createElement("option", { value: "5" }, "5 seconds"),
        React.createElement("option", { value: "10" }, "10 seconds"),
        React.createElement("option", { value: "30" }, "30 seconds")
    );
}

function TopBar({ now, health, healthState, pending, pendingState, brainStream, onOpenPayment, showSidebarToggle, onToggleSidebar, isSidebarOpen }) {
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
        showSidebarToggle && React.createElement(
            "button",
            {
                type: "button",
                className: "cc-menubar-action cc-menubar-navtoggle",
                onClick: onToggleSidebar,
                title: isSidebarOpen ? "Close navigation menu" : "Open navigation menu",
                "aria-label": isSidebarOpen ? "Close navigation menu" : "Open navigation menu",
                "aria-pressed": isSidebarOpen ? "true" : "false",
            },
            React.createElement(
                "span",
                { className: `cc-navtoggle-icon${isSidebarOpen ? " open" : ""}`, "aria-hidden": "true" },
                React.createElement("span", { className: "cc-navtoggle-line" }),
                React.createElement("span", { className: "cc-navtoggle-line" }),
                React.createElement("span", { className: "cc-navtoggle-line" })
            )
        ),
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
    const [rendered, setRendered] = React.useState(open);
    const [closing, setClosing] = React.useState(false);
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

    const resetForm = React.useCallback(() => {
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
    }, []);

    React.useEffect(() => {
        if (open) {
            setRendered(true);
            setClosing(false);
            return;
        }
        if (!rendered) return;
        setClosing(true);
        const timer = window.setTimeout(() => {
            setRendered(false);
            setClosing(false);
            setBusy(false);
            setStatusText("");
            resetForm();
        }, 360);
        return () => window.clearTimeout(timer);
    }, [open, rendered, resetForm]);

    React.useEffect(() => {
        if (!rendered) return;
        const onKey = (event) => {
            if (event.key === "Escape") onClose();
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [rendered, onClose]);

    const closeModal = () => {
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

    if (!rendered) return null;

    const modalState = closing ? "closing" : "opening";

    return React.createElement(
        "div",
        {
            className: "cc-modal-backdrop",
            "data-state": modalState,
            onMouseDown: (event) => {
                if (event.target === event.currentTarget) closeModal();
            },
        },
        React.createElement(
            "div",
            { className: "cc-modal cc-payment-modal", "data-state": modalState },
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
                React.createElement("input", { className: "cc-pay-input form-control", type: "number", min: "0.01", step: "0.01", value: amount, onChange: e => setAmount(e.target.value), placeholder: "40.00" }),
                React.createElement("label", { className: "cc-pay-label" }, "Currency"),
                React.createElement("input", { className: "cc-pay-input form-control", value: currency, maxLength: 3, onChange: e => setCurrency(e.target.value), placeholder: "USD" }),

                React.createElement("label", { className: "cc-pay-label" }, "Recipient"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide form-control", value: recipient, onChange: e => setRecipient(e.target.value), placeholder: "merchant@example.com" }),

                React.createElement("label", { className: "cc-pay-label" }, "Merchant"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide form-control", value: merchant, onChange: e => setMerchant(e.target.value), placeholder: "Lupa" }),

                React.createElement("label", { className: "cc-pay-label" }, "Reason"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide form-control", value: reason, onChange: e => setReason(e.target.value), placeholder: "Reservation deposit" }),

                React.createElement("label", { className: "cc-pay-label" }, "Cardholder Name"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide form-control", value: cardholder, onChange: e => setCardholder(e.target.value), placeholder: "Nickos" }),

                React.createElement("label", { className: "cc-pay-label" }, "Card Number"),
                React.createElement("input", { className: "cc-pay-input cc-pay-wide form-control", value: cardNumber, onChange: e => setCardNumber(e.target.value), placeholder: "4242 4242 4242 4242", inputMode: "numeric", autoComplete: "cc-number" }),

                React.createElement("label", { className: "cc-pay-label" }, "Exp Month"),
                React.createElement("input", { className: "cc-pay-input form-control", value: expMonth, onChange: e => setExpMonth(e.target.value), placeholder: "12", inputMode: "numeric" }),
                React.createElement("label", { className: "cc-pay-label" }, "Exp Year"),
                React.createElement("input", { className: "cc-pay-input form-control", value: expYear, onChange: e => setExpYear(e.target.value), placeholder: "2028", inputMode: "numeric" }),

                React.createElement("label", { className: "cc-pay-label" }, "Billing ZIP"),
                React.createElement("input", { className: "cc-pay-input form-control", value: billingZip, onChange: e => setBillingZip(e.target.value), placeholder: "10001" }),

                React.createElement("label", { className: "cc-pay-label" }, "Temporary Card"),
                React.createElement(
                    "label",
                    { className: "cc-pay-checkbox" },
                    React.createElement("input", { type: "checkbox", checked: temporaryCard, onChange: e => setTemporaryCard(e.target.checked) }),
                    React.createElement("span", null, temporaryCard ? "Yes" : "No")
                ),

                React.createElement("label", { className: "cc-pay-label" }, temporaryCard ? "CVV (optional)" : "CVV (required)"),
                React.createElement("input", { className: "cc-pay-input form-control", value: cvv, onChange: e => setCvv(e.target.value), placeholder: "123", inputMode: "numeric", autoComplete: "cc-csc" })
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
    const [shiftDelay] = React.useState(() => (0.22 + Math.random() * 0.78).toFixed(3));
    return React.createElement(
        "div", {
        className: "cc-card cc-card-pending cc-approvals-panel",
        "data-accent": n > 0 ? "red" : "green",
        style: { "--random-delay": shiftDelay },
    },
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
                                    React.createElement("stop", { offset: "0%", stopColor: lineColor, stopOpacity: "0.30" }),
                                    React.createElement("stop", { offset: "36%", stopColor: lineColor, stopOpacity: "0.20" }),
                                    React.createElement("stop", { offset: "68%", stopColor: lineColor, stopOpacity: "0.10" }),
                                    React.createElement("stop", { offset: "100%", stopColor: lineColor, stopOpacity: "0.02" })
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

function HealthCard({ health, healthState, pending, brainStream, brainEvents }) {
    const status = health?.status ?? null;
    const aiReady = health?.ai?.ready;
    const chat = health?.chat?.configured;
    const monitors = health?.monitors?.configured ?? 0;
    const stopped = health?.monitors?.stopped;
    const total = health?.event_bus?.total_events ?? 0;
    const unproc = health?.event_bus?.unprocessed_events ?? 0;
    const procPct = total > 0 ? Math.round(((total - unproc) / total) * 100) : 100;
    const pendingCount = Number.isFinite(pending) ? Number(pending) : 0;
    const recentBrainPerMin = Array.isArray(brainEvents)
        ? brainEvents.filter((row) => {
            const ts = Number(row?.ts);
            return Number.isFinite(ts) && ((Date.now() / 1000) - ts) <= 60;
        }).length
        : 0;
    const workloadScore = (
        (pendingCount * 3)
        + Number(unproc || 0)
        + (recentBrainPerMin * 2)
        + (healthState?.stale ? 5 : 0)
        + (brainStream?.status !== "live" ? 3 : 0)
    );
    const workloadLevel = workloadScore >= 20 ? "High" : workloadScore >= 9 ? "Medium" : "Low";
    const workloadColor = workloadLevel === "High"
        ? "var(--red)"
        : workloadLevel === "Medium"
            ? "var(--orange)"
            : "var(--green)";
    const workloadLabel = `${workloadLevel} • Q${pendingCount} U${unproc} E${recentBrainPerMin}/m`;
    const cpuPct = Number(health?.system?.cpu_percent);
    const cpuKnown = Number.isFinite(cpuPct);
    const cpuColor = !cpuKnown ? "var(--text2)" : cpuPct >= 85 ? "var(--red)" : cpuPct >= 65 ? "var(--orange)" : "var(--green)";
    const cpuLabel = cpuKnown ? `${cpuPct.toFixed(0)}%` : "—";

    const memPct = Number(health?.system?.memory_percent);
    const memUsedGb = Number(health?.system?.memory_used_gb);
    const memTotalGb = Number(health?.system?.memory_total_gb);
    const memKnown = Number.isFinite(memPct);
    const memColor = !memKnown ? "var(--text2)" : memPct >= 90 ? "var(--red)" : memPct >= 75 ? "var(--orange)" : "var(--green)";
    const memLabel = (memKnown && Number.isFinite(memUsedGb) && Number.isFinite(memTotalGb))
        ? `${memPct.toFixed(0)}% (${memUsedGb.toFixed(1)}/${memTotalGb.toFixed(1)}G)`
        : (memKnown ? `${memPct.toFixed(0)}%` : "—");

    const gpuPct = Number(health?.system?.gpu?.utilization_percent);
    const gpuKnown = Boolean(health?.system?.gpu?.available) && Number.isFinite(gpuPct);
    const gpuMemUsed = Number(health?.system?.gpu?.memory_used_mb);
    const gpuMemTotal = Number(health?.system?.gpu?.memory_total_mb);
    const gpuMemKnown = Number.isFinite(gpuMemUsed) && Number.isFinite(gpuMemTotal) && gpuMemTotal > 0;
    const gpuColor = !gpuKnown ? "var(--text2)" : gpuPct >= 90 ? "var(--red)" : gpuPct >= 70 ? "var(--orange)" : "var(--green)";
    const gpuLabel = gpuKnown
        ? (gpuMemKnown
            ? `${gpuPct.toFixed(0)}% (${(gpuMemUsed / 1024).toFixed(1)}/${(gpuMemTotal / 1024).toFixed(1)}G)`
            : `${gpuPct.toFixed(0)}%`)
        : (health?.system?.gpu?.available ? "idle" : "n/a");
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
            row("CPU", cpuLabel, cpuColor),
            row("RAM", memLabel, memColor),
            row("GPU", gpuLabel, gpuColor),
            row("Workload", workloadLabel, workloadColor),
            row("Monitors", `${monitors} ${stopped === false ? "▶" : stopped === true ? "■" : ""}`,
                stopped === false ? "var(--green)" : "var(--text2)"),
            row("Feed", healthState?.stale ? "Stale" : (health?.source === "health_cache" ? "Cache" : "Live"),
                healthState?.stale ? "var(--orange)" : "var(--text2)"),
        ),

        React.createElement("div", { className: "cc-progress", style: { marginTop: "auto" } },
            React.createElement("div", {
                className: "cc-progress-fill",
                style: {
                    "--fill-scale": String(Math.max(0, Math.min(1, Number(procPct || 0) / 100))),
                    background: procPct > 90 ? "var(--green)" : "var(--orange)",
                },
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
        React.createElement(
            "div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 } },
            React.createElement("div", { className: "cc-label" }, "Event Bus"),
            unproc > 0 && React.createElement(
                "span",
                { className: "cc-badge cc-badge-event" },
                `+${unproc} new`
            )
        ),
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
                style: {
                    "--bar-scale": String(Math.max(0.07, Math.min(1, Number(h || 0) / 28))),
                    background: "rgba(90,200,245,0.55)",
                },
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
                style: {
                    "--bar-scale": String(Math.max(0.07, Math.min(1, Number(h || 0) / 28))),
                    background: "rgba(48,209,88,0.5)",
                },
            }))
        )
    );
}

function RadarCoreCard({ health, pending, streamStatus, events }) {
    const sweepDelay = React.useMemo(() => `-${(Math.random() * 8).toFixed(3)}s`, []);

    const eventBacklog = Number(health?.event_bus?.unprocessed_events || 0);
    const pendingCount = Number(pending || 0);
    const recentEvents = Array.isArray(events) ? events.length : 0;
    const reconnecting = streamStatus === "connecting" || streamStatus === "reconnecting";

    const activityScore = Math.max(
        1,
        Math.min(
            12,
            1 +
            (pendingCount * 2) +
            (eventBacklog * 0.6) +
            (recentEvents * 0.4) +
            (reconnecting ? 3 : 0)
        )
    );

    const sweepDuration = Math.max(2.2, 8.4 - (activityScore * 0.42));
    const pulseDuration = Math.max(1.2, 3.2 - (activityScore * 0.14));
    const flickerDuration = Math.max(2.0, 7.6 - (activityScore * 0.26));
    const alertLevel = activityScore >= 8 ? "high" : activityScore >= 5 ? "medium" : "low";
    const alertText = alertLevel === "high" ? "ELEVATED" : alertLevel === "medium" ? "ACTIVE" : "STABLE";

    return React.createElement(
        "div", { className: "cc-card cc-core", "data-accent": "cyan" },
        React.createElement("div", { className: "cc-label" }, "Radar Core"),
        React.createElement(
            "div",
            {
                style: {
                    height: 120,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginTop: 4,
                },
            },
            React.createElement(
                "svg",
                {
                    className: "cc-crosshair",
                    viewBox: "0 0 100 100",
                    width: 108,
                    height: 108,
                    style: {
                        "--radar-sweep-delay": sweepDelay,
                        "--radar-sweep-duration": `${sweepDuration.toFixed(2)}s`,
                        "--radar-pulse-duration": `${pulseDuration.toFixed(2)}s`,
                        "--radar-flicker-duration": `${flickerDuration.toFixed(2)}s`,
                    },
                    "data-alert": alertLevel,
                    role: "img",
                    "aria-label": "Animated radar crosshair",
                },
                React.createElement("circle", {
                    cx: 50,
                    cy: 50,
                    r: 34,
                    fill: "none",
                    stroke: "rgba(34, 211, 238, 0.38)",
                    strokeWidth: 0.9,
                }),
                React.createElement("line", {
                    className: "cc-crosshair-line",
                    x1: 50,
                    y1: 10,
                    x2: 50,
                    y2: 90,
                    stroke: "rgba(34, 211, 238, 0.75)",
                    strokeWidth: 1,
                    strokeLinecap: "round",
                }),
                React.createElement("line", {
                    className: "cc-crosshair-line",
                    x1: 10,
                    y1: 50,
                    x2: 90,
                    y2: 50,
                    stroke: "rgba(34, 211, 238, 0.75)",
                    strokeWidth: 1,
                    strokeLinecap: "round",
                }),
                React.createElement("circle", { className: "cc-crosshair-center", cx: 50, cy: 50, r: 2.3 })
            )
        ),
        React.createElement(
            "div",
            { className: "cc-core-meta" },
            React.createElement("span", { className: `cc-badge ${alertLevel === "high" ? "orange" : alertLevel === "medium" ? "cyan" : "green"}` }, alertText),
            React.createElement("span", { className: "cc-watch-meta-item" }, `pending ${pendingCount}`),
            React.createElement("span", { className: "cc-watch-meta-item" }, `queue ${eventBacklog}`)
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
    const device = useDeviceProfile();
    const isPhone = device === "phone";
    const healthState = useHealth();
    const pendingState = usePending();
    const health = healthState.data;
    const pending = pendingState.count;
    const brainStream = useBrainStream();
    const brainEvents = brainStream.events;
    const voice = useVoice(device);
    const [phoneSidebarOpen, setPhoneSidebarOpen] = React.useState(false);
    const [paymentOpen, setPaymentOpen] = React.useState(false);
    const [settingsOpen, setSettingsOpen] = React.useState(false);
    const [view, setView] = React.useState(() => {
        try {
            const saved = localStorage.getItem("cc:lastView");
            if (saved && HUD_VIEWS.some(v => v.id === saved)) return saved;
        } catch (_) { }
        return "jarvis";
    });

    // Initialize randomized session color palette once on app mount
    React.useEffect(() => {
        initSessionColorPalette();
    }, []);

    React.useEffect(() => {
        let enabled = false;
        try {
            enabled = localStorage.getItem(TABLER_SKIN_KEY) === "1";
        } catch (_) { }
        applyTablerSkin(enabled);
    }, []);

    // Stop speech when navigating away from Jarvis tab
    React.useEffect(() => {
        if (view !== "jarvis") voice.stopListening();
    }, [view]); // eslint-disable-line react-hooks/exhaustive-deps

    React.useEffect(() => {
        try { localStorage.setItem("cc:lastView", view); } catch (_) { }
    }, [view]);

    React.useEffect(() => {
        document.body.dataset.device = device;
        return () => {
            delete document.body.dataset.device;
        };
    }, [device]);

    React.useEffect(() => {
        if (!isPhone) {
            setPhoneSidebarOpen(false);
        }
    }, [isPhone]);

    const [coinMeta, setCoinMeta] = React.useState({ id: "bitcoin", name: "Bitcoin", symbol: "btc" });
    const { price, delta, loading: assetLoading, flash: assetFlash } = useAssetPrice(coinMeta.id, coinMeta.symbol);
    const displayAsset = price !== null ? { name: coinMeta.name, symbol: coinMeta.symbol, price, delta } : null;

    const openMarkets = React.useMemo(
        () => MARKETS.filter(m => marketStatus(m, now).open).length,
        [Math.floor(now.getTime() / 60000)]
    );

    const iframeStyle = device === "phone"
        ? {
            position: "fixed", top: 40, left: 72, right: 0, bottom: 24,
            width: "calc(100% - 72px)", height: "calc(100vh - 64px)",
            border: "none", zIndex: 1,
        }
        : {
            position: "fixed", top: 40, left: 168, right: 0, bottom: 24,
            width: "calc(100% - 168px)", height: "calc(100vh - 64px)",
            border: "none", zIndex: 1,
        };

    return React.createElement(
        React.Fragment, null,
        React.createElement(TopBar, {
            now, health, healthState, pending, pendingState, brainStream,
            onOpenPayment: () => setPaymentOpen(true),
            showSidebarToggle: isPhone,
            onToggleSidebar: () => setPhoneSidebarOpen(v => !v),
            isSidebarOpen: phoneSidebarOpen,
        }),
        React.createElement(Sidebar, {
            view,
            onView: setView,
            voice,
            collapsed: isPhone ? !phoneSidebarOpen : (view === "jarvis" && device === "desktop"),
            onOpenSettings: () => setSettingsOpen(true),
            isPhone,
            phoneOpen: phoneSidebarOpen,
            onTogglePhone: setPhoneSidebarOpen,
        }),
        React.createElement(ChromeBottom, { health, pending, btcPrice: price ?? 0, openMarkets, brainEvents }),
        React.createElement(PaymentRequestModal, {
            open: paymentOpen,
            onClose: () => setPaymentOpen(false),
            onQueued: () => {
                setPaymentOpen(false);
            },
        }),
        React.createElement(SettingsModal, { open: settingsOpen, onClose: () => setSettingsOpen(false) }),
        view === "jarvis" && React.createElement(JarvisTab, { voice, onOpenCamera: () => setView("camera") }),
        view === "camera" && React.createElement(CameraTab, {
            onSendToJarvis: (text) => {
                setView("jarvis");
                voice.ask(text);
            },
        }),
        view === "globe" && React.createElement("iframe", { src: "/hud/globe", style: iframeStyle, title: "Strategic Globe" }),
        view === "approvals" && React.createElement("iframe", { src: "/", style: iframeStyle, title: "Approvals" }),
        view === "cc" && React.createElement(
            "div", { className: `cc-body cc-body-${device}` },
            React.createElement(ClockCard, { now }),
            React.createElement(AssetStatCard, { asset: displayAsset, loading: assetLoading, flash: assetFlash }),
            React.createElement(PendingCard, { pending }),
            React.createElement(WatchlistCard, { health, pending, pendingState, openMarkets, onSelectAsset: setCoinMeta }),
            React.createElement(NewsCard),
            React.createElement(DatasetsCard),
            React.createElement(AssetChartCard, { coinMeta, onSelect: setCoinMeta, price, delta, loading: assetLoading }),
            React.createElement(BrainActivityCard, { events: brainEvents, streamStatus: brainStream.status }),
            React.createElement(HealthCard, {
                health,
                healthState,
                pending,
                brainStream,
                brainEvents,
            }),
            React.createElement(RadarCoreCard, { health, pending, streamStatus: brainStream.status, events: brainEvents }),
            React.createElement(RuntimeControlCard, { health }),
            React.createElement(MonitorsCard, { health })
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) createRoot(rootEl).render(React.createElement(App));
