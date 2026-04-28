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

// ── hooks ─────────────────────────────────────────────────────────────────────

function useClock() {
    const [now, setNow] = React.useState(() => new Date());
    React.useEffect(() => {
        const t = setInterval(() => setNow(new Date()), 1000);
        return () => clearInterval(t);
    }, []);
    return now;
}

function useHealth() {
    const [data, setData] = React.useState(null);
    React.useEffect(() => {
        let dead = false;
        const go = async () => {
            try { const r = await fetch("/health"); if (!dead && r.ok) setData(await r.json()); }
            catch (_) { }
        };
        go();
        const t = setInterval(go, 8000);
        return () => { dead = true; clearInterval(t); };
    }, []);
    return data;
}

function usePending() {
    const [n, setN] = React.useState(null);
    React.useEffect(() => {
        let dead = false;
        const go = async () => {
            try {
                const r = await fetch("/approvals/pending?limit=100");
                if (!dead && r.ok) { const j = await r.json(); setN(Array.isArray(j.items) ? j.items.length : 0); }
            } catch (_) { }
        };
        go();
        const t = setInterval(go, 8000);
        return () => { dead = true; clearInterval(t); };
    }, []);
    return n;
}

// ── market data sources ───────────────────────────────────────────────────────
const CG      = "https://api.coingecko.com/api/v3";
const BINANCE = "https://api.binance.com/api/v3";
const METALS  = "https://metals.live/api/v1/spot";

// commodity metal assets — use metals.live, not Binance
const COMMODITY_META = {
    "commodity-gold":     { metalKey: "gold",     name: "Gold",     symbol: "XAU", unit: "US$/oz" },
    "commodity-silver":   { metalKey: "silver",   name: "Silver",   symbol: "XAG", unit: "US$/oz" },
    "commodity-platinum": { metalKey: "platinum", name: "Platinum", symbol: "XPT", unit: "US$/oz" },
    "commodity-palladium":{ metalKey: "palladium",name: "Palladium",symbol: "XPD", unit: "US$/oz" },
};
const COMMODITY_IDS = new Set(Object.keys(COMMODITY_META));

const WINDOWS = [
    { label: "LIVE", mode: "live" },
    { label: "1m",   mode: "binance", interval: "1m",  limit: 120 },
    { label: "5m",   mode: "binance", interval: "5m",  limit: 120 },
    { label: "15m",  mode: "binance", interval: "15m", limit: 96  },
    { label: "1h",   mode: "binance", interval: "1h",  limit: 72  },
    { label: "4h",   mode: "binance", interval: "4h",  limit: 84  },
    { label: "1D",   mode: "binance", interval: "1d",  limit: 90  },
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
function fetchMetals() {
    const now = Date.now();
    if (_metalsCache && now - _metalsCacheTs < 55000) return Promise.resolve(_metalsCache);
    if (_metalsPromise) return _metalsPromise;
    _metalsPromise = fetch(METALS)
        .then(r => r.json())
        .then(j => {
            const data = Array.isArray(j) ? j[0] : j;
            _metalsCache = data; _metalsCacheTs = Date.now(); _metalsPromise = null;
            return data;
        })
        .catch(() => { _metalsPromise = null; return _metalsCache ?? {}; });
    return _metalsPromise;
}

// price hook — branches on commodity vs crypto
function useAssetPrice(coinId, coinSymbol) {
    const [price, setPrice]     = React.useState(null);
    const [delta, setDelta]     = React.useState(0);
    const [loading, setLoading] = React.useState(true);
    const [flash, setFlash]     = React.useState(null);
    const prevRef = React.useRef(null);

    React.useEffect(() => {
        if (!coinId || !coinSymbol) return;
        setPrice(null); setDelta(0); setLoading(true); prevRef.current = null;
        let dead = false;

        if (COMMODITY_IDS.has(coinId)) {
            const meta = COMMODITY_META[coinId];
            const poll = async () => {
                try {
                    const data = await fetchMetals();
                    const p = parseFloat(data[meta.metalKey]);
                    if (isNaN(p) || dead) return;
                    if (prevRef.current !== null && p !== prevRef.current) {
                        setFlash(p > prevRef.current ? "up" : "down");
                        setTimeout(() => setFlash(null), 800);
                    }
                    prevRef.current = p;
                    const ticks = _liveTicks.get(coinId) ?? [];
                    ticks.push(p); if (ticks.length > 300) ticks.shift();
                    _liveTicks.set(coinId, ticks);
                    if (!dead) { setPrice(p); setDelta(0); setLoading(false); }
                } catch (_) { if (!dead) setLoading(false); }
            };
            poll();
            const t = setInterval(poll, 60000);
            return () => { dead = true; clearInterval(t); };
        }

        // crypto via Binance
        const sym = binanceSymbol(coinSymbol);
        const poll = async () => {
            try {
                const r = await fetch(`${BINANCE}/ticker/24hr?symbol=${sym}`);
                if (!r.ok || dead) return;
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
                if (!dead) { setPrice(p); setDelta(d); setLoading(false); }
            } catch (_) { if (!dead) setLoading(false); }
        };
        poll();
        const t = setInterval(poll, 10000);
        return () => { dead = true; clearInterval(t); };
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
            } catch (_) {}
        };

        load();
        const t = setInterval(load, win.mode === "live" ? 20000 : 60000);
        return () => { dead = true; clearInterval(t); };
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
    const seenRef = React.useRef(new Set());

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
                    setLoading(false);

                    // clear "new" highlights after 6s
                    if (fresh.size) setTimeout(() => setNewIds(new Set()), 6000);
                }
            } catch (_) {
                if (!dead) setLoading(false);
            }
        };

        load();
        const t = setInterval(load, 90 * 1000);
        return () => { dead = true; clearInterval(t); };
    }, [subreddit]);

    return { items, newIds, loading, lastAt };
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
    const preview = item.preview?.images?.[0]?.source?.url?.replaceAll("&amp;", "&");
    const url = preview || (item.thumbnail?.startsWith("http") ? item.thumbnail : null);
    // fall back to Google favicon for text posts
    const domain = item.domain?.replace(/^self\./, "") || "reddit.com";
    const final = url || `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
    _thumbCache.set(item.id, final);
    return final;
}

function NewsCard() {
    const [srcIdx, setSrcIdx] = React.useState(0);
    const { items, newIds, loading } = useNews(NEWS_SOURCES[srcIdx].sub);

    return React.createElement(
        "div", { className: "cc-card cc-card-news", "data-accent": "purple" },

        React.createElement(
            "div", { className: "cc-news-header" },
            React.createElement(
                "div", { style: { display: "flex", alignItems: "center", gap: 8 } },
                React.createElement("div", { className: "cc-section-title" }, "News Feed"),
                React.createElement("span", { className: "cc-live-dot" })
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
                            React.createElement("img", {
                                className: "cc-news-thumb",
                                src: thumb,
                                alt: "",
                                loading: "lazy",
                                referrerPolicy: "no-referrer",
                                onError: e => {
                                    const domain = item.domain?.replace(/^self\./, "") || "reddit.com";
                                    const fallback = `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
                                    if (e.target.src !== fallback) {
                                        e.target.src = fallback;
                                        e.target.style.objectFit = "contain";
                                        e.target.style.padding = "8px";
                                    }
                                },
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
    { id: "commodity-gold",     name: "Gold",     symbol: "XAU", market_cap_rank: 0 },
    { id: "commodity-silver",   name: "Silver",   symbol: "XAG", market_cap_rank: 0 },
    { id: "commodity-platinum", name: "Platinum", symbol: "XPT", market_cap_rank: 0 },
    { id: "commodity-palladium",name: "Palladium",symbol: "XPD", market_cap_rank: 0 },
    { id: "bitcoin",       name: "Bitcoin",       symbol: "btc",  market_cap_rank: 1  },
    { id: "ethereum",      name: "Ethereum",      symbol: "eth",  market_cap_rank: 2  },
    { id: "tether",        name: "Tether",        symbol: "usdt", market_cap_rank: 3  },
    { id: "binancecoin",   name: "BNB",           symbol: "bnb",  market_cap_rank: 4  },
    { id: "solana",        name: "Solana",        symbol: "sol",  market_cap_rank: 5  },
    { id: "ripple",        name: "XRP",           symbol: "xrp",  market_cap_rank: 6  },
    { id: "usd-coin",      name: "USD Coin",      symbol: "usdc", market_cap_rank: 7  },
    { id: "cardano",       name: "Cardano",       symbol: "ada",  market_cap_rank: 8  },
    { id: "avalanche-2",   name: "Avalanche",     symbol: "avax", market_cap_rank: 9  },
    { id: "dogecoin",      name: "Dogecoin",      symbol: "doge", market_cap_rank: 10 },
    { id: "polkadot",      name: "Polkadot",      symbol: "dot",  market_cap_rank: 11 },
    { id: "chainlink",     name: "Chainlink",     symbol: "link", market_cap_rank: 12 },
    { id: "matic-network", name: "Polygon",       symbol: "matic",market_cap_rank: 13 },
    { id: "litecoin",      name: "Litecoin",      symbol: "ltc",  market_cap_rank: 14 },
    { id: "pax-gold",      name: "PAX Gold",      symbol: "paxg", market_cap_rank: 50 },
    { id: "tether-gold",   name: "Tether Gold",   symbol: "xaut", market_cap_rank: 55 },
    { id: "shiba-inu",     name: "Shiba Inu",     symbol: "shib", market_cap_rank: 15 },
    { id: "tron",          name: "TRON",          symbol: "trx",  market_cap_rank: 16 },
    { id: "near",          name: "NEAR Protocol", symbol: "near", market_cap_rank: 17 },
    { id: "stellar",       name: "Stellar",       symbol: "xlm",  market_cap_rank: 18 },
];

let _marketList = null;
let _marketListTs = 0;
let _marketListPromise = null;

function getMarketList() {
    const now = Date.now();
    if (_marketList && now - _marketListTs < 3600000) return Promise.resolve(_marketList);
    if (_marketListPromise) return _marketListPromise;
    _marketListPromise = new Promise(res => setTimeout(res, 2000))
        .then(() => Promise.all([
            fetch(`${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&sparkline=false`),
            fetch(`${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=2&sparkline=false`),
        ]))
        .then(async ([r1, r2]) => {
            const [p1, p2] = await Promise.all([r1.json(), r2.json()]);
            return [...(Array.isArray(p1) ? p1 : []), ...(Array.isArray(p2) ? p2 : [])];
        })
        .then(j => { _marketList = j; _marketListTs = Date.now(); _marketListPromise = null; return j; })
        .catch(() => {
            _marketListPromise = null;
            setTimeout(() => { if (!_marketList) getMarketList(); }, 30000);
            return _marketList ?? FALLBACK_COINS;
        });
    return _marketListPromise;
}

function searchCoins(list, q) {
    const aliases = KEYWORD_ALIASES[q] ?? [];
    const boost   = new Set(aliases);
    const score = c => {
        const sym  = c.symbol.toLowerCase();
        const name = c.name.toLowerCase();
        if (sym === q || boost.has(sym) || boost.has(c.id)) return 0;
        if (sym.startsWith(q) || name.startsWith(q))        return 1;
        if (sym.includes(q)   || name.includes(q))          return 2;
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
    const [results, setResults]     = React.useState([]);
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
    { id: "bitcoin",       name: "Bitcoin",  symbol: "btc" },
    { id: "ethereum",      name: "Ethereum", symbol: "eth" },
    { id: "commodity-gold",name: "Gold",     symbol: "XAU" },
];

function useWatchlist() {
    const [list, setList] = React.useState(() => {
        try { return JSON.parse(localStorage.getItem(WATCHLIST_KEY)) || DEFAULT_WATCHLIST; }
        catch (_) { return DEFAULT_WATCHLIST; }
    });
    const save = items => { setList(items); localStorage.setItem(WATCHLIST_KEY, JSON.stringify(items)); };
    const add    = coin => { if (!list.find(c => c.id === coin.id)) save([...list, { id: coin.id, name: coin.name, symbol: coin.symbol }]); };
    const remove = id   => save(list.filter(c => c.id !== id));
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

function WatchlistCard({ health, pending, openMarkets, onSelectAsset }) {
    const { list, add, remove } = useWatchlist();
    const [addOpen, setAddOpen] = React.useState(false);
    const [query, setQuery]     = React.useState("");
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

// ── components ────────────────────────────────────────────────────────────────
function MenuBar({ now, health, pending }) {
    const status = health?.status ?? "unknown";
    const monitors = health?.monitors?.configured ?? 0;
    return React.createElement(
        "header", { className: "cc-menubar" },
        React.createElement("span", { className: "cc-menubar-title" }, "Jarvis — Command Center"),
        React.createElement(
            "div", { className: "cc-menubar-items" },
            React.createElement("span", { className: "cc-menubar-item" }, `${monitors} monitors`),
            pending !== null && React.createElement("span", { className: "cc-menubar-item" },
                pending > 0 ? `${pending} pending` : "queue clear"
            ),
            React.createElement(
                "span", { className: `cc-status-pill ${status}` },
                React.createElement("span", { className: `cc-status-dot ${status}` }),
                status === "ok" ? "Online" : status === "degraded" ? "Degraded" : "Unknown"
            ),
            React.createElement("span", { className: "cc-menubar-clock" }, `${fmtTime(now)} ${localTZName()}`),
            React.createElement(
                "div", { className: "cc-nav-chips" },
                React.createElement("a", { className: "cc-nav-chip", href: "/" }, "Approvals"),
                React.createElement("a", { className: "cc-nav-chip", href: "/hud/react" }, "HUD React")
            )
        )
    );
}

function ClockCard({ now }) {
    const tz = localTZName();
    return React.createElement(
        "div", { className: "cc-card cc-card-clock", "data-accent": "cyan" },
        React.createElement("div", { className: "cc-label" }, tz || "Local Time"),
        React.createElement("div", { className: "cc-clock-time" }, fmtTime(now)),
        React.createElement("div", { className: "cc-clock-date" }, fmtDate(now)),
        React.createElement("div", { className: "cc-clock-local" }, `UTC ${fmtUTC(now)}`)
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

    React.useEffect(() => {
        if (typeof serverStopped === "boolean") {
            setLocalStopped(serverStopped);
        }
    }, [serverStopped]);

    const isStopped = localStopped === null ? serverStopped === true : localStopped;

    const callRuntimeAction = async (action) => {
        if (busy) return;
        setBusy(action);
        setStatusText(action === "stop" ? "Stopping Jarvis..." : "Starting Jarvis...");
        try {
            const res = await fetch(`/runtime/${action}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: "{}",
            });
            const payload = await res.json();
            if (!res.ok) throw new Error(payload?.error || `HTTP ${res.status}`);
            const stoppedNow = payload?.status === "stopped";
            setLocalStopped(stoppedNow);
            setStatusText(stoppedNow ? "Jarvis is stopped." : "Jarvis is running.");
        } catch (_err) {
            setStatusText("Action failed. Check server connection.");
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
            React.createElement("span", { className: "cc-runtime-text" }, isStopped ? "Stopped" : "Running")
        ),
        React.createElement(
            "div", { className: "cc-runtime-actions" },
            React.createElement(
                "button",
                {
                    type: "button",
                    className: "cc-runtime-btn start",
                    onClick: () => callRuntimeAction("resume"),
                    disabled: busy.length > 0 || !isStopped,
                },
                busy === "resume" ? "Starting..." : "Start"
            ),
            React.createElement(
                "button",
                {
                    type: "button",
                    className: "cc-runtime-btn stop",
                    onClick: () => callRuntimeAction("stop"),
                    disabled: busy.length > 0 || isStopped,
                },
                busy === "stop" ? "Stopping..." : "Stop"
            )
        ),
        React.createElement(
            "div",
            { className: "cc-runtime-hint" },
            statusText || "Use Start/Stop to control monitor execution."
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

function HealthCard({ health }) {
    const status  = health?.status ?? null;
    const aiReady = health?.ai?.ready;
    const chat    = health?.chat?.configured;
    const monitors = health?.monitors?.configured ?? 0;
    const stopped  = health?.monitors?.stopped;
    const total   = health?.event_bus?.total_events ?? 0;
    const unproc  = health?.event_bus?.unprocessed_events ?? 0;
    const procPct = total > 0 ? Math.round(((total - unproc) / total) * 100) : 100;
    const accent  = status === "ok" ? "green" : status === "degraded" ? "red" : "cyan";

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
                    style: { fontFamily: "var(--mono)", fontSize: 12, fontWeight: 500,
                        color: status === "ok" ? "var(--green)" : status === "degraded" ? "var(--red)" : "var(--text2)" }
                }, status ? status.toUpperCase() : "CONNECTING…")
            ),

            row("AI",      aiReady === true ? "Ready" : aiReady === false ? "Not ready" : "—",
                           aiReady === true ? "var(--green)" : aiReady === false ? "var(--red)" : "var(--text2)"),
            row("Chat",    chat === true ? "On" : chat === false ? "Off" : "—",
                           chat === true ? "var(--green)" : "var(--text2)"),
            row("Monitors", `${monitors} ${stopped === false ? "▶" : stopped === true ? "■" : ""}`,
                           stopped === false ? "var(--green)" : "var(--text2)"),
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
function ChromeBottom({ health, pending, btcPrice, openMarkets }) {
    const monitors = health?.monitors?.configured ?? "—";
    const events = health?.event_bus?.total_events ?? "—";
    const unproc = health?.event_bus?.unprocessed_events ?? "—";
    const text =
        `[+]  SYSTEM: ${(health?.status ?? "STANDBY").toUpperCase()}  •  MONITORS: ${monitors}  •  ` +
        `EVENTS: ${events}  •  UNPROCESSED: ${unproc}  •  PENDING: ${pending ?? "—"}  •  ` +
        `MARKETS OPEN: ${openMarkets} / ${MARKETS.length}  •  ASSET: ${fmtPrice(btcPrice)}  •  ` +
        `NODE MESH ONLINE  •  JARVIS COMMAND CENTER  •  FEEDS CONNECTED  •  HOLD STEADY  •  ` +
        `[+]  SYSTEM: ${(health?.status ?? "STANDBY").toUpperCase()}  •  MONITORS: ${monitors}  •  ` +
        `EVENTS: ${events}  •  UNPROCESSED: ${unproc}  •  PENDING: ${pending ?? "—"}  •  ` +
        `MARKETS OPEN: ${openMarkets} / ${MARKETS.length}  •  ASSET: ${fmtPrice(btcPrice)}  •  ` +
        `NODE MESH ONLINE  •  JARVIS COMMAND CENTER  •  FEEDS CONNECTED  •  HOLD STEADY  •  `;
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
    const health = useHealth();
    const pending = usePending();
    const [coinMeta, setCoinMeta] = React.useState({ id: "bitcoin", name: "Bitcoin", symbol: "btc" });
    const { price, delta, loading: assetLoading, flash: assetFlash } = useAssetPrice(coinMeta.id, coinMeta.symbol);
    const displayAsset = price !== null ? { name: coinMeta.name, symbol: coinMeta.symbol, price, delta } : null;

    const openMarkets = React.useMemo(
        () => MARKETS.filter(m => marketStatus(m, now).open).length,
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [Math.floor(now.getTime() / 60000)]
    );

    return React.createElement(
        React.Fragment, null,
        React.createElement(MenuBar, { now, health, pending }),
        React.createElement(ChromeBottom, { health, pending, btcPrice: price ?? 0, openMarkets }),
        React.createElement(
            "div", { className: "cc-body" },
            React.createElement(ClockCard, { now }),
            React.createElement(AssetStatCard, { asset: displayAsset, loading: assetLoading, flash: assetFlash }),
            React.createElement(WatchlistCard, { health, pending, openMarkets, onSelectAsset: setCoinMeta }),
            React.createElement(NewsCard),
            React.createElement(AssetChartCard, { coinMeta, onSelect: setCoinMeta, price, delta, loading: assetLoading }),
            React.createElement(HealthCard, { health }),
            React.createElement(RuntimeControlCard, { health }),
            React.createElement(MonitorsCard, { health })
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) createRoot(rootEl).render(React.createElement(App));
