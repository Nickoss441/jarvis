// --- LIVE AIRCRAFT DATA HOOK ---
function useLiveAircraftData(pollMs = 10000) {
    const [aircraft, setAircraft] = React.useState([]);
    React.useEffect(() => {
        let cancelled = false;
        let timer = null;
        async function fetchAircraft() {
            try {
                const res = await fetch("/hud/air/states", { cache: "no-store" });
                if (!res.ok) throw new Error("aircraft status " + res.status);
                const data = await res.json();
                if (!cancelled) setAircraft(Array.isArray(data.aircraft) ? data.aircraft : []);
            } catch (e) {
                if (!cancelled) setAircraft([]);
            }
        }
        fetchAircraft();
        timer = setInterval(fetchAircraft, pollMs);
        return () => { cancelled = true; if (timer) clearInterval(timer); };
    }, [pollMs]);
    return aircraft;
}
import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import * as THREE from "https://esm.sh/three@0.167.1";
import ThreeGlobe from "https://esm.sh/three-globe@2.31.0?deps=three@0.167.1";

const GLOBE_MARKERS = [
    {
        id: "hormuz",
        label: "Strait of Hormuz",
        lat: 25.578,
        lon: 56.610,
        country: "Oman",
        color: 0x68c6ff,
        region: "Financial relay",
        threat: "Nominal",
        status: "Cross-checking macro liquidity, container flow, and trade-finance sentiment.",
        agents: 6,
        confidence: "94%",
        priority: "P3",
        window: "03m",
        feeds: ["FX", "Container index", "BTC basis", "Macro pulse"],
        protocols: ["Liquidity watch", "Risk rebalance", "Asia handoff"],
    },
    {
        id: "kabul",
        label: "Kabul",
        lat: 34.5553,
        lon: 69.2075,
        country: "Afghanistan",
        color: 0xff8aa8,
        region: "Regional stability watch",
        threat: "Elevated",
        status: "Monitoring cross-border headlines, aid corridors, and logistics resilience signals.",
        agents: 5,
        confidence: "89%",
        priority: "P2",
        window: "05m",
        feeds: ["Regional news", "Aid flow", "Border alerts", "Policy watch"],
        protocols: ["Humanitarian pulse", "Scenario planning", "Desk escalation"],
    },
    {
        id: "djibouti",
        label: "Djibouti",
        lat: 11.5721,
        lon: 43.1456,
        country: "Djibouti",
        color: 0x7cf7c1,
        region: "Maritime chokepoint relay",
        threat: "Guarded",
        status: "Tracking Bab el-Mandeb vessel flow, port congestion, and reroute pressure.",
        agents: 4,
        confidence: "91%",
        priority: "P2",
        window: "04m",
        feeds: ["AIS summary", "Port queues", "Freight rates", "Weather"],
        protocols: ["Shipping watch", "Latency hedge", "Route balancing"],
    },
    {
        id: "singapore",
        label: "Singapore",
        lat: 1.3521,
        lon: 103.8198,
        country: "Singapore",
        color: 0xffd27d,
        region: "Asia market gateway",
        threat: "Nominal",
        status: "Watching SGX-open liquidity, container velocity, and APAC session handoff risk.",
        agents: 7,
        confidence: "96%",
        priority: "P3",
        window: "02m",
        feeds: ["SGX", "Freight index", "FX Asia", "Energy spreads"],
        protocols: ["Asia handoff", "Volatility damp", "Liquidity rebalance"],
    },
];

const GLOBE_CONNECTIONS = [
    ["hormuz", "djibouti"],
    ["hormuz", "singapore"],
    ["kabul", "djibouti"],
    ["kabul", "singapore"],
];

const MARKER_COLOR_REFRESH_MS = 1600;

const SHIPPING_LANES = [
    {
        id: "asia-europe",
        label: "Asia-Europe",
        category: "Maritime Trade Route",
        color: 0x8ed8ff,
        speed: 0.018,
        cargo: "Containers, consumer goods, machinery",
        metric: "Suez carries about 12% of global trade and roughly 30% of container traffic",
        eta: "Singapore to Rotterdam: about 24-30 days",
        chokepoints: ["Malacca", "Bab el-Mandeb", "Suez"],
        waypoints: [
            { lat: 1.29, lon: 103.85 },      // Singapore
            { lat: 2.5, lon: 101.5 },        // Strait of Malacca
            { lat: 7.0, lon: 92.8 },         // Malacca exit to Indian Ocean
            { lat: 12.8, lon: 43.3 },        // Bab el-Mandeb (Red Sea entrance)
            { lat: 29.9, lon: 32.5 },        // Suez Canal
            { lat: 34.5, lon: 25.0 },        // Eastern Mediterranean
            { lat: 40.0, lon: 15.0 },        // Central Mediterranean
            { lat: 51.95, lon: 4.14 },       // Rotterdam
        ],
    },
    {
        id: "gulf-asia",
        label: "Gulf-Asia",
        category: "Energy Route",
        color: 0xffd27d,
        speed: 0.024,
        cargo: "Crude oil, refined products, LNG",
        metric: "Strait of Hormuz moves about 20 million barrels per day of petroleum liquids",
        eta: "Gulf to Singapore tanker run: about 9-14 days",
        chokepoints: ["Hormuz", "Arabian Sea", "Malacca"],
        waypoints: [
            { lat: 26.0, lon: 56.5 },        // Strait of Hormuz
            { lat: 20.0, lon: 64.0 },        // Gulf of Oman
            { lat: 13.0, lon: 55.0 },        // Arabian Sea
            { lat: 8.0, lon: 72.0 },         // Indian Ocean
            { lat: 4.0, lon: 78.0 },         // Western coast of India
            { lat: 2.5, lon: 101.5 },        // Strait of Malacca
            { lat: 1.29, lon: 103.85 },      // Singapore
        ],
    },
    {
        id: "panama",
        label: "Panama Canal",
        category: "Interoceanic Route",
        color: 0x7df0ba,
        speed: 0.016,
        cargo: "Containers, grain, LPG, vehicle carriers",
        metric: "Panama is the Atlantic-Pacific shortcut for US East Coast and Gulf services",
        eta: "Shanghai to New York via Panama: about 25-35 days",
        chokepoints: ["Panama Canal"],
        waypoints: [
            { lat: 31.23, lon: 121.47 },     // Shanghai
            { lat: 30.0, lon: 140.0 },       // NW Pacific
            { lat: 28.0, lon: 160.0 },       // North Pacific west
            { lat: 25.0, lon: 179.0 },       // Dateline west
            { lat: 22.0, lon: -170.0 },      // Dateline east
            { lat: 18.0, lon: -150.0 },      // Central Pacific
            { lat: 15.0, lon: -130.0 },      // Eastern Pacific
            { lat: 12.0, lon: -100.0 },      // Panama approach
            { lat: 9.08, lon: -79.68 },      // Panama Canal
            { lat: 18.0, lon: -65.0 },       // Caribbean
            { lat: 25.77, lon: -80.19 },     // Miami
            { lat: 40.7, lon: -74.0 },       // New York
        ],
    },
    {
        id: "cape-route",
        label: "Cape Route",
        category: "Diversion Route",
        color: 0xff8fb1,
        speed: 0.014,
        cargo: "Containers, bulk cargo, tankers during Suez disruption",
        metric: "Cape diversion adds about 3,000-3,500 nautical miles versus Suez on Asia-Europe runs",
        eta: "Usually adds about 10-14 days compared with Suez",
        chokepoints: ["Cape of Good Hope"],
        waypoints: [
            { lat: 1.29, lon: 103.85 },      // Singapore
            { lat: -10.0, lon: 70.0 },       // Indian Ocean south
            { lat: -20.0, lon: 60.0 },       // Mid-Indian Ocean
            { lat: -34.35, lon: 18.47 },     // Cape of Good Hope
            { lat: -25.0, lon: -5.0 },       // South Atlantic
            { lat: -10.0, lon: -15.0 },      // Eastern Atlantic
            { lat: 10.0, lon: -20.0 },       // Mid-Atlantic ridge crossing
            { lat: 35.0, lon: -10.0 },       // Atlantic approach to Europe
            { lat: 51.95, lon: 4.14 },       // Rotterdam
        ],
    },
];

const ACTIVE_AGENTS = ["Planner", "Trader", "Comms"];
const COUNTRY_POP_EST = {
    Belgium: 11800000,
    Oman: 4700000,
    Afghanistan: 41800000,
    Djibouti: 1120000,
    Singapore: 5920000,
    USA: 335000000,
    Canada: 40500000,
    Brazil: 216000000,
    UK: 68200000,
    France: 68200000,
    Germany: 84300000,
    Switzerland: 8900000,
    Russia: 144000000,
    Israel: 9800000,
    "Saudi Arabia": 36900000,
    UAE: 10100000,
    India: 1430000000,
    China: 1410000000,
    "South Korea": 51800000,
    Japan: 123000000,
    Australia: 26800000,
    "South Africa": 62300000,
};
const NEED_LIBRARY = {
    education: { id: "education", title: "Education Fund" },
    microcredit: { id: "microcredit", title: "Microcredit Pool" },
    food: { id: "food", title: "Food Relief" },
    healthcare: { id: "healthcare", title: "Healthcare Access" },
    housing: { id: "housing", title: "Housing Support" },
    jobs: { id: "jobs", title: "Workforce Training" },
};

const COUNTRY_NEEDS = {
    Belgium: {
        priorities: ["education", "housing", "jobs"],
        metrics: {
            education: { impact: "42 grants", progress: 68 },
            housing: { impact: "118 homes aided", progress: 64 },
            jobs: { impact: "390 placements", progress: 72 },
        },
    },
    Oman: {
        priorities: ["food", "microcredit", "education"],
        metrics: {
            food: { impact: "1,920 meals", progress: 81 },
            microcredit: { impact: "$84k deployed", progress: 54 },
            education: { impact: "42 grants", progress: 68 },
        },
    },
    Afghanistan: {
        priorities: ["food", "education", "healthcare"],
        metrics: {
            food: { impact: "2,640 meals", progress: 58 },
            education: { impact: "31 grants", progress: 47 },
            healthcare: { impact: "14 clinics supplied", progress: 52 },
        },
    },
    Djibouti: {
        priorities: ["food", "microcredit", "healthcare"],
        metrics: {
            food: { impact: "1,480 meals", progress: 73 },
            microcredit: { impact: "$56k deployed", progress: 61 },
            healthcare: { impact: "9 clinics supplied", progress: 55 },
        },
    },
    Singapore: {
        priorities: ["education", "microcredit", "jobs"],
        metrics: {
            education: { impact: "64 grants", progress: 79 },
            microcredit: { impact: "$102k deployed", progress: 66 },
            jobs: { impact: "510 placements", progress: 74 },
        },
    },
};

// Major financial markets and their host cities. Hours are local exchange time.
// daysOpen: 1=Mon ... 5=Fri (skipping known holidays is out of scope here).
const MARKETS = [
    { id: "nyse", name: "NYSE", city: "New York", country: "USA", lat: 40.7128, lon: -74.0060, tz: "America/New_York", openH: 9, openM: 30, closeH: 16, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "nasdaq", name: "NASDAQ", city: "New York", country: "USA", lat: 40.7589, lon: -73.9851, tz: "America/New_York", openH: 9, openM: 30, closeH: 16, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "tsx", name: "TSX", city: "Toronto", country: "Canada", lat: 43.6532, lon: -79.3832, tz: "America/Toronto", openH: 9, openM: 30, closeH: 16, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "b3", name: "B3", city: "Sao Paulo", country: "Brazil", lat: -23.5505, lon: -46.6333, tz: "America/Sao_Paulo", openH: 10, openM: 0, closeH: 17, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "lse", name: "LSE", city: "London", country: "UK", lat: 51.5074, lon: -0.1278, tz: "Europe/London", openH: 8, openM: 0, closeH: 16, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "eur", name: "Euronext", city: "Paris", country: "France", lat: 48.8566, lon: 2.3522, tz: "Europe/Paris", openH: 9, openM: 0, closeH: 17, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "fwb", name: "Xetra", city: "Frankfurt", country: "Germany", lat: 50.1109, lon: 8.6821, tz: "Europe/Berlin", openH: 9, openM: 0, closeH: 17, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "six", name: "SIX", city: "Zurich", country: "Switzerland", lat: 47.3769, lon: 8.5417, tz: "Europe/Zurich", openH: 9, openM: 0, closeH: 17, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "moex", name: "MOEX", city: "Moscow", country: "Russia", lat: 55.7558, lon: 37.6173, tz: "Europe/Moscow", openH: 10, openM: 0, closeH: 18, closeM: 50, daysOpen: [1, 2, 3, 4, 5] },
    { id: "tase", name: "TASE", city: "Tel Aviv", country: "Israel", lat: 32.0853, lon: 34.7818, tz: "Asia/Jerusalem", openH: 9, openM: 45, closeH: 17, closeM: 25, daysOpen: [0, 1, 2, 3, 4] }, // Sun-Thu
    { id: "tadawul", name: "Tadawul", city: "Riyadh", country: "Saudi Arabia", lat: 24.7136, lon: 46.6753, tz: "Asia/Riyadh", openH: 10, openM: 0, closeH: 15, closeM: 0, daysOpen: [0, 1, 2, 3, 4] },
    { id: "dfm", name: "DFM", city: "Dubai", country: "UAE", lat: 25.2048, lon: 55.2708, tz: "Asia/Dubai", openH: 10, openM: 0, closeH: 14, closeM: 50, daysOpen: [1, 2, 3, 4, 5] },
    { id: "bse", name: "BSE", city: "Mumbai", country: "India", lat: 19.0760, lon: 72.8777, tz: "Asia/Kolkata", openH: 9, openM: 15, closeH: 15, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "sgx", name: "SGX", city: "Singapore", country: "Singapore", lat: 1.3521, lon: 103.8198, tz: "Asia/Singapore", openH: 9, openM: 0, closeH: 17, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "hkex", name: "HKEX", city: "Hong Kong", country: "China", lat: 22.3193, lon: 114.1694, tz: "Asia/Hong_Kong", openH: 9, openM: 30, closeH: 16, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "sse", name: "SSE", city: "Shanghai", country: "China", lat: 31.2304, lon: 121.4737, tz: "Asia/Shanghai", openH: 9, openM: 30, closeH: 15, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "krx", name: "KRX", city: "Seoul", country: "South Korea", lat: 37.5665, lon: 126.9780, tz: "Asia/Seoul", openH: 9, openM: 0, closeH: 15, closeM: 30, daysOpen: [1, 2, 3, 4, 5] },
    { id: "tse", name: "TSE", city: "Tokyo", country: "Japan", lat: 35.6762, lon: 139.6503, tz: "Asia/Tokyo", openH: 9, openM: 0, closeH: 15, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "asx", name: "ASX", city: "Sydney", country: "Australia", lat: -33.8688, lon: 151.2093, tz: "Australia/Sydney", openH: 10, openM: 0, closeH: 16, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
    { id: "jse", name: "JSE", city: "Johannesburg", country: "South Africa", lat: -26.2041, lon: 28.0473, tz: "Africa/Johannesburg", openH: 9, openM: 0, closeH: 17, closeM: 0, daysOpen: [1, 2, 3, 4, 5] },
];

const MAJOR_CITY_DOTS = [
    { id: "los-angeles", city: "Los Angeles", country: "USA", lat: 34.0522, lon: -118.2437 },
    { id: "chicago", city: "Chicago", country: "USA", lat: 41.8781, lon: -87.6298 },
    { id: "mexico-city", city: "Mexico City", country: "Mexico", lat: 19.4326, lon: -99.1332 },
    { id: "sao-paulo", city: "Sao Paulo", country: "Brazil", lat: -23.5505, lon: -46.6333 },
    { id: "madrid", city: "Madrid", country: "Spain", lat: 40.4168, lon: -3.7038 },
    { id: "rome", city: "Rome", country: "Italy", lat: 41.9028, lon: 12.4964 },
    { id: "istanbul", city: "Istanbul", country: "Turkey", lat: 41.0082, lon: 28.9784 },
    { id: "cairo", city: "Cairo", country: "Egypt", lat: 30.0444, lon: 31.2357 },
    { id: "lagos", city: "Lagos", country: "Nigeria", lat: 6.5244, lon: 3.3792 },
    { id: "nairobi", city: "Nairobi", country: "Kenya", lat: -1.2921, lon: 36.8219 },
    { id: "riyadh", city: "Riyadh", country: "Saudi Arabia", lat: 24.7136, lon: 46.6753 },
    { id: "tehran", city: "Tehran", country: "Iran", lat: 35.6892, lon: 51.3890 },
    { id: "karachi", city: "Karachi", country: "Pakistan", lat: 24.8607, lon: 67.0011 },
    { id: "delhi", city: "Delhi", country: "India", lat: 28.6139, lon: 77.2090 },
    { id: "bangkok", city: "Bangkok", country: "Thailand", lat: 13.7563, lon: 100.5018 },
    { id: "jakarta", city: "Jakarta", country: "Indonesia", lat: -6.2088, lon: 106.8456 },
    { id: "manila", city: "Manila", country: "Philippines", lat: 14.5995, lon: 120.9842 },
    { id: "beijing", city: "Beijing", country: "China", lat: 39.9042, lon: 116.4074 },
    { id: "seoul", city: "Seoul", country: "South Korea", lat: 37.5665, lon: 126.9780 },
    { id: "osaka", city: "Osaka", country: "Japan", lat: 34.6937, lon: 135.5023 },
    { id: "melbourne", city: "Melbourne", country: "Australia", lat: -37.8136, lon: 144.9631 },
    { id: "auckland", city: "Auckland", country: "New Zealand", lat: -36.8509, lon: 174.7645 },
];

const WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Pull local time parts for a Date in a given IANA timezone.
function localPartsInTZ(date, tz) {
    const dtf = new Intl.DateTimeFormat("en-US", {
        timeZone: tz, hour12: false,
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "short",
    });
    const parts = Object.fromEntries(dtf.formatToParts(date).map((p) => [p.type, p.value]));
    const dayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    return {
        y: Number(parts.year),
        m: Number(parts.month),
        d: Number(parts.day),
        h: Number(parts.hour === "24" ? 0 : parts.hour),
        mi: Number(parts.minute),
        s: Number(parts.second),
        dow: dayMap[parts.weekday] ?? 0,
    };
}

// Convert a wall-clock date/time in an IANA timezone into a UTC timestamp.
// Iterative offset solving keeps countdowns stable and avoids per-second drift.
function tzWallClockToUTCms(tz, year, month, day, hour, minute) {
    let guess = Date.UTC(year, month - 1, day, hour, minute, 0);
    for (let i = 0; i < 4; i += 1) {
        const localAtGuess = localPartsInTZ(new Date(guess), tz);
        const asIfUTC = Date.UTC(
            localAtGuess.y,
            localAtGuess.m - 1,
            localAtGuess.d,
            localAtGuess.h,
            localAtGuess.mi,
            localAtGuess.s
        );
        const offsetMs = asIfUTC - guess;
        const next = Date.UTC(year, month - 1, day, hour, minute, 0) - offsetMs;
        if (Math.abs(next - guess) < 1000) {
            guess = next;
            break;
        }
        guess = next;
    }
    return guess;
}

function getMarketStatus(market, now) {
    const local = localPartsInTZ(now, market.tz);
    const nowMinutes = local.h * 60 + local.mi;
    const openMinutes = market.openH * 60 + market.openM;
    const closeMinutes = market.closeH * 60 + market.closeM;
    const isTradingDay = market.daysOpen.includes(local.dow);
    const nowMs = now.getTime();

    if (isTradingDay && nowMinutes >= openMinutes && nowMinutes < closeMinutes) {
        const closeTodayUTC = tzWallClockToUTCms(market.tz, local.y, local.m, local.d, market.closeH, market.closeM);
        return { open: true, label: "OPEN", deltaMs: closeTodayUTC - nowMs, deltaLabel: "closes in", nextOpenLocal: "" };
    }

    if (isTradingDay && nowMinutes < openMinutes) {
        const openTodayUTC = tzWallClockToUTCms(market.tz, local.y, local.m, local.d, market.openH, market.openM);
        const hh = String(market.openH).padStart(2, "0");
        const mm = String(market.openM).padStart(2, "0");
        return {
            open: false,
            label: "CLOSED",
            deltaMs: openTodayUTC - nowMs,
            deltaLabel: "opens in",
            nextOpenLocal: `${WEEKDAY_SHORT[local.dow]} ${hh}:${mm}`,
        };
    }

    // find next open within next 8 days
    for (let offset = 1; offset < 8; offset += 1) {
        const probeLocal = localPartsInTZ(new Date(nowMs + offset * 86400000), market.tz);
        if (market.daysOpen.includes(probeLocal.dow)) {
            const probeOpenUTC = tzWallClockToUTCms(market.tz, probeLocal.y, probeLocal.m, probeLocal.d, market.openH, market.openM);
            const hh = String(market.openH).padStart(2, "0");
            const mm = String(market.openM).padStart(2, "0");
            return {
                open: false,
                label: "CLOSED",
                deltaMs: probeOpenUTC - nowMs,
                deltaLabel: "opens in",
                nextOpenLocal: `${WEEKDAY_SHORT[probeLocal.dow]} ${hh}:${mm}`,
            };
        }
    }
    return { open: false, label: "CLOSED", deltaMs: 0, deltaLabel: "opens in", nextOpenLocal: "" };
}

function formatHMS(ms) {
    if (ms <= 0) return "00:00:00";
    const total = Math.floor(ms / 1000);
    const d = Math.floor(total / 86400);
    const h = Math.floor((total % 86400) / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const pad = (n) => String(n).padStart(2, "0");
    if (d > 0) return `${d}d ${pad(h)}:${pad(m)}:${pad(s)}`;
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function formatMarketLocalClock(tz, now) {
    return new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(now || new Date());
}

function formatViewerLocalClock(now) {
    try {
        return new Intl.DateTimeFormat("en-GB", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
            timeZoneName: "short",
        }).format(now || new Date());
    } catch (_) {
        return (now || new Date()).toLocaleTimeString();
    }
}

function formatPopulationEstimate(value) {
    const num = Number(value);
    if (!Number.isFinite(num) || num <= 0) return "n/a";
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function latLonToVector3(latDeg, lonDeg, radius) {
    // Matches Three.js default SphereGeometry UV layout used by the Blue Marble
    // texture: u=0.5 (Greenwich, lon 0) sits on +X, lon increases east toward -Z.
    const lat = (latDeg * Math.PI) / 180;
    const lon = (lonDeg * Math.PI) / 180;
    return new THREE.Vector3(
        radius * Math.cos(lat) * Math.cos(lon),
        radius * Math.sin(lat),
        -radius * Math.cos(lat) * Math.sin(lon)
    );
}

function MetricCard({ label, value, meta, tone = "cyan" }) {
    return React.createElement(
        "section",
        { className: `hud-card tone-${tone}` },
        React.createElement("div", { className: "hud-label" }, label),
        React.createElement("div", { className: "hud-value" }, value),
        meta ? React.createElement("div", { className: "hud-card-meta" }, meta) : null
    );
}

function MarkerRibbon({ markers, selectedId, onSelect }) {
    return React.createElement(
        "section",
        { className: "hud-marker-ribbon", "aria-label": "Strategic region nodes" },
        ...markers.map((marker) =>
            React.createElement(
                "button",
                {
                    key: marker.id,
                    type: "button",
                    className: `hud-marker-pill ${selectedId === marker.id ? "is-active" : ""}`,
                    onClick: () => onSelect(marker),
                },
                React.createElement("span", {
                    className: "hud-marker-dot",
                    style: { backgroundColor: `#${marker.color.toString(16).padStart(6, "0")}` },
                }),
                React.createElement("span", { className: "hud-marker-name" }, marker.label),
                React.createElement("span", { className: "hud-marker-priority" }, marker.priority)
            )
        )
    );
}

function ActiveAgentLoop({ activeIndex }) {
    return React.createElement(
        "section",
        { className: "hud-agent-loop", "aria-label": "Active agent loop" },
        ...ACTIVE_AGENTS.map((name, idx) =>
            React.createElement(
                "div",
                { key: name, className: `agent-chip ${idx === activeIndex ? "is-active" : ""}` },
                name
            )
        )
    );
}

function DialogueDatasetPanel({ rows, loading, error }) {
    return React.createElement(
        "section",
        { className: "hud-dialogue-panel", "aria-label": "April 27 dialogue dataset" },
        React.createElement("div", { className: "hud-dialogue-title" }, "Command Transcript"),
        loading
            ? React.createElement("div", { className: "hud-dialogue-meta" }, "Loading dataset...")
            : error
                ? React.createElement("div", { className: "hud-dialogue-meta" }, error)
                : React.createElement("div", { className: "hud-dialogue-meta" }, `${rows.length} lines indexed`),
        React.createElement(
            "div",
            { className: "hud-dialogue-list" },
            ...rows.slice(0, 4).map((item, idx) =>
                React.createElement(
                    "div",
                    { key: `${item.ts || "row"}-${idx}`, className: "hud-dialogue-row" },
                    React.createElement("span", { className: "hud-dialogue-speaker" }, item.speaker || "unknown"),
                    React.createElement("span", { className: "hud-dialogue-text" }, item.text || "")
                )
            )
        )
    );
}

function LiveNewsPanel() {
    const [state, setState] = React.useState({ loading: true, error: "", rows: [], source: "reuters", updatedAt: "" });

    React.useEffect(() => {
        let cancelled = false;
        let timer = null;

        const load = async () => {
            try {
                const res = await fetch("/hud/news?source=reuters&limit=6", { cache: "no-store" });
                if (!res.ok) throw new Error(`news status ${res.status}`);
                const payload = await res.json();
                if (cancelled) return;
                setState({
                    loading: false,
                    error: "",
                    rows: Array.isArray(payload.items) ? payload.items : [],
                    source: String(payload.source || "reuters"),
                    updatedAt: String(payload.updated_at || ""),
                });
            } catch (_e) {
                if (!cancelled) setState((prev) => ({ ...prev, loading: false, error: "News feed unavailable" }));
            }
        };

        load();
        timer = setInterval(load, 180000);

        return () => {
            cancelled = true;
            if (timer) clearInterval(timer);
        };
    }, []);

    return React.createElement(
        "section",
        { className: "hud-news-panel", "aria-label": "Live global news" },
        React.createElement("div", { className: "hud-news-title" }, "Live News"),
        React.createElement(
            "div",
            { className: "hud-news-meta" },
            state.loading
                ? "Loading Reuters feed..."
                : state.error
                    ? state.error
                    : `${state.source.toUpperCase()} | ${state.rows.length} updates`
        ),
        React.createElement(
            "div",
            { className: "hud-news-list" },
            ...(state.rows.length
                ? state.rows.slice(0, 4).map((row, idx) =>
                    React.createElement(
                        "a",
                        {
                            key: `${row.url || "news"}-${idx}`,
                            className: "hud-news-row",
                            href: row.url || "#",
                            target: "_blank",
                            rel: "noreferrer noopener",
                        },
                        React.createElement("span", { className: "hud-news-headline" }, row.title || "Untitled"),
                        React.createElement("span", { className: "hud-news-time" }, row.published || "recent")
                    )
                )
                : [React.createElement("div", { key: "empty", className: "hud-news-empty" }, "No updates right now")])
        ),
        state.updatedAt
            ? React.createElement("div", { className: "hud-news-updated" }, `Updated ${new Date(state.updatedAt).toLocaleTimeString()}`)
            : null
    );
}

function FinancialSocialMissionWidgets({ selectedMarker, liveLocation }) {
    const HOME_COUNTRY = "Belgium";
    const availableCountries = React.useMemo(
        () => [HOME_COUNTRY, ...Object.keys(COUNTRY_NEEDS).filter((c) => c !== HOME_COUNTRY)],
        []
    );
    const [countryMode, setCountryMode] = React.useState("auto");
    const [pickedNeedIds, setPickedNeedIds] = React.useState([]);

    const autoCountry = React.useMemo(() => {
        if (selectedMarker?.country && COUNTRY_NEEDS[selectedMarker.country]) {
            return selectedMarker.country;
        }
        if (liveLocation && Number.isFinite(liveLocation.lat) && Number.isFinite(liveLocation.lon)) {
            let best = null;
            let bestScore = Number.POSITIVE_INFINITY;
            MARKETS.forEach((m) => {
                const d = Math.hypot(liveLocation.lat - m.lat, liveLocation.lon - m.lon);
                if (d < bestScore) {
                    best = m;
                    bestScore = d;
                }
            });
            if (best?.country && COUNTRY_NEEDS[best.country]) return best.country;
        }
        return HOME_COUNTRY;
    }, [liveLocation, selectedMarker]);

    const activeCountry = countryMode === "auto" ? autoCountry : countryMode;
    const countryModel = COUNTRY_NEEDS[activeCountry] || COUNTRY_NEEDS[HOME_COUNTRY];

    React.useEffect(() => {
        setPickedNeedIds(countryModel.priorities.slice(0, 3));
    }, [activeCountry]);

    const activeNeedIds = pickedNeedIds.length ? pickedNeedIds : countryModel.priorities.slice(0, 3);
    const cards = activeNeedIds
        .map((needId) => {
            const def = NEED_LIBRARY[needId];
            const metric = countryModel.metrics[needId];
            if (!def || !metric) return null;
            return {
                id: needId,
                title: def.title,
                impact: metric.impact,
                progress: metric.progress,
            };
        })
        .filter(Boolean)
        .slice(0, 3);

    const allNeedIds = countryModel.priorities.filter((id) => NEED_LIBRARY[id] && countryModel.metrics[id]);

    return React.createElement(
        "section",
        { className: "hud-mission-grid", "aria-label": "Financial social mission widgets" },
        React.createElement(
            "div",
            { className: "hud-mission-controls" },
            React.createElement(
                "label",
                { className: "hud-mission-control" },
                React.createElement("span", { className: "hud-mission-control-label" }, "Country profile"),
                React.createElement(
                    "select",
                    {
                        className: "hud-mission-select",
                        value: countryMode,
                        onChange: (e) => setCountryMode(e.target.value),
                    },
                    React.createElement("option", { value: "auto" }, `Auto (${autoCountry})`),
                    ...availableCountries.map((country) =>
                        React.createElement("option", { key: country, value: country }, country)
                    )
                )
            ),
            React.createElement(
                "div",
                { className: "hud-mission-picker", role: "group", "aria-label": "Need categories" },
                ...allNeedIds.map((needId) =>
                    React.createElement(
                        "button",
                        {
                            key: needId,
                            type: "button",
                            className: `hud-mission-chip ${activeNeedIds.includes(needId) ? "is-active" : ""}`,
                            onClick: () => {
                                setPickedNeedIds((prev) => {
                                    if (prev.includes(needId)) {
                                        if (prev.length <= 1) return prev;
                                        return prev.filter((id) => id !== needId);
                                    }
                                    return [...prev, needId].slice(-3);
                                });
                            },
                        },
                        NEED_LIBRARY[needId].title
                    )
                )
            )
        ),
        ...cards.map((widget) =>
            React.createElement(
                "article",
                { key: widget.id, className: "hud-mission-card" },
                React.createElement("div", { className: "hud-mission-title" }, widget.title),
                React.createElement("div", { className: "hud-mission-impact" }, widget.impact),
                React.createElement(
                    "div",
                    { className: "hud-mission-progress" },
                    React.createElement("span", { className: "hud-mission-fill", style: { width: `${widget.progress}%` } })
                ),
                React.createElement("div", { className: "hud-mission-meta" }, `${widget.progress}% target coverage`)
            )
        ),
        React.createElement("div", { className: "hud-mission-country-meta" }, `Needs model: ${activeCountry}`)
    );
}

function useLiveLocation() {
    const [loc, setLoc] = React.useState(null);
    React.useEffect(() => {
        if (typeof navigator === "undefined" || !navigator.geolocation) return undefined;
        let watchId = null;
        let cancelled = false;

        const start = () => {
            if (cancelled) return;
            try {
                watchId = navigator.geolocation.watchPosition(
                    (pos) => setLoc({
                        lat: pos.coords.latitude,
                        lon: pos.coords.longitude,
                        accuracy: pos.coords.accuracy,
                        ts: pos.timestamp,
                    }),
                    () => setLoc(null),
                    { enableHighAccuracy: false, maximumAge: 60000, timeout: 15000 }
                );
            } catch (_e) { /* unavailable */ }
        };

        // Silent: only activate if permission has already been granted (Permissions API).
        // We never call getCurrentPosition / watchPosition before that, so no prompt is shown.
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({ name: "geolocation" }).then((status) => {
                if (status.state === "granted") start();
                status.onchange = () => {
                    if (status.state === "granted" && watchId === null) start();
                };
            }).catch(() => { /* permissions API blocked — stay silent */ });
        }

        return () => {
            cancelled = true;
            if (watchId !== null) {
                try { navigator.geolocation.clearWatch(watchId); } catch (_e) { /* noop */ }
            }
        };
    }, []);
    return loc;
}

function LiveLocationBadge({ liveLocation }) {
    const HOME = { lat: 50.7806267, lon: 5.4639172, label: "Tongeren 3700, BE" };
    const isAway = liveLocation && Math.hypot(liveLocation.lat - HOME.lat, liveLocation.lon - HOME.lon) > 0.5;
    return React.createElement(
        "section",
        { className: "hud-locbadge", "aria-label": "Live location status" },
        React.createElement(
            "div",
            { className: "hud-locbadge-row" },
            React.createElement("span", { className: "hud-locbadge-dot home" }),
            React.createElement("span", { className: "hud-locbadge-label" }, "HOME"),
            React.createElement("span", { className: "hud-locbadge-value" }, HOME.label)
        ),
        liveLocation
            ? React.createElement(
                "div",
                { className: "hud-locbadge-row" },
                React.createElement("span", { className: "hud-locbadge-dot live" }),
                React.createElement("span", { className: "hud-locbadge-label" }, isAway ? "TRIP" : "AT HOME"),
                React.createElement(
                    "span",
                    { className: "hud-locbadge-value" },
                    `${liveLocation.lat.toFixed(3)}, ${liveLocation.lon.toFixed(3)}`
                )
            )
            : React.createElement(
                "div",
                { className: "hud-locbadge-row dim" },
                React.createElement("span", { className: "hud-locbadge-dot off" }),
                React.createElement("span", { className: "hud-locbadge-label" }, "LIVE LOC"),
                React.createElement("span", { className: "hud-locbadge-value" }, "permission needed")
            )
    );
}

function MarketHoursPanel() {
    const [markets, setMarkets] = React.useState(() => MARKETS);
    const [now, setNow] = React.useState(() => new Date());
    const [clockOffsetMs, setClockOffsetMs] = React.useState(0);
    const [timeSource, setTimeSource] = React.useState("local");

    const fetchMarketSchedule = React.useCallback(async () => {
        try {
            const res = await fetch(`/hud/markets?_ts=${Date.now()}`, { cache: "no-store" });
            if (!res.ok) return;
            const data = await res.json();
            const items = Array.isArray(data && data.items) ? data.items : null;
            if (!items || items.length === 0) return;
            setMarkets(items.filter((item) => item && item.id && item.tz && item.openH != null && item.closeH != null));
        } catch (_) {
        }
    }, []);

    const syncServerClock = React.useCallback(async () => {
        try {
            const res = await fetch(`/health?_ts=${Date.now()}`, { cache: "no-store" });
            const serverDateHeader = res.headers.get("date");
            if (!serverDateHeader) {
                setTimeSource("local");
                return;
            }
            const serverNow = new Date(serverDateHeader).getTime();
            if (!Number.isFinite(serverNow)) {
                setTimeSource("local");
                return;
            }
            setClockOffsetMs(serverNow - Date.now());
            setTimeSource("server");
        } catch (_) {
            setTimeSource("local");
        }
    }, []);

    React.useEffect(() => {
        const t = window.setInterval(() => setNow(new Date()), 1000);
        return () => window.clearInterval(t);
    }, []);

    React.useEffect(() => {
        syncServerClock();
        const t = window.setInterval(syncServerClock, 5 * 60 * 1000);
        return () => window.clearInterval(t);
    }, [syncServerClock]);

    React.useEffect(() => {
        fetchMarketSchedule();
        const t = window.setInterval(fetchMarketSchedule, 10 * 60 * 1000);
        return () => window.clearInterval(t);
    }, [fetchMarketSchedule]);

    const effectiveNow = React.useMemo(
        () => new Date(now.getTime() + clockOffsetMs),
        [now, clockOffsetMs]
    );

    const enriched = markets.map((m) => ({ market: m, status: getMarketStatus(m, effectiveNow) }));
    const openCount = enriched.filter((row) => row.status.open).length;
    const nextOpen = enriched
        .filter((row) => !row.status.open && row.status.deltaMs > 0)
        .sort((a, b) => a.status.deltaMs - b.status.deltaMs)[0] || null;
    const viewerLocal = formatViewerLocalClock(new Date());
    const headerMeta = openCount > 0
        ? `${openCount} / ${markets.length} open • machine ${viewerLocal}`
        : nextOpen
            ? `All cash markets closed • next: ${nextOpen.market.name} in ${formatHMS(nextOpen.status.deltaMs)} • machine ${viewerLocal}`
            : `All cash markets closed • machine ${viewerLocal}`;

    return React.createElement(
        "section",
        { className: "hud-market-panel", "aria-label": "Global market hours" },
        React.createElement(
            "div",
            { className: "hud-market-header" },
            React.createElement(
                "div",
                { className: "hud-market-title-wrap" },
                React.createElement("div", { className: "hud-market-title" }, "ECA x EVA Market Matrix"),
                React.createElement("div", { className: "hud-market-subtitle" }, "Cash session lattice and handoff timing")
            ),
            React.createElement(
                "div",
                { className: "hud-market-head-right" },
                React.createElement(
                    "div",
                    { className: "hud-market-brand" },
                    React.createElement("span", { className: "hud-market-chip jarvis" }, "ECA CORE"),
                    React.createElement("span", { className: "hud-market-chip eva" }, "EVA ANALYTICS")
                ),
                React.createElement("div", { className: "hud-market-meta" }, headerMeta)
            )
        ),
        React.createElement(
            "div",
            { className: "hud-market-list" },
            ...enriched.map(({ market, status }) =>
                React.createElement(
                    "div",
                    { key: market.id, className: `hud-market-row ${status.open ? "is-open" : "is-closed"}` },
                    React.createElement("span", { className: "hud-market-dot" }),
                    React.createElement(
                        "div",
                        { className: "hud-market-ident" },
                        React.createElement("span", { className: "hud-market-name" }, market.name),
                        React.createElement("span", { className: "hud-market-city" }, `${market.city} • ${formatMarketLocalClock(market.tz, effectiveNow)} local`)
                    ),
                    React.createElement(
                        "div",
                        { className: "hud-market-status" },
                        React.createElement("span", { className: "hud-market-state" }, status.label),
                        React.createElement(
                            "span",
                            { className: "hud-market-countdown" },
                            `${status.deltaLabel} ${formatHMS(status.deltaMs)}${status.nextOpenLocal ? ` (${status.nextOpenLocal})` : ""}`
                        )
                    )
                )
            )
        )
    );
}

function BurstWidget({ label, tone, delayMs }) {
    return React.createElement(
        "div",
        { className: `burst-widget tone-${tone}` },
        React.createElement("div", { className: "burst-ring", style: { animationDelay: `${delayMs}ms` } }),
        React.createElement("div", { className: "burst-core" }),
        React.createElement("div", { className: "burst-label" }, label)
    );
}

function BurstWidgetStrip() {
    return React.createElement(
        "section",
        { className: "hud-burst-strip", "aria-label": "Signal burst widgets" },
        React.createElement(BurstWidget, { label: "Signal", tone: "blue", delayMs: 0 }),
        React.createElement(BurstWidget, { label: "Priority", tone: "rose", delayMs: 280 }),
        React.createElement(BurstWidget, { label: "Ops", tone: "gold", delayMs: 560 })
    );
}


const WEATHER_LABELS_GLOBE = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunder hail",
};

function buildStarField(count, rMin, rMax, ptSize, bandFocus) {
    const pos = [], col = [];
    const c = new THREE.Color();
    for (let i = 0; i < count; i++) {
        const inBand = bandFocus && Math.random() < 0.7;
        const spread = inBand ? (Math.random() - 0.5) * 0.45 : (Math.random() - 0.5) * 2;
        const theta = Math.PI / 2 + spread;
        const phi = Math.random() * Math.PI * 2;
        const r = rMin + Math.random() * (rMax - rMin);
        const x0 = r * Math.sin(theta) * Math.cos(phi);
        const y0 = r * Math.cos(theta);
        const z0 = r * Math.sin(theta) * Math.sin(phi);
        const tilt = (25 * Math.PI) / 180;
        pos.push(x0, y0 * Math.cos(tilt) - z0 * Math.sin(tilt), y0 * Math.sin(tilt) + z0 * Math.cos(tilt));
        const h = Math.random();
        if (h < 0.55) c.setHSL(0.58, 0.4, 0.78 + Math.random() * 0.2);
        else if (h < 0.85) c.setHSL(0.10, 0.25, 0.85 + Math.random() * 0.15);
        else c.setHSL(0.95, 0.35, 0.70 + Math.random() * 0.2);
        col.push(c.r, c.g, c.b);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    return new THREE.Points(geo, new THREE.PointsMaterial({
        size: ptSize, transparent: true, opacity: 0.82,
        vertexColors: true, sizeAttenuation: true, depthWrite: false,
    }));
}

function fallbackColorFromId(id) {
    const colors = ['#5bc8ff', '#ff6b88', '#ffd166', '#06d6a0', '#a78bfa', '#fb923c', '#34d399'];
    let h = 0; for (let i = 0; i < (id || '').length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
    return colors[h % colors.length];
}

function seededUnitFromId(id, salt) {
    const raw = String(id || '') + '|' + String(salt || '');
    let h = 2166136261;
    for (let i = 0; i < raw.length; i++) {
        h ^= raw.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return (h >>> 0) / 4294967295;
}

function normalizeMarkerColor(marker) {
    if (marker && typeof marker.color === 'number') {
        return '#' + marker.color.toString(16).padStart(6, '0');
    }
    if (marker && typeof marker.color === 'string') {
        return marker.color;
    }
    return fallbackColorFromId(marker && marker.id);
}

function colorDriftForMarker(marker, elapsedMs, cache) {
    const markerId = (marker && marker.id) || 'marker';
    const key = markerId;
    let cfg = cache.get(key);
    if (!cfg) {
        cfg = {
            speedHz: 0.009 + seededUnitFromId(markerId, 'speed') * 0.012,
            speedHz2: 0.004 + seededUnitFromId(markerId, 'speed2') * 0.007,
            phase: seededUnitFromId(markerId, 'phase') * Math.PI * 2,
            phase2: seededUnitFromId(markerId, 'phase2') * Math.PI * 2,
            hueAmp: 0.01 + seededUnitFromId(markerId, 'hueAmp') * 0.018,
            satAmp: 0.02 + seededUnitFromId(markerId, 'satAmp') * 0.03,
            lightAmp: 0.022 + seededUnitFromId(markerId, 'lightAmp') * 0.04,
            hueBias: (seededUnitFromId(markerId, 'hueBias') - 0.5) * 0.006,
        };
        cache.set(key, cfg);
    }

    const base = new THREE.Color(normalizeMarkerColor(marker));
    const hsl = { h: 0, s: 0, l: 0 };
    base.getHSL(hsl);

    const t = elapsedMs * 0.001;
    const wavePrimary = Math.sin(t * cfg.speedHz * Math.PI * 2 + cfg.phase);
    const waveSecondary = Math.sin(t * cfg.speedHz2 * Math.PI * 2 + cfg.phase2);
    const wave = wavePrimary * 0.72 + waveSecondary * 0.28;
    const waveOffset = Math.sin(t * cfg.speedHz * Math.PI * 2 * 0.83 + cfg.phase * 1.23) * 0.66
        + Math.sin(t * cfg.speedHz2 * Math.PI * 2 * 1.17 + cfg.phase2 * 1.09) * 0.34;

    const nextH = (hsl.h + cfg.hueBias + cfg.hueAmp * wave + 1) % 1;
    const nextS = Math.min(1, Math.max(0, hsl.s + cfg.satAmp * waveOffset));
    const nextL = Math.min(0.88, Math.max(0.2, hsl.l + cfg.lightAmp * wave));

    return '#' + new THREE.Color().setHSL(nextH, nextS, nextL).getHexString();
}

const _weatherCache = new Map();
async function fetchWeather(lat, lon) {
    const key = lat.toFixed(2) + ',' + lon.toFixed(2);
    const cached = _weatherCache.get(key);
    if (cached && Date.now() - cached.ts < 600000) return cached.data;
    try {
        const r = await fetch('https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon + '&current=temperature_2m,weather_code&timezone=auto');
        const j = await r.json();
        const data = { temp: j.current && j.current.temperature_2m, code: j.current && j.current.weather_code };
        _weatherCache.set(key, { data, ts: Date.now() });
        return data;
    } catch (e) { return null; }
}

const _wbCache = new Map();
async function fetchWorldBankGDP(year) {
    if (_wbCache.has(year)) return _wbCache.get(year);
    try {
        const r = await fetch('https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json&per_page=300&date=' + year);
        const j = await r.json();
        const map = {};
        ((j && j[1]) || []).forEach(e => { if (e.value) map[e.countryiso3code] = e.value; });
        _wbCache.set(year, map);
        return map;
    } catch (e) { return {}; }
}

function GlobeLayer({ onMarkerSelect, selectedMarkerId, selectedMarker, liveLocation, markers = [] }) {
    const containerRef = React.useRef(null);
    const statusChipRef = React.useRef(null);
    const hoverCardRef = React.useRef(null);
    const hoverLineRef = React.useRef(null);
    const cameraRef = React.useRef(null);
    const rendererRef = React.useRef(null);
    const containerDOMRef = React.useRef(null);
    const hoverPointRef = React.useRef(null);
    const mousePixelRef = React.useRef({ x: 0, y: 0 });
    const [activeLayer, setActiveLayer] = React.useState(null);
    const [timeYear, setTimeYear] = React.useState(2023);
    const [hoverInfo, setHoverInfo] = React.useState(null);

    React.useEffect(function () {
        if (activeLayer !== 'economic') return;
        fetchWorldBankGDP(timeYear).then(function () { });
    }, [activeLayer, timeYear]);

    React.useEffect(function () {
        const container = containerRef.current;
        if (!container) return;

        const W = Math.max(300, container.clientWidth || 300);
        const H = Math.max(360, container.clientHeight || 360);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(W, H);
        container.appendChild(renderer.domElement);

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 5000);
        camera.position.set(0, 0, 280);

        // Store refs for line positioning in other effects
        cameraRef.current = camera;
        rendererRef.current = renderer;
        containerDOMRef.current = container;

        scene.add(new THREE.AmbientLight(0x334466, 0.9));
        const sun = new THREE.DirectionalLight(0xfff8e7, 1.35);
        sun.position.set(400, 200, 300);
        scene.add(sun);
        const rim = new THREE.DirectionalLight(0x2233ff, 0.25);
        rim.position.set(-300, -150, -200);
        scene.add(rim);

        scene.add(buildStarField(3400, 1800, 2400, 1.4, true));
        scene.add(buildStarField(520, 1600, 2200, 2.2, false));

        const atmGeo = new THREE.SphereGeometry(118, 64, 64);
        const atmMat = new THREE.ShaderMaterial({
            transparent: true, depthWrite: false, side: THREE.BackSide,
            uniforms: { glowColor: { value: new THREE.Color(0x1a6eb5) } },
            vertexShader: "varying float intensity; void main() { vec3 vNormal = normalize(normalMatrix * normal); intensity = pow(dot(vNormal, vec3(0,0,1)), 4.5); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
            fragmentShader: "uniform vec3 glowColor; varying float intensity; void main() { gl_FragColor = vec4(glowColor, intensity * 0.6); }",
        });
        scene.add(new THREE.Mesh(atmGeo, atmMat));

        const moonPivot = new THREE.Object3D();
        scene.add(moonPivot);
        const moonMesh = new THREE.Mesh(
            new THREE.SphereGeometry(6, 32, 32),
            new THREE.MeshStandardMaterial({ color: 0xbbbbcc, roughness: 0.9 })
        );
        moonMesh.position.set(220, 0, 0);
        moonPivot.add(moonMesh);

        const globe = new ThreeGlobe({ animateIn: false })
            .globeImageUrl('/hud/react/textures/earth_atmos_2048.jpg')
            .bumpImageUrl('/hud/react/textures/earth_normal_2048.jpg');

        const markerDriftCache = new Map();

        function buildPointsData(elapsedMs) {
            const pts = [];
            const activeMarkers = Array.isArray(markers) ? markers : [];
            activeMarkers.forEach(function (m) {
                if (m.lat == null || m.lon == null) return;
                const markerColor = selectedMarkerId === m.id
                    ? '#00ffcc'
                    : colorDriftForMarker(m, elapsedMs || 0, markerDriftCache);
                pts.push({ lat: m.lat, lng: m.lon, size: selectedMarkerId === m.id ? 0.9 : 0.55, color: markerColor, _type: 'marker', _data: m });
            });
            pts.push({ lat: 50.7805, lng: 5.4631, size: 0.6, color: '#ffa500', _type: 'home', _data: { label: 'Home Base', region: 'Tongeren, Belgium' } });
            if (liveLocation && liveLocation.lat != null) {
                pts.push({ lat: liveLocation.lat, lng: liveLocation.lon != null ? liveLocation.lon : liveLocation.lng, size: 0.65, color: '#00e5ff', _type: 'live', _data: { label: 'Live Location' } });
            }
            MARKETS.forEach(function (mkt) {
                const st = getMarketStatus(mkt, new Date());
                pts.push({ lat: mkt.lat, lng: mkt.lon, size: 0.4, color: st.open ? '#00ff88' : '#ff4455', _type: 'market', _data: Object.assign({}, mkt, { status: st }) });
            });
            return pts;
        }

        globe.pointsData(buildPointsData(0)).pointAltitude(0.01).pointColor(function (d) { return d.color; }).pointRadius(function (d) { return d.size; }).pointResolution(6);

        const arcsData = [];
        SHIPPING_LANES.forEach(function (lane) {
            const wpts = lane.waypoints;
            for (let i = 0; i < wpts.length - 1; i++) {
                arcsData.push({ startLat: wpts[i].lat, startLng: wpts[i].lon, endLat: wpts[i + 1].lat, endLng: wpts[i + 1].lon, color: '#' + lane.color.toString(16).padStart(6, '0'), _label: lane.label, _cargo: lane.cargo });
            }
        });
        const markerMap = {};
        (Array.isArray(markers) ? markers : []).forEach(function (m) { markerMap[m.id] = m; });
        GLOBE_CONNECTIONS.forEach(function (pair) {
            const ma = markerMap[pair[0]], mb = markerMap[pair[1]];
            if (ma && ma.lat != null && mb && mb.lat != null) {
                arcsData.push({ startLat: ma.lat, startLng: ma.lon, endLat: mb.lat, endLng: mb.lon, color: '#ffffff', _label: ma.label + ' - ' + mb.label });
            }
        });
        globe.arcsData(arcsData).arcColor(function (d) { return d.color; }).arcStroke(0.5).arcDashLength(0.4).arcDashGap(0.2).arcDashAnimateTime(3000).arcAltitudeAutoScale(0.25);

        scene.add(globe);

        // Helper function to calculate distance from point to line segment
        function distanceToLineSegment(p, a, b) {
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const len2 = dx * dx + dy * dy;
            if (len2 === 0) return Math.hypot(p.x - a.x, p.y - a.y);
            let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
            t = Math.max(0, Math.min(1, t));
            const closest = { x: a.x + t * dx, y: a.y + t * dy };
            return Math.hypot(p.x - closest.x, p.y - closest.y);
        }

        if (typeof globe.onPointHover === 'function') {
            globe.onPointHover(function (pt) {
                if (!pt) { setHoverInfo(null); hoverPointRef.current = null; return; }
                hoverPointRef.current = { lat: pt.lat, lng: pt.lng };
                const info = { label: (pt._data && pt._data.label) ? pt._data.label : 'Unknown', type: pt._type, lat: pt.lat, lng: pt.lng };
                if (pt._type === 'market') {
                    info.extra = pt._data.label + ' - ' + (pt._data.status && pt._data.status.open ? 'OPEN' : 'CLOSED');
                    setHoverInfo(info);
                } else {
                    fetchWeather(pt.lat, pt.lng).then(function (wx) {
                        if (wx) info.weather = (wx.temp != null ? wx.temp + String.fromCharCode(176) + 'C ' : '') + (WEATHER_LABELS_GLOBE[wx.code] || '');
                        setHoverInfo(Object.assign({}, info));
                    });
                    setHoverInfo(info);
                }
            });
        }
        if (typeof globe.onPointClick === 'function') {
            globe.onPointClick(function (pt) {
                if (pt && pt._type === 'marker' && onMarkerSelect) onMarkerSelect(pt._data);
            });
        }
        if (typeof globe.onLinkHover === 'function') {
            globe.onLinkHover(function (arc) {
                if (!arc) { setHoverInfo(null); hoverPointRef.current = null; return; }
                // Calculate midpoint on the arc for the connecting line
                const midLat = (arc.startLat + arc.endLat) / 2;
                const midLng = (arc.startLng + arc.endLng) / 2;
                hoverPointRef.current = { lat: midLat, lng: midLng };
                setHoverInfo({ label: arc._label || 'Shipping Lane', type: 'arc', lat: midLat, lng: midLng, extra: arc._cargo });
            });
        } else if (typeof globe.onArcHover === 'function') {
            globe.onArcHover(function (arc) {
                if (!arc) { setHoverInfo(null); hoverPointRef.current = null; return; }
                // Calculate midpoint on the arc for the connecting line
                const midLat = (arc.startLat + arc.endLat) / 2;
                const midLng = (arc.startLng + arc.endLng) / 2;
                hoverPointRef.current = { lat: midLat, lng: midLng };
                setHoverInfo({ label: arc._label || 'Shipping Lane', type: 'arc', lat: midLat, lng: midLng, extra: arc._cargo });
            });
        }

        let isDragging = false, lastX = 0, lastY = 0, rotX = 0.3, rotY = 0, camDist = 280;
        const ZOOM_MIN = 130, ZOOM_MAX = 500;

        function updateCamera() {
            camera.position.x = camDist * Math.sin(rotY) * Math.cos(rotX);
            camera.position.y = camDist * Math.sin(rotX);
            camera.position.z = camDist * Math.cos(rotY) * Math.cos(rotX);
            camera.lookAt(0, 0, 0);
        }
        updateCamera();

        const canvas = renderer.domElement;
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        function onMouseDown(e) { isDragging = true; lastX = e.clientX; lastY = e.clientY; setHoverInfo(null); }
        function onMouseMove(e) {
            const rect = canvas.getBoundingClientRect();
            mousePixelRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };

            // Handle dragging first
            if (isDragging) {
                rotY -= (e.clientX - lastX) * 0.006; rotX += (e.clientY - lastY) * 0.004;
                rotX = Math.max(-1.4, Math.min(1.4, rotX));
                lastX = e.clientX; lastY = e.clientY; updateCamera();
                return;
            }

            // When not dragging, detect arcs for hover
            // Update mouse position for raycasting
            mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

            // Raycast to detect globe objects (including arcs if they're raycaster-enabled)
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(scene.children, true);

            // Look for arc intersections (try to find arc data)
            let foundArc = false;
            for (const intersection of intersects) {
                const obj = intersection.object;
                // Check if this looks like an arc object
                if (obj.userData && obj.userData.arcData) {
                    const arcData = obj.userData.arcData;
                    const midLat = (arcData.startLat + arcData.endLat) / 2;
                    const midLng = (arcData.startLng + arcData.endLng) / 2;
                    hoverPointRef.current = { lat: midLat, lng: midLng };
                    setHoverInfo({ label: arcData._label || 'Shipping Lane', type: 'arc', lat: midLat, lng: midLng, extra: arcData._cargo });
                    foundArc = true;
                    break;
                }
            }

            // If no arc found via raycaster, try checking distance to arc paths
            if (!foundArc && arcsData && Array.isArray(arcsData)) {
                let closestDist = Infinity;
                let closestArc = null;

                for (const arc of arcsData) {
                    // Use the same globe axis conversion as the render layer to avoid mislabeled hover hits.
                    const startPhi = (90 - arc.startLat) * Math.PI / 180;
                    const startTheta = (arc.startLng + 180) * Math.PI / 180;
                    const endPhi = (90 - arc.endLat) * Math.PI / 180;
                    const endTheta = (arc.endLng + 180) * Math.PI / 180;

                    const start = new THREE.Vector3(
                        100 * Math.sin(startPhi) * Math.cos(startTheta),
                        100 * Math.cos(startPhi),
                        100 * Math.sin(startPhi) * Math.sin(startTheta)
                    );
                    const end = new THREE.Vector3(
                        100 * Math.sin(endPhi) * Math.cos(endTheta),
                        100 * Math.cos(endPhi),
                        100 * Math.sin(endPhi) * Math.sin(endTheta)
                    );

                    start.project(camera);
                    end.project(camera);

                    const startScreen = new THREE.Vector2(start.x, start.y);
                    const endScreen = new THREE.Vector2(end.x, end.y);

                    const dist = distanceToLineSegment(mouse, startScreen, endScreen);
                    if (dist < closestDist && dist < 0.08) {
                        closestDist = dist;
                        closestArc = arc;
                    }
                }

                if (closestArc) {
                    const midLat = (closestArc.startLat + closestArc.endLat) / 2;
                    const midLng = (closestArc.startLng + closestArc.endLng) / 2;
                    hoverPointRef.current = { lat: midLat, lng: midLng };
                    setHoverInfo({ label: closestArc._label || 'Shipping Lane', type: 'arc', lat: midLat, lng: midLng, extra: closestArc._cargo });
                } else {
                    setHoverInfo(null);
                    hoverPointRef.current = null;
                }
            } else if (!foundArc) {
                setHoverInfo(null);
                hoverPointRef.current = null;
            }
        }
        function onMouseUp() { isDragging = false; }
        function onWheel(e) {
            e.preventDefault();
            const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
            const zoomFactor = Math.exp(delta * 0.0015);
            camDist = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, camDist * zoomFactor));
            updateCamera();
        }
        canvas.addEventListener('mousedown', onMouseDown);
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
        canvas.addEventListener('wheel', onWheel, { passive: false });

        let rafId, t = 0;
        let lastMarkerColorRefresh = 0;
        function animate() {
            rafId = requestAnimationFrame(animate);
            t += 0.008;
            moonPivot.rotation.y = t * 0.15;
            const elapsedMs = performance.now();
            if (elapsedMs - lastMarkerColorRefresh > MARKER_COLOR_REFRESH_MS) {
                globe.pointsData(buildPointsData(elapsedMs));
                lastMarkerColorRefresh = elapsedMs;
            }
            renderer.render(scene, camera);
        }
        animate();

        const mktTimer = setInterval(function () { globe.pointsData(buildPointsData(performance.now())); }, 30000);
        const resizeObs = new ResizeObserver(function (entries) {
            const e = entries[0]; if (!e) return;
            renderer.setSize(e.contentRect.width, e.contentRect.height);
            camera.aspect = e.contentRect.width / e.contentRect.height;
            camera.updateProjectionMatrix();
        });
        resizeObs.observe(container);
        if (statusChipRef.current) statusChipRef.current.textContent = 'Strategic Mesh Online';

        return function () {
            cancelAnimationFrame(rafId); clearInterval(mktTimer);
            canvas.removeEventListener('mousedown', onMouseDown);
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
            canvas.removeEventListener('wheel', onWheel);
            resizeObs.disconnect();
            scene.traverse(function (obj) {
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) { const mats = Array.isArray(obj.material) ? obj.material : [obj.material]; mats.forEach(function (m) { m.dispose(); }); }
            });
            renderer.dispose();
            if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
        };
    }, [markers, selectedMarkerId, liveLocation]);

    React.useEffect(function () {
        const card = hoverCardRef.current; if (!card) return;
        const line = hoverLineRef.current; if (!line) return;
        const camera = cameraRef.current; if (!camera) return;
        const container = containerDOMRef.current; if (!container) return;

        // Only show card for hovered arcs/trade routes, not for selected markers
        const displayInfo = hoverInfo;
        if (!displayInfo) {
            card.style.opacity = '0'; card.style.pointerEvents = 'none';
            line.style.display = 'none';
            return;
        }
        const titleEl = card.querySelector('.globe-hover-title');
        const rows = card.querySelectorAll('.globe-hover-row');
        if (titleEl) titleEl.textContent = displayInfo.label;
        if (rows[0]) rows[0].textContent = displayInfo.extra || (displayInfo.type ? displayInfo.type.toUpperCase() : '');
        if (rows[1]) rows[1].textContent = displayInfo.lat != null ? displayInfo.lat.toFixed(2) + ', ' + displayInfo.lng.toFixed(2) : '';
        if (rows[2]) rows[2].textContent = displayInfo.weather || '';
        card.style.opacity = '1'; card.style.pointerEvents = 'auto';

        // Position the connecting line from hover point to the card
        const pointLat = hoverPointRef.current?.lat ?? displayInfo.lat;
        const pointLng = hoverPointRef.current?.lng ?? displayInfo.lng;

        if (pointLat != null && pointLng != null) {
            // Use actual mouse pixel position for line origin
            const screenX = mousePixelRef.current.x;
            const screenY = mousePixelRef.current.y;

            // Card position (top-right, 8px from edges, ~260px wide)
            const cardRight = container.clientWidth - 8;
            const cardWidth = 260;
            const cardTop = 16;
            const cardCenterX = cardRight - cardWidth / 2;
            const cardCenterY = cardTop + 40;

            // Calculate line from mouse to card, but stop 80px before the card
            const dx = cardCenterX - screenX;
            const dy = cardCenterY - screenY;
            const fullDist = Math.sqrt(dx * dx + dy * dy);
            const lineDist = Math.max(60, fullDist - 80);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI;

            line.style.left = screenX + 'px';
            line.style.top = screenY + 'px';
            line.style.width = lineDist + 'px';
            line.style.transform = 'rotate(' + angle + 'deg)';
            line.style.display = 'block';
        } else {
            line.style.display = 'none';
        }
    }, [hoverInfo]);

    const layerChips = ['weather', 'economic', 'events'].map(function (l) {
        const labels = { weather: 'Weather', economic: 'Economy', events: 'Events' };
        return React.createElement('button', { key: l, className: 'globe-layer-chip' + (activeLayer === l ? ' is-active' : ''), onClick: function () { setActiveLayer(function (prev) { return prev === l ? null : l; }); } }, labels[l]);
    });

    const timeline = activeLayer === 'economic' ? React.createElement('div', { className: 'globe-timeline' },
        React.createElement('input', { type: 'range', min: 2000, max: 2023, value: timeYear, className: 'globe-timeline-slider', onChange: function (e) { setTimeYear(Number(e.target.value)); } }),
        React.createElement('span', { className: 'globe-timeline-year' }, String(timeYear))
    ) : null;

    return React.createElement('section', { className: 'globe-frame', role: 'img', 'aria-label': 'Three dimensional globe layer' },
        React.createElement('div', { ref: statusChipRef, className: 'globe-status-chip' }, 'Strategic Mesh Online'),
        React.createElement('div', { ref: containerRef, className: 'globe-canvas' }),
        React.createElement('div', { ref: hoverLineRef, className: 'globe-hover-line', 'aria-hidden': 'true' }),
        React.createElement.apply(React, ['div', { className: 'globe-ui-overlay' }].concat(
            [React.createElement.apply(React, ['div', { className: 'globe-layer-chips' }].concat(layerChips))],
            timeline ? [timeline] : []
        )),
        React.createElement('div', { ref: hoverCardRef, className: 'globe-hover-card', 'aria-hidden': 'true', style: { opacity: 0, pointerEvents: 'none' } },
            React.createElement('div', { className: 'globe-hover-title' }),
            React.createElement('div', { className: 'globe-hover-row' }),
            React.createElement('div', { className: 'globe-hover-row' }),
            React.createElement('div', { className: 'globe-hover-row' })
        )
    );
}

function SlidePanel({ marker }) {
    const [webcam, setWebcam] = React.useState(null);
    const [webcamLoading, setWebcamLoading] = React.useState(false);
    React.useEffect(() => {
        if (!marker || !marker.lat || !marker.lon) { setWebcam(null); return; }
        setWebcamLoading(true);
        fetch(`/hud/webcam?lat=${marker.lat}&lon=${marker.lon}`)
            .then(res => res.ok ? res.json() : { webcams: [] })
            .then(data => {
                setWebcam((data.webcams && data.webcams.length) ? data.webcams[0] : null);
                setWebcamLoading(false);
            })
            .catch(() => { setWebcam(null); setWebcamLoading(false); });
    }, [marker]);
    return React.createElement(
        "aside",
        { className: `hud-slide-panel ${marker ? "is-open" : ""}`, "aria-live": "polite" },
        React.createElement("div", { className: "hud-panel-kicker" }, marker?.priority || "Awaiting selection"),
        React.createElement("div", { className: "hud-slide-title" }, marker?.label || "Marker Details"),
        React.createElement("div", { className: "hud-slide-sub" }, marker?.region || "Select a strategic node to inspect telemetry."),
        React.createElement("p", { className: "hud-slide-summary" }, marker?.status || "No telemetry selected."),
        React.createElement(
            "div",
            { className: "hud-stat-grid" },
            React.createElement("div", { className: "hud-stat-card" }, React.createElement("span", null, "Threat"), React.createElement("strong", null, marker?.threat || "n/a")),
            React.createElement("div", { className: "hud-stat-card" }, React.createElement("span", null, "Agents"), React.createElement("strong", null, String(marker?.agents ?? 0).padStart(2, "0"))),
            React.createElement("div", { className: "hud-stat-card" }, React.createElement("span", null, "Confidence"), React.createElement("strong", null, marker?.confidence || "n/a")),
            React.createElement("div", { className: "hud-stat-card" }, React.createElement("span", null, "Refresh"), React.createElement("strong", null, marker?.window || "n/a"))
        ),
        React.createElement("div", { className: "hud-panel-section-title" }, "Feed Stack"),
        React.createElement(
            "div",
            { className: "hud-chip-row" },
            ...(marker?.feeds || ["No feeds"]).map((item) => React.createElement("span", { key: item, className: "hud-info-chip" }, item))
        ),
        React.createElement("div", { className: "hud-panel-section-title" }, "Protocol Actions"),
        React.createElement(
            "div",
            { className: "hud-protocol-list" },
            ...(marker?.protocols || ["Awaiting command"]).map((item) => React.createElement("div", { key: item, className: "hud-protocol-item" }, item))
        ),
        React.createElement("div", { className: "hud-panel-section-title" }, "Live Webcam"),
        webcamLoading ? React.createElement("div", { className: "hud-webcam-loading" }, "Loading webcam...") :
            webcam ? React.createElement("iframe", {
                src: webcam.embedUrl,
                title: webcam.title,
                width: "100%",
                height: "220",
                style: { border: 0, borderRadius: "8px", background: "#111" },
                allow: "autoplay; encrypted-media"
            }) :
                React.createElement("div", { className: "hud-webcam-unavailable" }, "No live webcam available for this region."),
        React.createElement(
            "div",
            { className: "hud-slide-id" },
            marker ? `lat ${Number(marker.lat).toFixed(4)}, lon ${Number(marker.lon).toFixed(4)} • id ${marker.id}` : "id: none"
        )
    );
}

function CommandDeck({ marker }) {
    return React.createElement(
        "section",
        { className: "hud-command-deck" },
        React.createElement(MetricCard, { label: "Selected Node", value: marker.label, meta: marker.region }),
        React.createElement(MetricCard, { label: "Threat State", value: marker.threat, meta: `${marker.priority} / ${marker.confidence}`, tone: "rose" }),
        React.createElement(MetricCard, { label: "Active Feeds", value: String(marker.feeds.length).padStart(2, "0"), meta: marker.feeds.join(" • "), tone: "gold" }),
        React.createElement(MetricCard, { label: "Reaction Window", value: marker.window, meta: `${marker.agents} agents deployed` })
    );
}

const REGION_KEYWORDS = {
    hormuz: ["hormuz", "iran", "strait", "persian gulf", "tanker", "oil"],
    kabul: ["kabul", "afghanistan", "taliban", "afghan"],
    djibouti: ["djibouti", "bab el-mandeb", "red sea", "houthi", "yemen", "somalia"],
    singapore: ["singapore", "malacca", "south china sea", "asean", "taiwan"],
};

function useThreatLevels(markers) {
    const [threats, setThreats] = React.useState({});
    const [lastUpdated, setLastUpdated] = React.useState(null);

    const fetchAll = React.useCallback(async () => {
        const results = {};
        await Promise.all(markers.map(async (m) => {
            const keywords = (REGION_KEYWORDS[m.id] || [m.id]).join(",");
            try {
                const res = await fetch(`/hud/globe/threat?region=${m.id}&keywords=${encodeURIComponent(keywords)}`);
                if (!res.ok) return;
                const data = await res.json();
                results[m.id] = data;
            } catch (_) { }
        }));
        if (Object.keys(results).length > 0) {
            setThreats(results);
            setLastUpdated(new Date());
        }
    }, [markers]);

    React.useEffect(() => {
        fetchAll();
        const interval = setInterval(fetchAll, 15 * 60 * 1000);
        return () => clearInterval(interval);
    }, [fetchAll]);

    return { threats, lastUpdated, refresh: fetchAll };
}

function HudViewport() {
    const aircraft = useLiveAircraftData(10000); // poll every 10s
    const [selectedMarker, setSelectedMarker] = React.useState(GLOBE_MARKERS[0]);
    const [dialogueRows, setDialogueRows] = React.useState([]);
    const [dialogueLoading, setDialogueLoading] = React.useState(true);
    const [dialogueError, setDialogueError] = React.useState("");
    const liveLocation = useLiveLocation();
    const { threats, lastUpdated, refresh: refreshThreats } = useThreatLevels(GLOBE_MARKERS);

    const liveMarkers = React.useMemo(() => GLOBE_MARKERS.map(m => {
        const t = threats[m.id];
        if (!t) return m;
        return { ...m, threat: t.threat, confidence: t.confidence, _liveScore: t.score, _signals: t.signals };
    }), [threats]);

    const liveSelected = React.useMemo(() =>
        liveMarkers.find(m => m.id === selectedMarker.id) || selectedMarker,
        [liveMarkers, selectedMarker]
    );
    const alertSummary = React.useMemo(() => {
        const levelFor = (threat) => {
            const t = String(threat || "").toLowerCase();
            if (t.includes("critical")) return "critical";
            if (t.includes("elevated")) return "elevated";
            if (t.includes("guarded")) return "guarded";
            return "nominal";
        };
        const criticalCount = liveMarkers.filter((m) => levelFor(m.threat) === "critical").length;
        const elevatedCount = liveMarkers.filter((m) => levelFor(m.threat) === "elevated").length;
        const guardedCount = liveMarkers.filter((m) => levelFor(m.threat) === "guarded").length;
        const focusPriority = liveSelected && liveSelected.priority ? liveSelected.priority : "P3";
        const focusLabel = liveSelected && liveSelected.label ? liveSelected.label : "Unknown";

        if (criticalCount > 0) {
            return `${criticalCount} critical alert${criticalCount > 1 ? "s" : ""} • ${focusPriority} focus: ${focusLabel}`;
        }
        if (elevatedCount > 0) {
            return `${elevatedCount} elevated alert${elevatedCount > 1 ? "s" : ""} • ${focusPriority} focus: ${focusLabel}`;
        }
        if (guardedCount > 0) {
            return `${guardedCount} guarded region${guardedCount > 1 ? "s" : ""} • ${focusPriority} focus: ${focusLabel}`;
        }
        return `No critical alerts • ${focusPriority} focus: ${focusLabel}`;
    }, [liveMarkers, liveSelected]);
    const iso = new Date().toISOString();

    React.useEffect(() => {
        let cancelled = false;
        const loadDataset = async () => {
            try {
                const response = await fetch("/hud/react/data/april_27_dialogue.json");
                if (!response.ok) {
                    throw new Error(`dataset_http_${response.status}`);
                }
                const payload = await response.json();
                if (!cancelled) {
                    setDialogueRows(Array.isArray(payload.items) ? payload.items : []);
                    setDialogueError("");
                }
            } catch (_err) {
                if (!cancelled) {
                    setDialogueRows([]);
                    setDialogueError("Dataset unavailable");
                }
            } finally {
                if (!cancelled) {
                    setDialogueLoading(false);
                }
            }
        };

        loadDataset();
        return () => {
            cancelled = true;
        };
    }, []);

    const handleMarkerSelect = React.useCallback((marker) => {
        setSelectedMarker(marker);
    }, []);

    return React.createElement(
        "main",
        { className: "hud-shell" },
        React.createElement(
            "div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" } },
            React.createElement("div", { className: "hud-eyebrow" }, "Orbital command viewport"),
            React.createElement(
                "div", { style: { display: "flex", gap: "6px" } },
                React.createElement("a", { href: "/", style: { fontFamily: "monospace", fontSize: "10px", color: "rgba(255,255,255,0.4)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "20px", padding: "2px 10px", textDecoration: "none", letterSpacing: "0.04em" } }, "Approvals"),
                React.createElement("a", { href: "/hud/cc", style: { fontFamily: "monospace", fontSize: "10px", color: "rgba(255,255,255,0.4)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "20px", padding: "2px 10px", textDecoration: "none", letterSpacing: "0.04em" } }, "Command Center")
            )
        ),
        React.createElement("h1", { className: "hud-title" }, "Jarvis Strategic Globe"),
        React.createElement(
            "div", { style: { display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" } },
            React.createElement("p", { className: "hud-subline", style: { margin: 0 } }, "Live threat scoring via Reuters/BBC RSS — keyword signal analysis, refreshed every 15 min."),
            React.createElement("button", {
                onClick: refreshThreats,
                style: { fontFamily: "monospace", fontSize: "10px", color: "#22d3ee", background: "rgba(34,211,238,0.08)", border: "1px solid rgba(34,211,238,0.25)", borderRadius: "12px", padding: "2px 10px", cursor: "pointer", whiteSpace: "nowrap", letterSpacing: "0.06em" },
            }, "↻ Refresh"),
            lastUpdated && React.createElement("span", {
                style: { fontFamily: "monospace", fontSize: "10px", color: "rgba(255,255,255,0.3)", whiteSpace: "nowrap" }
            }, `updated ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`)
        ),
        React.createElement(CommandDeck, { marker: liveSelected }),
        React.createElement(
            "div",
            { className: "hud-theatre hud-theatre-cross" },
            React.createElement(
                "section",
                { className: "hud-side-column hud-left-column" },
                React.createElement(LiveNewsPanel),
                React.createElement(FinancialSocialMissionWidgets, { selectedMarker: liveSelected, liveLocation })
            ),
            React.createElement(
                "section",
                { className: "hud-main-column" },
                React.createElement(GlobeLayer, { onMarkerSelect: handleMarkerSelect, selectedMarkerId: liveSelected.id, selectedMarker: liveSelected, liveLocation, markers: liveMarkers, aircraft }),
                React.createElement(MarkerRibbon, {
                    markers: liveMarkers,
                    selectedId: liveSelected.id,
                    onSelect: handleMarkerSelect,
                }),
                React.createElement("div", { className: "hud-footnotes" }, `Node mesh: ${liveMarkers.map((item) => item.label).join(" • ")} • threat scored from live headlines`)
            ),
            React.createElement(
                "section",
                { className: "hud-side-column hud-right-column" },
                React.createElement(LiveLocationBadge, { liveLocation }),
                React.createElement(SlidePanel, { marker: liveSelected }),
                React.createElement(MarketHoursPanel)
            )
        ),
        React.createElement(
            "div",
            { className: "hud-footer" },
            React.createElement("span", null, `Loaded ${iso}`),
            React.createElement("span", { className: "hud-alert" }, alertSummary)
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) {
    createRoot(rootEl).render(React.createElement(HudViewport));
}
