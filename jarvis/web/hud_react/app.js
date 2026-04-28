import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import * as THREE from "https://esm.sh/three@0.167.1";

const GLOBE_MARKERS = [
    {
        id: "hormuz",
        label: "Strait of Hormuz",
        lat: 25.578,
        lon: 56.610,
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
    // Add other marker objects as needed
];

const GLOBE_CONNECTIONS = [
    ["hormuz", "djibouti"],
    ["hormuz", "singapore"],
    ["kabul", "djibouti"],
    ["kabul", "singapore"],
];

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
            { lat: 6.0, lon: 96.5 },         // Malacca approach
            { lat: 12.6, lon: 43.35 },       // Bab el-Mandeb
            { lat: 29.9, lon: 32.55 },       // Suez
            { lat: 36.0, lon: 14.5 },        // Central Med
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
            { lat: 25.58, lon: 56.61 },      // Hormuz
            { lat: 19.0, lon: 67.0 },        // Arabian Sea
            { lat: 13.0, lon: 80.3 },        // Chennai lane
            { lat: 6.0, lon: 96.5 },         // Malacca
            { lat: 1.29, lon: 103.85 },      // Singapore
            { lat: 22.32, lon: 114.17 },     // Hong Kong / PRD
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
        chokepoints: ["Caribbean approach", "Panama Canal"],
        waypoints: [
            { lat: 31.23, lon: 121.47 },     // Shanghai
            { lat: 24.8, lon: 141.0 },       // Pacific crossing
            { lat: 17.8, lon: -79.7 },       // Caribbean approach
            { lat: 9.08, lon: -79.68 },      // Panama Canal
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
            { lat: -6.0, lon: 76.0 },        // Indian Ocean south lane
            { lat: -34.35, lon: 18.47 },     // Cape Town
            { lat: -5.0, lon: 5.0 },         // South Atlantic turn
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

// Convert "wall-clock minutes since midnight in tz on day offset" to a UTC ms.
// We use the IANA tz current offset (good enough for status displays — drifts only across the precise DST transition minute).
function tzWallClockToUTCms(referenceDate, tz, dayOffset, hour, minute) {
    // referenceDate "now" -> local parts in tz on the current day
    const nowLocal = localPartsInTZ(referenceDate, tz);
    // build a UTC Date at the same y/m/d/h/mi/s; the diff to referenceDate gives the tz offset.
    const asIfUTC = Date.UTC(nowLocal.y, nowLocal.m - 1, nowLocal.d, nowLocal.h, nowLocal.mi, nowLocal.s);
    const tzOffsetMs = asIfUTC - referenceDate.getTime();
    // target wall clock = today's local midnight + dayOffset days + hour:minute
    const localMidnightUTC = Date.UTC(nowLocal.y, nowLocal.m - 1, nowLocal.d, 0, 0, 0);
    return localMidnightUTC + dayOffset * 86400000 + hour * 3600000 + minute * 60000 - tzOffsetMs;
}

function getMarketStatus(market, now) {
    const local = localPartsInTZ(now, market.tz);
    const openTodayUTC = tzWallClockToUTCms(now, market.tz, 0, market.openH, market.openM);
    const closeTodayUTC = tzWallClockToUTCms(now, market.tz, 0, market.closeH, market.closeM);
    const isTradingDay = market.daysOpen.includes(local.dow);
    const nowMs = now.getTime();

    if (isTradingDay && nowMs >= openTodayUTC && nowMs < closeTodayUTC) {
        return { open: true, label: "OPEN", deltaMs: closeTodayUTC - nowMs, deltaLabel: "closes in" };
    }
    // find next open within next 8 days
    for (let offset = 0; offset < 8; offset += 1) {
        const probeDow = (local.dow + offset) % 7;
        const probeOpenUTC = tzWallClockToUTCms(now, market.tz, offset, market.openH, market.openM);
        if (market.daysOpen.includes(probeDow) && probeOpenUTC > nowMs) {
            return { open: false, label: "CLOSED", deltaMs: probeOpenUTC - nowMs, deltaLabel: "opens in" };
        }
    }
    return { open: false, label: "CLOSED", deltaMs: 0, deltaLabel: "opens in" };
}

function formatHMS(ms) {
    if (ms <= 0) return "00:00:00";
    const total = Math.floor(ms / 1000);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function formatMarketLocalClock(tz) {
    return new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
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
    const [now, setNow] = React.useState(() => new Date());
    React.useEffect(() => {
        const t = window.setInterval(() => setNow(new Date()), 1000);
        return () => window.clearInterval(t);
    }, []);

    const enriched = MARKETS.map((m) => ({ market: m, status: getMarketStatus(m, now) }));
    const openCount = enriched.filter((row) => row.status.open).length;

    return React.createElement(
        "section",
        { className: "hud-market-panel", "aria-label": "Global market hours" },
        React.createElement(
            "div",
            { className: "hud-market-header" },
            React.createElement("div", { className: "hud-market-title" }, "Global Market Hours"),
            React.createElement("div", { className: "hud-market-meta" }, `${openCount} / ${MARKETS.length} open • UTC ${now.toISOString().slice(11, 19)}`)
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
                        React.createElement("span", { className: "hud-market-city" }, `${market.city} • ${formatMarketLocalClock(market.tz)} local`)
                    ),
                    React.createElement(
                        "div",
                        { className: "hud-market-status" },
                        React.createElement("span", { className: "hud-market-state" }, status.label),
                        React.createElement("span", { className: "hud-market-countdown" }, `${status.deltaLabel} ${formatHMS(status.deltaMs)}`)
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

function GlobeLayer({ onMarkerSelect, selectedMarkerId, liveLocation }) {
    const containerRef = React.useRef(null);
    const statusChipRef = React.useRef(null);
    const hoverCardRef = React.useRef(null);
    const hoverLineRef = React.useRef(null);
    const hoverTitleRef = React.useRef(null);
    const hoverPopRef = React.useRef(null);
    const hoverCoordsRef = React.useRef(null);
    const hoverWeatherRef = React.useRef(null);

    React.useEffect(() => {
        const container = containerRef.current;
        if (!container) {
            return undefined;
        }

        const width = Math.max(300, container.clientWidth || 300);
        const height = Math.max(360, container.clientHeight || 360);
        const selectedMarker = GLOBE_MARKERS.find((marker) => marker.id === selectedMarkerId) || GLOBE_MARKERS[0];

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
        camera.position.set(0, 0.18, 3.6);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
        renderer.setSize(width, height);
        container.appendChild(renderer.domElement);

        // --- Camera zoom + orbit state (hacker-movie satellite -> wireframe) ---
        const ZOOM_MIN = 0.70;     // closest: near-atmosphere dive
        const ZOOM_MAX = 18.00;    // farthest: wide solar-system framing (supports distant dwarfs)
        const ZOOM_DEFAULT = 4.20;
        const cameraState = {
            distance: ZOOM_DEFAULT,
            targetDistance: ZOOM_DEFAULT,
            yaw: 0,
            pitch: 0.05,
            targetYaw: 0,
            targetPitch: 0.05,
            userActive: false,
            lastInteractionAt: 0,
        };
        const movementState = {
            rootSpin: 0.00012,
            targetRootSpin: 0.00012,
            inertiaYaw: 0,
            inertiaPitch: 0,
            lastFrameAt: performance.now(),
            driftPhase: Math.random() * Math.PI * 2,
        };

        renderer.domElement.style.touchAction = "none";
        renderer.domElement.style.cursor = "grab";

        const onWheel = (event) => {
            event.preventDefault();
            const delta = event.deltaY;
            const factor = Math.exp(delta * 0.0015);
            cameraState.targetDistance = Math.min(
                ZOOM_MAX,
                Math.max(ZOOM_MIN, cameraState.targetDistance * factor)
            );
            cameraState.userActive = true;
            cameraState.lastInteractionAt = performance.now();
        };
        renderer.domElement.addEventListener("wheel", onWheel, { passive: false });

        let dragState = null;
        const onPointerDown = (event) => {
            renderer.domElement.setPointerCapture(event.pointerId);
            renderer.domElement.style.cursor = "grabbing";
            hideHover();
            dragState = {
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                lastX: event.clientX,
                lastY: event.clientY,
                startYaw: cameraState.targetYaw,
                startPitch: cameraState.targetPitch,
                moved: false,
            };
            movementState.inertiaYaw = 0;
            movementState.inertiaPitch = 0;
        };
        const onPointerMove = (event) => {
            if (dragState && event.pointerId === dragState.pointerId) {
                const dx = event.clientX - dragState.startX;
                const dy = event.clientY - dragState.startY;
                const stepDx = event.clientX - dragState.lastX;
                const stepDy = event.clientY - dragState.lastY;
                if (Math.abs(dx) + Math.abs(dy) > 4) dragState.moved = true;
                // MIRRORED: invert direction for both axes
                cameraState.targetYaw = dragState.startYaw - dx * 0.005;
                cameraState.targetPitch = dragState.startPitch - dy * 0.005;
                movementState.inertiaYaw = THREE.MathUtils.clamp(-stepDx * 0.00085, -0.05, 0.05);
                movementState.inertiaPitch = THREE.MathUtils.clamp(-stepDy * 0.00085, -0.05, 0.05);
                dragState.lastX = event.clientX;
                dragState.lastY = event.clientY;
                cameraState.userActive = true;
                cameraState.lastInteractionAt = performance.now();
                return;
            }
            updateHoverFromPointer(event);
        };
        const onPointerUp = (event) => {
            if (!dragState || event.pointerId !== dragState.pointerId) return;
            try { renderer.domElement.releasePointerCapture(event.pointerId); } catch (_) { /* noop */ }
            renderer.domElement.style.cursor = "grab";
            const wasDrag = dragState.moved;
            dragState = null;
            // Add inertial continuation when user releases after a real drag.
            if (wasDrag) {
                cameraState.targetYaw += movementState.inertiaYaw * 16;
                cameraState.targetPitch += movementState.inertiaPitch * 16;
                cameraState.lastInteractionAt = performance.now();
            }
            // suppress click marker selection if it was actually a drag
            if (wasDrag) {
                event.stopPropagation();
            }
        };
        renderer.domElement.addEventListener("pointerdown", onPointerDown);
        renderer.domElement.addEventListener("pointermove", onPointerMove);
        renderer.domElement.addEventListener("pointerup", onPointerUp);
        renderer.domElement.addEventListener("pointercancel", onPointerUp);

        const root = new THREE.Group();
        scene.add(root);

        // Real Earth satellite texture (NASA Blue Marble via three.js examples CDN).
        // Falls back gracefully to the deep-blue base color if loading fails.
        const earthMaterial = new THREE.MeshPhongMaterial({
            color: 0x0c1f33,
            emissive: 0x000000,
            emissiveIntensity: 0.06,
            transparent: false,
            opacity: 1.0,
            shininess: 22,
            specular: new THREE.Color(0x1a2a3a),
        });

        const textureLoader = new THREE.TextureLoader();
        textureLoader.setCrossOrigin("anonymous");
        const TEX_BASE = "https://threejs.org/examples/textures/planets/";
        // Higher-res 4K Blue Marble (NASA via three-globe CDN). Falls back to 2048 atlas if blocked.
        const HIRES_DAY = "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";
        textureLoader.load(
            HIRES_DAY,
            (tex) => {
                if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
                tex.anisotropy = renderer.capabilities.getMaxAnisotropy?.() || 4;
                earthMaterial.map = tex;
                earthMaterial.color.setHex(0xffffff);
                earthMaterial.emissive.setHex(0x000000);
                earthMaterial.emissiveIntensity = 0.05;
                earthMaterial.needsUpdate = true;
            },
            undefined,
            () => {
                // Fallback to threejs 2048 atlas if 4K is blocked
                textureLoader.load(`${TEX_BASE}earth_atmos_2048.jpg`, (tex) => {
                    earthMaterial.map = tex;
                    earthMaterial.color.setHex(0xffffff);
                    earthMaterial.emissive.setHex(0x000000);
                    earthMaterial.emissiveIntensity = 0.05;
                    earthMaterial.needsUpdate = true;
                });
            }
        );
        textureLoader.load(`${TEX_BASE}earth_specular_2048.jpg`, (tex) => {
            earthMaterial.specularMap = tex;
            // Slight blue tint on ocean specular for realistic water glint, kept dim.
            earthMaterial.specular = new THREE.Color(0x335577);
            earthMaterial.shininess = 28;
            earthMaterial.needsUpdate = true;
        });
        textureLoader.load(`${TEX_BASE}earth_normal_2048.jpg`, (tex) => {
            earthMaterial.normalMap = tex;
            earthMaterial.normalScale = new THREE.Vector2(0.7, 0.7);
            earthMaterial.needsUpdate = true;
        });

        // Night-side city lights with a real sun-direction mask (no camo bleed).
        // Updated each frame from the live sub-solar point.
        const nightMaterial = new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            uniforms: {
                nightMap: { value: null },
                sunDir: { value: new THREE.Vector3(1, 0, 0) },
                opacity: { value: 0.0 },
                tint: { value: new THREE.Color(0xffd9a0) },
            },
            vertexShader: `
                varying vec3 vNormal;
                varying vec2 vUv;
                void main() {
                    vNormal = normalize(normal);
                    vUv = uv;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform sampler2D nightMap;
                uniform vec3 sunDir;
                uniform float opacity;
                uniform vec3 tint;
                varying vec3 vNormal;
                varying vec2 vUv;
                void main() {
                    float d = dot(normalize(vNormal), normalize(sunDir));
                    // 1.0 on the dark side, smoothly fading across the terminator,
                    // 0.0 on the day side. Negative d = facing away from the sun.
                    float nightMask = smoothstep(0.10, -0.15, d);
                    vec3 lights = texture2D(nightMap, vUv).rgb * tint;
                    gl_FragColor = vec4(lights * nightMask, nightMask * opacity);
                }
            `,
        });
        textureLoader.load(
            "https://unpkg.com/three-globe/example/img/earth-night.jpg",
            (tex) => {
                if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
                nightMaterial.uniforms.nightMap.value = tex;
                nightMaterial.uniforms.opacity.value = 1.0;
                nightMaterial.needsUpdate = true;
            },
            undefined,
            () => { /* offline / blocked — silent fallback */ }
        );

        const coreSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.02, 96, 96),
            earthMaterial
        );
        root.add(coreSphere);
        // Earth's axial tilt at the root group — markers, clouds, night side and
        // wireframe all share this tilt because they're children of `root`.
        root.rotation.z = (23.5 * Math.PI) / 180;

        // Earth's Moon around the primary globe (Earth is the main sphere).
        const earthMoonPivot = new THREE.Group();
        const earthMoonMaterial = new THREE.MeshStandardMaterial({
            color: 0xd6dce4,
            roughness: 1.0,
            metalness: 0.0,
            emissive: 0x07090c,
            emissiveIntensity: 0.03,
        });
        const earthMoon = new THREE.Mesh(
            new THREE.SphereGeometry(0.07, 24, 24),
            earthMoonMaterial
        );
        earthMoon.position.set(1.62, 0.06, 0);
        earthMoonPivot.add(earthMoon);
        root.add(earthMoonPivot);
        textureLoader.load(`${TEX_BASE}moon_1024.jpg`, (tex) => {
            if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
            earthMoonMaterial.map = tex;
            earthMoonMaterial.needsUpdate = true;
        });
        earthMoon.userData.planetEgg = {
            name: "Moon",
            category: "Moon",
            temp: "-173°C to 127°C",
            wind: "No atmosphere",
            pop: "0",
            distanceAuMin: 0.00257,
            distanceAuMax: 0.00257,
        };
        earthMoon.userData.isPlanet = true;

        // Cloud layer — adds parallax + realism over the satellite imagery
        const cloudMaterial = new THREE.MeshPhongMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.0,
            depthWrite: false,
        });
        const cloudSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.035, 64, 64),
            cloudMaterial
        );
        root.add(cloudSphere);
        cloudSphere.visible = false;

        const nightSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.022, 96, 96),
            nightMaterial
        );
        root.add(nightSphere);

        // Atmosphere — Fresnel-style glow on the limb
        const atmosphereMaterial = new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            side: THREE.BackSide,
            uniforms: {
                glowColor: { value: new THREE.Color(0x4b9ed0) },
                power: { value: 3.2 },
                intensity: { value: 0.34 },
            },
            vertexShader: `
                varying vec3 vNormal;
                varying vec3 vViewDir;
                void main() {
                    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                    vNormal = normalize(normalMatrix * normal);
                    vViewDir = normalize(-mvPosition.xyz);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                varying vec3 vNormal;
                varying vec3 vViewDir;
                uniform vec3 glowColor;
                uniform float power;
                uniform float intensity;
                void main() {
                    float fres = pow(1.0 - max(dot(vNormal, vViewDir), 0.0), power);
                    gl_FragColor = vec4(glowColor, fres * intensity);
                }
            `,
        });
        const atmosphereSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.085, 64, 64),
            atmosphereMaterial
        );
        // Atmosphere should not tilt with the planet (sits on the camera-facing limb)
        scene.add(atmosphereSphere);

        const wireSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.06, 48, 48),
            new THREE.MeshBasicMaterial({
                color: 0x5bc8ff,
                wireframe: true,
                transparent: true,
                opacity: 0,
            })
        );
        root.add(wireSphere);

        const cityScanGroup = new THREE.Group();
        cityScanGroup.visible = false;
        root.add(cityScanGroup);

        const cityScanFloor = new THREE.Mesh(
            new THREE.CircleGeometry(0.22, 24),
            new THREE.MeshBasicMaterial({
                color: 0x5bc8ff,
                wireframe: true,
                transparent: true,
                opacity: 0,
                depthWrite: false,
            })
        );
        cityScanFloor.rotation.x = -Math.PI / 2;
        cityScanGroup.add(cityScanFloor);

        const cityScanBuildings = [
            { x: 0.0, z: 0.0, w: 0.034, d: 0.034, h: 0.23 },
            { x: -0.055, z: -0.02, w: 0.026, d: 0.026, h: 0.16 },
            { x: 0.06, z: -0.03, w: 0.03, d: 0.03, h: 0.14 },
            { x: -0.02, z: 0.065, w: 0.028, d: 0.028, h: 0.12 },
            { x: 0.075, z: 0.055, w: 0.02, d: 0.02, h: 0.09 },
            { x: -0.082, z: 0.048, w: 0.024, d: 0.024, h: 0.11 },
        ].map((spec) => {
            const mesh = new THREE.Mesh(
                new THREE.BoxGeometry(spec.w, spec.h, spec.d),
                new THREE.MeshBasicMaterial({
                    color: 0x7edaff,
                    wireframe: true,
                    transparent: true,
                    opacity: 0,
                    depthWrite: false,
                })
            );
            mesh.position.set(spec.x, spec.h * 0.5, spec.z);
            cityScanGroup.add(mesh);
            return mesh;
        });

        const cityScanPulse = new THREE.Mesh(
            new THREE.RingGeometry(0.08, 0.11, 40),
            new THREE.MeshBasicMaterial({
                color: 0x9be3ff,
                transparent: true,
                opacity: 0,
                side: THREE.DoubleSide,
                depthWrite: false,
            })
        );
        cityScanPulse.rotation.x = -Math.PI / 2;
        cityScanPulse.position.y = 0.003;
        cityScanGroup.add(cityScanPulse);

        const CITY_SCAN_MARKERS = new Set(["Singapore", "Kabul", "Djibouti", "Tongeren"]);
        let cityInspectionTarget = null;
        const setCityInspectionTarget = (target) => {
            cityInspectionTarget = target;
            cityScanGroup.visible = Boolean(target);
            if (!target) return;
            const normal = latLonToVector3(target.lat, target.lon, 1.0).normalize();
            cityScanGroup.position.copy(normal.clone().multiplyScalar(1.045));
            cityScanGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
        };

        const glowSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.1, 48, 48),
            new THREE.MeshBasicMaterial({
                color: 0x62d8ff,
                transparent: true,
                opacity: 0.018,
                side: THREE.BackSide,
            })
        );
        root.add(glowSphere);

        scene.add(new THREE.AmbientLight(0xffffff, 0.28));
        const fillLight = new THREE.HemisphereLight(0xb8d8ff, 0x0b1424, 0.24);
        scene.add(fillLight);
        const sunLight = new THREE.DirectionalLight(0xfff4d6, 2.0);
        sunLight.position.set(4.0, 2.0, 3.5);
        scene.add(sunLight);

        // Visible sun body + halo for a clearer solar-system feel.
        const sunGroup = new THREE.Group();
        const sunCore = new THREE.Mesh(
            new THREE.SphereGeometry(0.56, 40, 40),
            new THREE.MeshBasicMaterial({ color: 0xffd27a })
        );
        const sunHalo = new THREE.Mesh(
            new THREE.SphereGeometry(1.24, 32, 32),
            new THREE.MeshBasicMaterial({
                color: 0xffb347,
                transparent: true,
                opacity: 0.24,
                side: THREE.BackSide,
                depthWrite: false,
            })
        );
        sunGroup.add(sunHalo);
        sunGroup.add(sunCore);
        scene.add(sunGroup);

        const sunEasterEgg = {
            name: "Sun",
            category: "Star",
            temp: "5,500°C surface",
            wind: "Solar wind ~400 km/s",
            pop: "0",
            distanceAuMin: 1.0,
            distanceAuMax: 1.0,
        };
        sunCore.userData.planetEgg = sunEasterEgg;
        sunCore.userData.isPlanet = true;
        sunHalo.userData.planetEgg = sunEasterEgg;
        sunHalo.userData.isPlanet = true;

        // Real-time sun direction: place the directional light at the actual sub-solar point
        // so the day/night terminator on the globe matches reality.
        const updateSunFromClock = () => {
            const now = new Date();
            const startOfYear = Date.UTC(now.getUTCFullYear(), 0, 0);
            const dayOfYear = Math.floor((now.getTime() - startOfYear) / 86400000);
            // Solar declination (degrees)
            const decl = 23.44 * Math.sin(((360 / 365) * (dayOfYear - 81) * Math.PI) / 180);
            // Subsolar longitude (degrees east): noon at 0° longitude when UTC = 12:00.
            // Sun moves WEST at 15°/hour, so subsolar lon = -(UTC_hours - 12) * 15.
            const utcHours = now.getUTCHours() + now.getUTCMinutes() / 60 + now.getUTCSeconds() / 3600;
            const subsolarLon = -(utcHours - 12) * 15;
            const sunDir = latLonToVector3(decl, subsolarLon, 8);
            // Apply the same axial tilt that's on `root` so day/night aligns with the rotated Earth.
            sunDir.applyEuler(new THREE.Euler(0, 0, root.rotation.z));
            sunLight.position.copy(sunDir);
            sunGroup.position.copy(sunDir.clone().normalize().multiplyScalar(10.8));
        };
        updateSunFromClock();
        const rimLight = new THREE.PointLight(0x5bc8ff, 0.18, 14);
        rimLight.position.set(-4.4, 1.5, -3.2);
        scene.add(rimLight);
        const pinkLight = new THREE.PointLight(0xff6688, 0.08, 9);
        pinkLight.position.set(-3.4, -1.5, 2.5);
        scene.add(pinkLight);

        const gridMaterial = new THREE.LineBasicMaterial({ color: 0x4fc8ff, transparent: true, opacity: 0.18 });
        const makeLoop = (points) => new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), gridMaterial);

        [-50, -20, 10, 36, 62].forEach((latDeg) => {
            const radius = Math.cos((latDeg * Math.PI) / 180) * 1.09;
            const y = Math.sin((latDeg * Math.PI) / 180) * 1.09;
            const points = [];
            for (let i = 0; i <= 96; i += 1) {
                const theta = (i / 96) * Math.PI * 2;
                points.push(new THREE.Vector3(Math.cos(theta) * radius, y, Math.sin(theta) * radius));
            }
            root.add(makeLoop(points));
        });

        [0, 36, 72, 108, 144].forEach((lonDeg) => {
            const points = [];
            for (let i = 0; i <= 96; i += 1) {
                const lat = ((i / 96) * Math.PI) - Math.PI / 2;
                const lon = (lonDeg * Math.PI) / 180;
                points.push(new THREE.Vector3(
                    1.09 * Math.cos(lat) * Math.sin(lon),
                    1.09 * Math.sin(lat),
                    1.09 * Math.cos(lat) * Math.cos(lon)
                ));
            }
            root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), gridMaterial));
        });

        // Milky Way starfield: dense band of colored stars on a far background sphere.
        const starGeometry = new THREE.BufferGeometry();
        const starData = [];
        const starColors = [];
        const STAR_COUNT = 3400;
        const tmpColor = new THREE.Color();
        for (let i = 0; i < STAR_COUNT; i += 1) {
            // Concentrate ~70% of stars near a great-circle band (the galactic plane)
            // to give the Milky Way streak a visible density gradient.
            const inBand = Math.random() < 0.7;
            const bandSpread = inBand ? (Math.random() - 0.5) * 0.45 : (Math.random() - 0.5) * 2;
            const theta = Math.PI / 2 + bandSpread;
            const phi = Math.random() * Math.PI * 2;
            const radius = 18 + Math.random() * 6;
            // Tilt the band ~25° so it cuts across the scene at a cinematic angle
            const x0 = radius * Math.sin(theta) * Math.cos(phi);
            const y0 = radius * Math.cos(theta);
            const z0 = radius * Math.sin(theta) * Math.sin(phi);
            const tilt = (25 * Math.PI) / 180;
            const x = x0;
            const y = y0 * Math.cos(tilt) - z0 * Math.sin(tilt);
            const z = y0 * Math.sin(tilt) + z0 * Math.cos(tilt);
            starData.push(x, y, z);
            // Slight color variation: cool blue, warm white, faint amber
            const hueRoll = Math.random();
            if (hueRoll < 0.55) tmpColor.setHSL(0.58, 0.4, 0.78 + Math.random() * 0.2);
            else if (hueRoll < 0.85) tmpColor.setHSL(0.10, 0.25, 0.85 + Math.random() * 0.15);
            else tmpColor.setHSL(0.95, 0.35, 0.70 + Math.random() * 0.2);
            starColors.push(tmpColor.r, tmpColor.g, tmpColor.b);
        }
        starGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starData, 3));
        starGeometry.setAttribute("color", new THREE.Float32BufferAttribute(starColors, 3));
        const stars = new THREE.Points(
            starGeometry,
            new THREE.PointsMaterial({
                size: 0.05,
                transparent: true,
                opacity: 0.82,
                vertexColors: true,
                sizeAttenuation: true,
                depthWrite: false,
            })
        );
        scene.add(stars);

        // Brighter foreground stars for depth and more cinematic detail.
        const brightGeometry = new THREE.BufferGeometry();
        const brightData = [];
        const brightColors = [];
        for (let i = 0; i < 520; i += 1) {
            const theta = Math.acos(2 * Math.random() - 1);
            const phi = Math.random() * Math.PI * 2;
            const radius = 14 + Math.random() * 8;
            const x = radius * Math.sin(theta) * Math.cos(phi);
            const y = radius * Math.cos(theta);
            const z = radius * Math.sin(theta) * Math.sin(phi);
            brightData.push(x, y, z);
            const hueRoll = Math.random();
            if (hueRoll < 0.45) tmpColor.setHSL(0.58, 0.35, 0.88);
            else if (hueRoll < 0.75) tmpColor.setHSL(0.12, 0.20, 0.90);
            else tmpColor.setHSL(0.95, 0.28, 0.82);
            brightColors.push(tmpColor.r, tmpColor.g, tmpColor.b);
        }
        brightGeometry.setAttribute("position", new THREE.Float32BufferAttribute(brightData, 3));
        brightGeometry.setAttribute("color", new THREE.Float32BufferAttribute(brightColors, 3));
        const starsBright = new THREE.Points(
            brightGeometry,
            new THREE.PointsMaterial({
                size: 0.1,
                transparent: true,
                opacity: 0.95,
                vertexColors: true,
                sizeAttenuation: true,
                depthWrite: false,
            })
        );
        scene.add(starsBright);

        // Decorative orbiting planets (not interactive, no raycast).
        // They live on tilted orbital rings far behind the globe.
        // Stylized relative scale anchored to Earth at the globe origin.
        // Planet direction is computed from simple heliocentric circular orbits and
        // then converted to geocentric vectors (planet minus Earth).
        const AU_VISIBILITY_SCALE = 2.15;
        const AU_VISIBILITY_CURVE = 1.8;
        const ORBIT_EPOCH_MS = Date.UTC(2000, 0, 1, 12, 0, 0); // J2000
        const EARTH_ORBIT = { au: 1.0, periodDays: 365.256, meanLonDeg: 100.46435 };
        const planetSpecs = [
            { color: 0xb98a5b, radius: 0.08, au: 0.39, periodDays: 87.969, meanLonDeg: 252.251, spinSpeed: 0.00045, tilt: 0.05, tex: "mercury.jpg", roughness: 0.95, bumpTex: "mercury.jpg", bumpScale: 0.028, moons: 0 },   // Mercury
            { color: 0xd9a86a, radius: 0.17, au: 0.72, periodDays: 224.701, meanLonDeg: 181.980, spinSpeed: 0.00031, tilt: 0.10, tex: "venus.jpg", roughness: 0.92, detailShell: true, shellOpacity: 0.16, moons: 0 },     // Venus
            { color: 0xc1573b, radius: 0.10, au: 1.52, periodDays: 686.980, meanLonDeg: 355.453, spinSpeed: 0.00022, tilt: 0.18, tex: "mars_1k_color.jpg", roughness: 0.90, normalTex: "mars_1k_normal.jpg", normalScale: 0.9, bumpTex: "mars_1k_color.jpg", bumpScale: 0.02, moons: 2 }, // Mars
            { color: 0xd8b89a, radius: 0.52, au: 5.20, periodDays: 4332.59, meanLonDeg: 34.404, spinSpeed: 0.00014, tilt: 0.04, tex: "jupiter.jpg", roughness: 0.85, detailShell: true, shellOpacity: 0.20, moons: 4 },   // Jupiter
            { color: 0xe7d28c, radius: 0.44, au: 9.58, periodDays: 10759.22, meanLonDeg: 49.944, spinSpeed: 0.00010, tilt: 0.22, tex: "saturn.jpg", roughness: 0.88, ring: true, detailShell: true, shellOpacity: 0.18, moons: 3 }, // Saturn
            { color: 0x9ec9ff, radius: 0.25, au: 19.2, periodDays: 30688.5, meanLonDeg: 313.232, spinSpeed: 0.00007, tilt: 0.15, tex: "uranus.jpg", roughness: 0.90, ring: true, ringTint: 0xbfd7e6, moons: 2 },    // Uranus
            { color: 0x5b8dff, radius: 0.24, au: 30.05, periodDays: 60195, meanLonDeg: 304.880, spinSpeed: 0.00005, tilt: 0.08, tex: "neptune.jpg", roughness: 0.90, detailShell: true, shellOpacity: 0.12, moons: 2 },   // Neptune
            { color: 0xdbc3a6, radius: 0.07, au: 39.48, periodDays: 90560, meanLonDeg: 238.929, spinSpeed: 0.000035, tilt: 0.12, tex: "pluto.jpg", roughness: 0.96, bumpTex: "moon_1024.jpg", bumpScale: 0.012, moons: 1 },    // Pluto (dwarf)
            { color: 0xb9b6b2, radius: 0.06, au: 2.77, periodDays: 1680.0, meanLonDeg: 80.3, spinSpeed: 0.000040, tilt: 0.08, tex: "moon_1024.jpg", roughness: 0.98, bumpTex: "moon_1024.jpg", bumpScale: 0.014, moons: 0 }, // Ceres (dwarf)
            { color: 0xcdd7e6, radius: 0.06, au: 67.7, periodDays: 204400, meanLonDeg: 204.2, spinSpeed: 0.000024, tilt: 0.10, tex: "moon_1024.jpg", roughness: 0.98, bumpTex: "moon_1024.jpg", bumpScale: 0.014, moons: 0 }, // Eris (dwarf)
            { color: 0xdccdb3, radius: 0.055, au: 43.1, periodDays: 103500, meanLonDeg: 122.0, spinSpeed: 0.000022, tilt: 0.14, tex: "moon_1024.jpg", roughness: 0.98, bumpTex: "moon_1024.jpg", bumpScale: 0.013, moons: 0 }, // Haumea (dwarf)
            { color: 0xe6d9bd, radius: 0.058, au: 45.8, periodDays: 112900, meanLonDeg: 152.0, spinSpeed: 0.000021, tilt: 0.09, tex: "moon_1024.jpg", roughness: 0.98, bumpTex: "moon_1024.jpg", bumpScale: 0.013, moons: 0 }, // Makemake
        ];
        const heliocentricPos = (au, periodDays, meanLonDeg, nowMs) => {
            const daysSinceEpoch = (nowMs - ORBIT_EPOCH_MS) / 86400000;
            const angleDeg = (meanLonDeg + (daysSinceEpoch / periodDays) * 360) % 360;
            const angle = (angleDeg * Math.PI) / 180;
            return new THREE.Vector3(Math.cos(angle) * au, 0, Math.sin(angle) * au);
        };
        const compressAuDistance = (auDistance) => Math.log1p(Math.abs(auDistance) * AU_VISIBILITY_CURVE) * AU_VISIBILITY_SCALE;
        const loadPlanetTexture = (file, onLoad) => {
            if (!file) return;
            textureLoader.load(
                `${TEX_BASE}${file}`,
                (tex) => {
                    if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
                    tex.anisotropy = renderer.capabilities.getMaxAnisotropy?.() || 4;
                    onLoad(tex);
                },
                undefined,
                () => { /* silent fallback: keep base color */ }
            );
        };
        const planetEasterEggs = [
            { name: "Mercury", category: "Planet", temp: "-173°C to 427°C", wind: "0 m/s", pop: "0", distanceAuMin: 0.61, distanceAuMax: 1.39 },
            { name: "Venus", category: "Planet", temp: "462°C", wind: "360 km/h", pop: "600 Marshins", distanceAuMin: 0.28, distanceAuMax: 1.72 },
            { name: "Mars", category: "Planet", temp: "-63°C avg", wind: "5 m/s", pop: "1200 Martians", distanceAuMin: 0.37, distanceAuMax: 2.68 },
            { name: "Jupiter", category: "Planet", temp: "-108°C", wind: "620 km/h", pop: "60,000 Selenites", distanceAuMin: 3.95, distanceAuMax: 6.45 },
            { name: "Saturn", category: "Planet", temp: "-139°C", wind: "1800 km/h", pop: "9000 Ringlings", distanceAuMin: 8.00, distanceAuMax: 11.05 },
            { name: "Uranus", category: "Planet", temp: "-197°C", wind: "900 km/h", pop: "3000 Icefolk", distanceAuMin: 17.20, distanceAuMax: 21.10 },
            { name: "Neptune", category: "Planet", temp: "-201°C", wind: "2100 km/h", pop: "6000 Deepsea", distanceAuMin: 28.80, distanceAuMax: 30.40 },
            { name: "Pluto", category: "Dwarf Planet", temp: "-229°C", wind: "Thin atmosphere", pop: "0", distanceAuMin: 29.70, distanceAuMax: 49.30 },
            { name: "Ceres", category: "Dwarf Planet", temp: "-105°C", wind: "No atmosphere", pop: "0", distanceAuMin: 1.60, distanceAuMax: 4.60 },
            { name: "Eris", category: "Dwarf Planet", temp: "-231°C", wind: "No atmosphere", pop: "0", distanceAuMin: 37.80, distanceAuMax: 97.60 },
            { name: "Haumea", category: "Dwarf Planet", temp: "-223°C", wind: "No atmosphere", pop: "0", distanceAuMin: 34.90, distanceAuMax: 51.50 },
            { name: "Makemake", category: "Dwarf Planet", temp: "-239°C", wind: "No atmosphere", pop: "0", distanceAuMin: 38.50, distanceAuMax: 52.80 },
        ];
        const setSpaceInteraction = (object3d, egg) => {
            object3d.userData.planetEgg = egg;
            object3d.userData.isPlanet = true;
        };

        const planets = planetSpecs.map((spec, idx) => {
            const group = new THREE.Group();
            const planetMaterial = new THREE.MeshStandardMaterial({
                color: spec.color,
                roughness: spec.roughness ?? 0.9,
                metalness: 0.0,
                emissive: 0x040608,
                emissiveIntensity: 0.06,
            });
            loadPlanetTexture(spec.tex, (tex) => {
                planetMaterial.map = tex;
                planetMaterial.needsUpdate = true;
            });
            if (spec.normalTex) {
                loadPlanetTexture(spec.normalTex, (tex) => {
                    planetMaterial.normalMap = tex;
                    const n = Number(spec.normalScale);
                    planetMaterial.normalScale = new THREE.Vector2(Number.isFinite(n) ? n : 0.7, Number.isFinite(n) ? n : 0.7);
                    planetMaterial.needsUpdate = true;
                });
            }
            if (spec.bumpTex) {
                loadPlanetTexture(spec.bumpTex, (tex) => {
                    planetMaterial.bumpMap = tex;
                    const b = Number(spec.bumpScale);
                    planetMaterial.bumpScale = Number.isFinite(b) ? b : 0.01;
                    planetMaterial.needsUpdate = true;
                });
            }
            const mesh = new THREE.Mesh(
                new THREE.SphereGeometry(spec.radius, 56, 56),
                planetMaterial
            );
            mesh.rotation.z = spec.tilt * 1.8;
            group.add(mesh);
            const egg = planetEasterEggs[idx] ?? null;
            if (egg) setSpaceInteraction(mesh, egg);

            if (spec.detailShell) {
                const shell = new THREE.Mesh(
                    new THREE.SphereGeometry(spec.radius * 1.03, 40, 40),
                    new THREE.MeshBasicMaterial({
                        color: 0xd5eaff,
                        transparent: true,
                        opacity: spec.shellOpacity ?? 0.12,
                        depthWrite: false,
                        side: THREE.DoubleSide,
                    })
                );
                loadPlanetTexture(spec.tex, (tex) => {
                    shell.material.map = tex;
                    shell.material.needsUpdate = true;
                });
                if (egg) setSpaceInteraction(shell, egg);
                mesh.add(shell);
            }

            const moonPivots = [];
            const moonCount = spec.moons ?? 0;
            for (let m = 0; m < moonCount; m += 1) {
                const moonPivot = new THREE.Group();
                moonPivot.rotation.y = Math.random() * Math.PI * 2;
                moonPivot.rotation.z = (Math.random() - 0.5) * 0.9;
                const moonRadius = Math.max(0.012, spec.radius * (0.12 + Math.random() * 0.08));
                const moonOrbit = spec.radius * (2.2 + m * 0.48 + Math.random() * 0.35);
                const moon = new THREE.Mesh(
                    new THREE.SphereGeometry(moonRadius, 14, 14),
                    new THREE.MeshStandardMaterial({
                        color: 0xd6dde6,
                        roughness: 1.0,
                        metalness: 0.0,
                        emissive: 0x06080a,
                        emissiveIntensity: 0.03,
                    })
                );
                moon.position.x = moonOrbit;
                if (egg) {
                    const moonEgg = {
                        name: `${egg.name} Moon ${m + 1}`,
                        category: "Moon",
                        temp: egg.temp,
                        wind: "No atmosphere",
                        pop: "0",
                        distanceAuMin: egg.distanceAuMin,
                        distanceAuMax: egg.distanceAuMax,
                    };
                    setSpaceInteraction(moon, moonEgg);
                }
                moonPivot.add(moon);
                mesh.add(moonPivot);
                moonPivots.push({
                    pivot: moonPivot,
                    speed: spec.spinSpeed * (2.4 + m * 0.6),
                });
            }

            if (spec.ring) {
                const ringMaterial = new THREE.MeshBasicMaterial({
                    color: spec.ringTint || 0xd9c08a,
                    side: THREE.DoubleSide,
                    transparent: true,
                    opacity: 0.62,
                    depthWrite: false,
                });
                const ringColorTex = spec.tex === "uranus.jpg" ? "saturnringpattern.gif" : "saturnringcolor.jpg";
                loadPlanetTexture(ringColorTex, (tex) => {
                    ringMaterial.map = tex;
                    ringMaterial.needsUpdate = true;
                });
                loadPlanetTexture("saturnringpattern.gif", (tex) => {
                    ringMaterial.alphaMap = tex;
                    ringMaterial.needsUpdate = true;
                });
                const ring = new THREE.Mesh(
                    new THREE.RingGeometry(spec.radius * 1.5, spec.radius * 2.35, 128),
                    ringMaterial
                );
                ring.rotation.x = Math.PI / 2.2;
                if (egg) setSpaceInteraction(ring, egg);
                mesh.add(ring);
            }
            // Random starting phase
            group.rotation.y = 0;
            scene.add(group);
            return {
                group,
                mesh,
                spinSpeed: spec.spinSpeed,
                orbitAu: spec.au,
                orbitPeriodDays: spec.periodDays,
                orbitMeanLonDeg: spec.meanLonDeg,
                moonPivots,
            };
        });

        const connectionsGroup = new THREE.Group();
        const shippingGroup = new THREE.Group();
        const shippingTraffic = [];
        GLOBE_CONNECTIONS.forEach(([fromId, toId]) => {
            const from = GLOBE_MARKERS.find((item) => item.id === fromId);
            const to = GLOBE_MARKERS.find((item) => item.id === toId);
            if (!from || !to) {
                return;
            }
            const start = latLonToVector3(from.lat, from.lon, 1.08);
            const end = latLonToVector3(to.lat, to.lon, 1.08);
            const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(1.55);
            const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
            const arc = new THREE.Line(
                new THREE.BufferGeometry().setFromPoints(curve.getPoints(64)),
                new THREE.LineBasicMaterial({ color: 0x7ad9ff, transparent: true, opacity: 0.34 })
            );
            connectionsGroup.add(arc);
        });
        root.add(connectionsGroup);

        SHIPPING_LANES.forEach((lane) => {
            lane.modeledDistanceNm = routeDistanceNm(lane.waypoints);
            const lanePoints = lane.waypoints.map((point) => latLonToVector3(point.lat, point.lon, 1.034));
            const laneCurve = new THREE.CatmullRomCurve3(lanePoints, false, "catmullrom", 0.08);
            const laneSamples = laneCurve
                .getPoints(320)
                .map((point) => point.clone().normalize().multiplyScalar(1.034));
            const laneSurfaceCurve = new THREE.CatmullRomCurve3(laneSamples, false, "catmullrom", 0.04);
            const laneArc = new THREE.Line(
                new THREE.BufferGeometry().setFromPoints(laneSamples),
                new THREE.LineBasicMaterial({ color: lane.color, transparent: true, opacity: 0.34 })
            );
            laneArc.userData = {
                shippingLane: lane,
                detailLabel: `MODELED DIST ${formatNm(lane.modeledDistanceNm)}`,
            };
            shippingGroup.add(laneArc);

            lane.waypoints.forEach((point, idx) => {
                if (idx === 0 || idx === lane.waypoints.length - 1) return;
                const chokepoint = new THREE.Mesh(
                    new THREE.SphereGeometry(0.01, 14, 14),
                    new THREE.MeshBasicMaterial({ color: lane.color, transparent: true, opacity: 0.7 })
                );
                chokepoint.position.copy(latLonToVector3(point.lat, point.lon, 1.038));
                chokepoint.userData = {
                    shippingLane: lane,
                    detailLabel: `Chokepoint near ${point.lat.toFixed(2)}, ${point.lon.toFixed(2)}`,
                };
                shippingGroup.add(chokepoint);
                shippingTraffic.push({
                    type: "beacon",
                    mesh: chokepoint,
                    baseOpacity: 0.7,
                    phase: idx * 0.65,
                });
            });

            [0, 0.38, 0.72].forEach((phase, shipIdx) => {
                const vessel = new THREE.Mesh(
                    new THREE.SphereGeometry(0.0085, 14, 14),
                    new THREE.MeshBasicMaterial({ color: 0xf4fbff, transparent: true, opacity: 0.95 })
                );
                vessel.userData = { shippingLane: lane, detailLabel: `Active vessel on ${lane.label}` };
                shippingGroup.add(vessel);
                shippingTraffic.push({
                    type: "vessel",
                    mesh: vessel,
                    curve: laneSurfaceCurve,
                    phase: (phase + shipIdx * 0.04) % 1,
                    speed: lane.speed,
                    laneColor: lane.color,
                });
            });
        });
        root.add(shippingGroup);

        const markerGroup = new THREE.Group();
        GLOBE_MARKERS.forEach((marker) => {
            const shell = new THREE.Mesh(
                new THREE.SphereGeometry(0.038, 16, 16),
                new THREE.MeshBasicMaterial({ color: marker.color, transparent: true, opacity: 0.96 })
            );
            const halo = new THREE.Mesh(
                new THREE.SphereGeometry(0.07, 16, 16),
                new THREE.MeshBasicMaterial({ color: marker.color, transparent: true, opacity: 0.18 })
            );
            const anchor = new THREE.Group();
            anchor.position.copy(latLonToVector3(marker.lat, marker.lon, 1.1));
            anchor.name = marker.id;
            anchor.userData = { ...marker, halo, shell };
            anchor.add(shell);
            anchor.add(halo);
            markerGroup.add(anchor);
        });
        root.add(markerGroup);

        // Major financial-market city pins (smaller, color-coded by current open status)
        const marketPinGroup = new THREE.Group();
        const marketPinMeshes = [];
        MARKETS.forEach((market) => {
            const mat = new THREE.MeshBasicMaterial({ color: 0x66e08a, transparent: true, opacity: 0.85 });
            const dot = new THREE.Mesh(new THREE.SphereGeometry(0.018, 12, 12), mat);
            dot.position.copy(latLonToVector3(market.lat, market.lon, 1.085));
            dot.userData = { id: `market_${market.id}`, market };
            marketPinGroup.add(dot);
            marketPinMeshes.push({ mesh: dot, material: mat, market });
        });
        root.add(marketPinGroup);

        // Home pin: Tongeren, Belgium — amber, distinct from threat/market dots
        const HOME_LAT = 50.7806267;
        const HOME_LON = 5.4639172;
        const homePin = new THREE.Mesh(
            new THREE.SphereGeometry(0.028, 16, 16),
            new THREE.MeshBasicMaterial({ color: 0xffb347, transparent: true, opacity: 0.95 })
        );
        homePin.position.copy(latLonToVector3(HOME_LAT, HOME_LON, 1.095));
        homePin.userData = { id: "home_belgium" };
        root.add(homePin);
        const homeHalo = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 16, 16),
            new THREE.MeshBasicMaterial({ color: 0xffb347, transparent: true, opacity: 0.22 })
        );
        homeHalo.position.copy(homePin.position);
        root.add(homeHalo);

        // Live location pin (only if user granted geolocation and current pos is not home)
        let livePin = null;
        let livePinHalo = null;
        if (liveLocation && Number.isFinite(liveLocation.lat) && Number.isFinite(liveLocation.lon)) {
            const distFromHome = Math.hypot(liveLocation.lat - HOME_LAT, liveLocation.lon - HOME_LON);
            if (distFromHome > 0.5) {
                livePin = new THREE.Mesh(
                    new THREE.SphereGeometry(0.026, 16, 16),
                    new THREE.MeshBasicMaterial({ color: 0x5bc8ff, transparent: true, opacity: 0.95 })
                );
                livePin.position.copy(latLonToVector3(liveLocation.lat, liveLocation.lon, 1.095));
                root.add(livePin);
                livePinHalo = new THREE.Mesh(
                    new THREE.SphereGeometry(0.06, 16, 16),
                    new THREE.MeshBasicMaterial({ color: 0x5bc8ff, transparent: true, opacity: 0.18 })
                );
                livePinHalo.position.copy(livePin.position);
                root.add(livePinHalo);
            }
        }

        const selectedRing = new THREE.Mesh(
            new THREE.TorusGeometry(0.11, 0.008, 12, 48),
            new THREE.MeshBasicMaterial({ color: selectedMarker.color, transparent: true, opacity: 0.92 })
        );
        selectedRing.position.copy(latLonToVector3(selectedMarker.lat, selectedMarker.lon, 1.12));
        selectedRing.lookAt(new THREE.Vector3(0, 0, 0));
        root.add(selectedRing);

        // Reusable label sprite that floats above whichever pin was last clicked.
        const makeLabelTexture = (text) => {
            const canvas = document.createElement("canvas");
            canvas.width = 512;
            canvas.height = 128;
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const pad = 18;
            ctx.font = "600 44px 'Inter', system-ui, sans-serif";
            const textWidth = ctx.measureText(text).width;
            const boxW = Math.min(canvas.width - 4, textWidth + pad * 2);
            const boxH = 88;
            const boxX = (canvas.width - boxW) / 2;
            const boxY = (canvas.height - boxH) / 2;
            ctx.fillStyle = "rgba(6, 12, 22, 0.86)";
            ctx.strokeStyle = "rgba(91, 200, 255, 0.85)";
            ctx.lineWidth = 2;
            const r = 14;
            ctx.beginPath();
            ctx.moveTo(boxX + r, boxY);
            ctx.lineTo(boxX + boxW - r, boxY);
            ctx.quadraticCurveTo(boxX + boxW, boxY, boxX + boxW, boxY + r);
            ctx.lineTo(boxX + boxW, boxY + boxH - r);
            ctx.quadraticCurveTo(boxX + boxW, boxY + boxH, boxX + boxW - r, boxY + boxH);
            ctx.lineTo(boxX + r, boxY + boxH);
            ctx.quadraticCurveTo(boxX, boxY + boxH, boxX, boxY + boxH - r);
            ctx.lineTo(boxX, boxY + r);
            ctx.quadraticCurveTo(boxX, boxY, boxX + r, boxY);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#def4ff";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 2);
            const tex = new THREE.CanvasTexture(canvas);
            if ("colorSpace" in tex) tex.colorSpace = THREE.SRGBColorSpace;
            tex.needsUpdate = true;
            return tex;
        };
        const labelMaterial = new THREE.SpriteMaterial({
            map: makeLabelTexture(""),
            transparent: true,
            depthTest: false,
            depthWrite: false,
        });
        const labelSprite = new THREE.Sprite(labelMaterial);
        labelSprite.scale.set(0.55, 0.14, 1);
        labelSprite.visible = false;
        labelSprite.renderOrder = 999;
        root.add(labelSprite);

        const showLabel = (text, lat, lon) => {
            if (labelMaterial.map) labelMaterial.map.dispose();
            labelMaterial.map = makeLabelTexture(text);
            labelMaterial.needsUpdate = true;
            const pos = latLonToVector3(lat, lon, 1.22);
            labelSprite.position.copy(pos);
            // Scale label width with text length so long names don't squish
            const w = Math.max(0.45, Math.min(1.1, 0.04 + text.length * 0.025));
            labelSprite.scale.set(w, w * 0.26, 1);
            labelSprite.visible = true;
        };

        const raycaster = new THREE.Raycaster();
        const pointer = new THREE.Vector2();
        let rafId = 0;
        const weatherCache = new Map();
        const WEATHER_LABELS = {
            0: "Clear",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Rime fog",
            51: "Light drizzle",
            53: "Drizzle",
            55: "Dense drizzle",
            56: "Freezing drizzle",
            57: "Freezing drizzle",
            61: "Light rain",
            63: "Rain",
            65: "Heavy rain",
            66: "Freezing rain",
            67: "Freezing rain",
            71: "Light snow",
            73: "Snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Rain showers",
            81: "Rain showers",
            82: "Violent showers",
            85: "Snow showers",
            86: "Snow showers",
            95: "Thunderstorm",
            96: "Thunder hail",
            99: "Thunder hail",
        };
        const hoverState = {
            key: "",
            visible: false,
            title: "",
            country: "",
            lat: 0,
            lon: 0,
            weatherText: "loading...",
            worldPos: new THREE.Vector3(),
            pointerX: 0,
            pointerY: 0,
            pointerActive: false,
        };

        const hideHover = () => {
            hoverState.visible = false;
            hoverState.pointerActive = false;
            if (hoverCardRef.current) hoverCardRef.current.style.display = "none";
            if (hoverLineRef.current) hoverLineRef.current.style.display = "none";
        };

        const setHoverPointerAnchor = (event, rect) => {
            if (!event || !rect) return;
            hoverState.pointerX = Math.min(rect.width - 2, Math.max(2, event.clientX - rect.left));
            hoverState.pointerY = Math.min(rect.height - 2, Math.max(2, event.clientY - rect.top));
            hoverState.pointerActive = true;
        };

        const getHoverAnchor = (rect, worldPos) => {
            if (hoverState.pointerActive) {
                return {
                    visible: true,
                    px: hoverState.pointerX,
                    py: hoverState.pointerY,
                };
            }
            const projected = worldPos.clone().project(camera);
            const visible = projected.z > -1 && projected.z < 1;
            return {
                visible,
                px: (projected.x * 0.5 + 0.5) * rect.width,
                py: (-projected.y * 0.5 + 0.5) * rect.height,
            };
        };

        const LIGHT_MINUTES_PER_AU = 8.316746;
        const KM_PER_AU = 149597870.7;
        const EARTH_RADIUS_KM = 6371;
        const KM_TO_NM = 0.5399568;
        const formatMinutesHuman = (minutes) => {
            if (!Number.isFinite(minutes) || minutes <= 0) return "n/a";
            if (minutes >= 60) {
                const h = Math.floor(minutes / 60);
                const m = Math.round(minutes % 60);
                return `${h}h ${String(m).padStart(2, "0")}m`;
            }
            return `${minutes.toFixed(1)}m`;
        };
        const distanceRangeLabel = (egg) => {
            const min = Number(egg.distanceAuMin);
            const max = Number(egg.distanceAuMax);
            if (Number.isFinite(min) && Number.isFinite(max)) {
                if (Math.abs(min - max) < 0.005) return `~${min.toFixed(2)} AU`;
                return `${min.toFixed(2)}-${max.toFixed(2)} AU`;
            }
            return "n/a";
        };
        const distanceRangeKmLabel = (egg) => {
            const min = Number(egg.distanceAuMin);
            const max = Number(egg.distanceAuMax);
            if (!Number.isFinite(min) || !Number.isFinite(max)) return "n/a";
            const minM = (min * KM_PER_AU) / 1_000_000;
            const maxM = (max * KM_PER_AU) / 1_000_000;
            if (Math.abs(minM - maxM) < 0.2) return `~${minM.toFixed(1)}M km`;
            return `${minM.toFixed(1)}-${maxM.toFixed(1)}M km`;
        };
        const lightEtaLabel = (egg) => {
            const min = Number(egg.distanceAuMin);
            const max = Number(egg.distanceAuMax);
            if (!Number.isFinite(min) || !Number.isFinite(max)) return "n/a";
            const minEta = min * LIGHT_MINUTES_PER_AU;
            const maxEta = max * LIGHT_MINUTES_PER_AU;
            if (Math.abs(minEta - maxEta) < 0.25) return formatMinutesHuman(minEta);
            return `${formatMinutesHuman(minEta)}-${formatMinutesHuman(maxEta)}`;
        };
        const toRad = (deg) => (deg * Math.PI) / 180;
        const legDistanceNm = (a, b) => {
            const dLat = toRad(b.lat - a.lat);
            const dLon = toRad(b.lon - a.lon);
            const lat1 = toRad(a.lat);
            const lat2 = toRad(b.lat);
            const s = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
            const c = 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
            return EARTH_RADIUS_KM * c * KM_TO_NM;
        };
        const routeDistanceNm = (waypoints) => {
            let total = 0;
            for (let i = 1; i < waypoints.length; i += 1) {
                total += legDistanceNm(waypoints[i - 1], waypoints[i]);
            }
            return total;
        };
        const formatNm = (nm) => `${Math.round(nm).toLocaleString()} nm`;

        const showSpaceEggHover = (egg, worldPos) => {
            hoverState.key = `planet:${egg.name}`;
            hoverState.visible = true;
            hoverState.title = egg.name;
            hoverState.country = "Outer System";
            hoverState.lat = 0;
            hoverState.lon = 0;
            hoverState.weatherText = `TEMP ${egg.temp} • WIND ${egg.wind}`;
            hoverState.worldPos.copy(worldPos);
            if (hoverTitleRef.current) hoverTitleRef.current.textContent = `${egg.name} • ${egg.category || "Outer System"}`;
            if (hoverPopRef.current) hoverPopRef.current.textContent = `ESTM POPULATION ${egg.pop}`;
            if (hoverCoordsRef.current) hoverCoordsRef.current.textContent = `EARTH DIST ${distanceRangeLabel(egg)} • ${distanceRangeKmLabel(egg)}`;
            if (hoverWeatherRef.current) hoverWeatherRef.current.textContent = `LIGHT ETA ${lightEtaLabel(egg)} • TEMP ${egg.temp}`;
            if (hoverCardRef.current) hoverCardRef.current.style.display = "grid";
            if (hoverLineRef.current) {
                const rect = renderer.domElement.getBoundingClientRect();
                const anchor = getHoverAnchor(rect, worldPos);
                const px = anchor.px;
                const py = anchor.py;
                const cardX = Math.min(rect.width - 228, Math.max(14, px + 34));
                const cardY = Math.min(rect.height - 124, Math.max(12, py - 88));
                const anchorX = cardX;
                const anchorY = cardY + 26;
                const dx = anchorX - px;
                const dy = anchorY - py;
                const len = Math.hypot(dx, dy);
                hoverLineRef.current.style.display = "block";
                hoverLineRef.current.style.left = `${px}px`;
                hoverLineRef.current.style.top = `${py}px`;
                hoverLineRef.current.style.width = `${len}px`;
                hoverLineRef.current.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
            }
        };

        const showShippingLaneHover = (lane, worldPos, detailLabel) => {
            hoverState.key = `shipping:${lane.id}`;
            hoverState.visible = true;
            hoverState.title = lane.label;
            hoverState.country = lane.category || "Maritime Route";
            hoverState.lat = 0;
            hoverState.lon = 0;
            hoverState.weatherText = lane.eta;
            hoverState.worldPos.copy(worldPos);
            if (hoverTitleRef.current) hoverTitleRef.current.textContent = `${lane.label} • ${lane.category || "Maritime Route"}`;
            if (hoverPopRef.current) hoverPopRef.current.textContent = `CARGO ${lane.cargo}`;
            if (hoverCoordsRef.current) hoverCoordsRef.current.textContent = `CHOKEPOINTS ${lane.chokepoints.join(" • ")}`;
            if (hoverWeatherRef.current) {
                const modeled = Number.isFinite(lane.modeledDistanceNm)
                    ? formatNm(lane.modeledDistanceNm)
                    : "n/a";
                hoverWeatherRef.current.textContent = `${detailLabel || lane.metric} • ETA EST ${lane.eta} • ${modeled}`;
            }
            if (hoverCardRef.current) hoverCardRef.current.style.display = "grid";
            if (hoverLineRef.current) {
                const rect = renderer.domElement.getBoundingClientRect();
                const anchor = getHoverAnchor(rect, worldPos);
                const px = anchor.px;
                const py = anchor.py;
                const cardWidth = 228;
                const cardHeight = 112;
                const preferLeft = px > rect.width * 0.56;
                const preferBelow = py < rect.height * 0.3;
                const cardX = preferLeft
                    ? Math.max(14, px - cardWidth - 24)
                    : Math.min(rect.width - cardWidth - 14, px + 34);
                const cardY = preferBelow
                    ? Math.min(rect.height - cardHeight - 12, py + 24)
                    : Math.max(12, py - 88);
                const anchorX = preferLeft ? cardX + cardWidth : cardX;
                const anchorY = cardY + 26;
                const dx = anchorX - px;
                const dy = anchorY - py;
                const len = Math.hypot(dx, dy);
                if (hoverCardRef.current) {
                    hoverCardRef.current.style.left = `${cardX}px`;
                    hoverCardRef.current.style.top = `${cardY}px`;
                }
                hoverLineRef.current.style.display = "block";
                hoverLineRef.current.style.left = `${px}px`;
                hoverLineRef.current.style.top = `${py}px`;
                hoverLineRef.current.style.width = `${len}px`;
                hoverLineRef.current.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
            }
        };

        const getInteractiveTargets = () => [
            ...markerGroup.children,
            ...marketPinGroup.children,
            ...shippingGroup.children,
            homePin,
            ...(livePin ? [livePin] : []),
            ...planets.map((p) => p.mesh),
            sunCore,
            sunHalo,
            earthMoon,
        ];

        const applyHoverContent = () => {
            const country = hoverState.country || "n/a";
            const pop = formatPopulationEstimate(COUNTRY_POP_EST[country]);
            if (hoverTitleRef.current) hoverTitleRef.current.textContent = `${hoverState.title} • ${country}`;
            if (hoverPopRef.current) hoverPopRef.current.textContent = `ESTM POPULATION ${pop}`;
            if (hoverCoordsRef.current) hoverCoordsRef.current.textContent = `DETAIL COORDS ${hoverState.lat.toFixed(3)}, ${hoverState.lon.toFixed(3)}`;
            if (hoverWeatherRef.current) hoverWeatherRef.current.textContent = `WEATHER TEMP ${hoverState.weatherText}`;
        };

        const fetchWeather = async (lat, lon, key) => {
            const cacheHit = weatherCache.get(key);
            if (cacheHit && performance.now() - cacheHit.t < 600000) {
                hoverState.weatherText = cacheHit.text;
                applyHoverContent();
                return;
            }
            try {
                const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}&current=temperature_2m,weather_code&timezone=auto`;
                const res = await fetch(url, { cache: "no-store" });
                if (!res.ok) throw new Error(`weather_${res.status}`);
                const payload = await res.json();
                const temp = payload?.current?.temperature_2m;
                const code = payload?.current?.weather_code;
                const label = WEATHER_LABELS[Number(code)] || "Unknown";
                const weatherText = Number.isFinite(Number(temp)) ? `${Math.round(Number(temp))}°C • ${label}` : "n/a";
                weatherCache.set(key, { t: performance.now(), text: weatherText });
                if (hoverState.key === key && hoverState.visible) {
                    hoverState.weatherText = weatherText;
                    applyHoverContent();
                }
            } catch (_e) {
                if (hoverState.key === key && hoverState.visible) {
                    hoverState.weatherText = "n/a";
                    applyHoverContent();
                }
            }
        };

        const setHoverFromData = (data, worldPos) => {
            if (!data) {
                hideHover();
                return;
            }
            const lat = Number(data.lat);
            const lon = Number(data.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                hideHover();
                return;
            }
            const title = String(data.title || data.label || data.name || "Location");
            const country = String(data.country || "n/a");
            const key = `${country}:${lat.toFixed(3)},${lon.toFixed(3)}`;
            hoverState.key = key;
            hoverState.visible = true;
            hoverState.title = title;
            hoverState.country = country;
            hoverState.lat = lat;
            hoverState.lon = lon;
            hoverState.weatherText = "loading...";
            hoverState.worldPos.copy(worldPos);
            applyHoverContent();
            fetchWeather(lat, lon, key);
        };

        const isFrontHemispherePoint = (point) => {
            if (!point) return false;
            const surfaceNormal = point.clone().normalize();
            const cameraDirection = camera.position.clone().normalize();
            return surfaceNormal.dot(cameraDirection) > 0.06;
        };

        const getVisibleHit = (hits) => hits.find((item) => isFrontHemispherePoint(item.point));

        const updateHoverFromPointer = (event) => {
            if (event.pointerType === "touch") {
                hideHover();
                return;
            }
            const rect = renderer.domElement.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                hideHover();
                return;
            }
            pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            setHoverPointerAnchor(event, rect);
            raycaster.setFromCamera(pointer, camera);
            const hits = raycaster.intersectObjects(getInteractiveTargets(), true);
            const hit = getVisibleHit(hits);
            if (!hit) {
                hideHover();
                return;
            }
            const node = hit.object;
            // Easter egg: planet hover
            if (node.userData.isPlanet && node.userData.planetEgg) {
                const worldPos = node.getWorldPosition(new THREE.Vector3());
                const egg = node.userData.planetEgg;
                showSpaceEggHover(egg, worldPos);
                return;
            }
            if (node.userData.shippingLane) {
                const worldPos = hit.point.clone();
                showShippingLaneHover(node.userData.shippingLane, worldPos, node.userData.detailLabel);
                return;
            }
            const data = node?.parent?.userData?.id ? node.parent.userData : node?.userData;
            const worldPos = node.getWorldPosition(new THREE.Vector3());
            if (data?.market) {
                setHoverFromData({
                    title: `${data.market.name} • ${data.market.city}`,
                    country: data.market.country,
                    lat: data.market.lat,
                    lon: data.market.lon,
                }, worldPos);
                return;
            }
            if (data?.id === "home_belgium") {
                setHoverFromData({ title: "Home • Tongeren 3700, BE", country: "Belgium", lat: HOME_LAT, lon: HOME_LON }, worldPos);
                return;
            }
            if (data?.id && Number.isFinite(data.lat) && Number.isFinite(data.lon)) {
                setHoverFromData({
                    title: data.label || data.id,
                    country: data.country || "n/a",
                    lat: data.lat,
                    lon: data.lon,
                }, worldPos);
                return;
            }
            if (livePin && node === livePin) {
                setHoverFromData({
                    title: "Live location",
                    country: "n/a",
                    lat: liveLocation?.lat ?? HOME_LAT,
                    lon: liveLocation?.lon ?? HOME_LON,
                }, worldPos);
                return;
            }
            hideHover();
        };

        let lastSunUpdate = 0;
        let lastMarketTick = 0;
        let earthInspectionMode = false;
        const animate = () => {
            const time = performance.now() * 0.001;
            const nowMs = performance.now();
            const deltaSec = Math.min(0.05, Math.max(0.001, (nowMs - movementState.lastFrameAt) / 1000));
            movementState.lastFrameAt = nowMs;

            // Recompute sun direction every ~5s (terminator drifts slowly)
            if (performance.now() - lastSunUpdate > 5000) {
                updateSunFromClock();
                lastSunUpdate = performance.now();
            }
            // Recolor market pins every ~1s based on open/closed status
            if (performance.now() - lastMarketTick > 1000) {
                const now = new Date();
                marketPinMeshes.forEach(({ material, market }) => {
                    const status = getMarketStatus(market, now);
                    material.color.setHex(status.open ? 0x66e08a : 0xff7b95);
                    material.opacity = status.open ? 0.95 : 0.55;
                });
                lastMarketTick = performance.now();
            }


            // Smoother, more responsive interpolation for precise control
            cameraState.distance += (cameraState.targetDistance - cameraState.distance) * 0.18;
            cameraState.yaw += (cameraState.targetYaw - cameraState.yaw) * 0.28;
            cameraState.pitch += (cameraState.targetPitch - cameraState.pitch) * 0.28;

            // Post-release inertia for camera orbit, damped over time (faster decay)
            if (!dragState) {
                cameraState.targetYaw += movementState.inertiaYaw * (deltaSec * 60);
                cameraState.targetPitch += movementState.inertiaPitch * (deltaSec * 60);
                const damp = Math.pow(0.7, deltaSec * 60);
                movementState.inertiaYaw *= damp;
                movementState.inertiaPitch *= damp;
            }

            // Quaternion-based orbit: rotate the rest position (0, 0, distance) by yaw (Y axis)
            // then by pitch (local X axis). This gives unlimited rotation on every axis with
            // no pole flip. We also rotate the up vector so lookAt() works past the poles.
            const qYaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), cameraState.yaw);
            const qPitch = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), cameraState.pitch);
            const orbit = qYaw.clone().multiply(qPitch);
            const camOffset = new THREE.Vector3(0, 0, cameraState.distance).applyQuaternion(orbit);
            const camUp = new THREE.Vector3(0, 1, 0).applyQuaternion(orbit);
            camera.position.copy(camOffset);
            camera.up.copy(camUp);
            camera.lookAt(0, 0, 0);

            // Auto-rotate the globe ONLY when user isn't actively interacting
            const sinceInteract = performance.now() - cameraState.lastInteractionAt;
            const autoRotateAllowed = !dragState && sinceInteract > 3500;
            const zoomT = THREE.MathUtils.clamp(1 - (cameraState.distance - ZOOM_MIN) / (ZOOM_MAX - ZOOM_MIN), 0, 1);
            const idleFade = THREE.MathUtils.clamp((sinceInteract - 1800) / 2600, 0, 1);
            const breathing = 0.75 + 0.25 * Math.sin(time * 0.42 + movementState.driftPhase);
            const baseSpin = (0.00022 - zoomT * 0.00013) * breathing;
            movementState.targetRootSpin = autoRotateAllowed ? (baseSpin * idleFade) : 0;
            movementState.rootSpin += (movementState.targetRootSpin - movementState.rootSpin) * 0.04;
            root.rotation.y += movementState.rootSpin * (deltaSec * 60);
            stars.rotation.y += Math.max(0, movementState.rootSpin * 0.2) * (deltaSec * 60);
            starsBright.rotation.y += Math.max(0, movementState.rootSpin * 0.28) * (deltaSec * 60);
            // Decorative planets always drift on their orbits (no interaction)
            const nowDateMs = Date.now();
            const earthHelio = heliocentricPos(EARTH_ORBIT.au, EARTH_ORBIT.periodDays, EARTH_ORBIT.meanLonDeg, nowDateMs);
            planets.forEach((p) => {
                const bodyHelio = heliocentricPos(p.orbitAu, p.orbitPeriodDays, p.orbitMeanLonDeg, nowDateMs);
                const geo = bodyHelio.sub(earthHelio);
                const geoDistAu = Math.max(0.0001, geo.length());
                const sceneDist = compressAuDistance(geoDistAu);
                const dir = geo.normalize();
                p.mesh.position.set(dir.x * sceneDist, dir.y * sceneDist, dir.z * sceneDist);
                p.mesh.rotation.y += p.spinSpeed * 2;
                p.moonPivots.forEach((moon) => {
                    moon.pivot.rotation.y += moon.speed;
                });
            });
            earthMoonPivot.rotation.y += 0.00045;
            const sunPulse = 1 + Math.sin(time * 1.6) * 0.035;
            sunCore.scale.setScalar(sunPulse);
            sunHalo.material.opacity = 0.20 + (Math.sin(time * 1.1) + 1) * 0.06;
            // Cloud layer intentionally disabled: non-live clouds can be misleading.

            // Only show wireframe detail when a city is selected and the camera is
            // close enough to imply building-level inspection.
            const zoomEase = Math.pow(zoomT, 1.4);
            if (cityInspectionTarget) {
                const normal = latLonToVector3(cityInspectionTarget.lat, cityInspectionTarget.lon, 1.0).normalize();
                cityScanGroup.position.copy(normal.clone().multiplyScalar(1.045));
                cityScanGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
            }
            const cityInspectionBlend = cityInspectionTarget
                ? THREE.MathUtils.clamp((1.1 - cameraState.distance) / 0.28, 0, 1)
                : 0;
            const nextInspectionMode = cityInspectionBlend > 0.06;
            if (nextInspectionMode !== earthInspectionMode) {
                earthInspectionMode = nextInspectionMode;
                if (statusChipRef.current) {
                    statusChipRef.current.textContent = earthInspectionMode && cityInspectionTarget
                        ? `City Scan • ${cityInspectionTarget.name}`
                        : "Strategic Mesh Online";
                }
            }
            // Keep the planet solid. The wireframe effect is localized to the active city scan.
            earthMaterial.opacity = 1.0;
            const baseCloudOpacity = cloudMaterial.alphaMap ? 0.55 : 0;
            cloudMaterial.opacity = baseCloudOpacity;
            nightMaterial.uniforms.opacity.value = 0.65 * (1.0 - zoomEase * 0.6);
            wireSphere.material.opacity = 0;
            glowSphere.material.opacity = 0.026 - zoomEase * 0.01;
            atmosphereMaterial.uniforms.intensity.value = 0.34 - zoomEase * 0.1;
            gridMaterial.opacity = 0;
            stars.material.opacity = 0.75 - zoomEase * 0.55;
            starsBright.material.opacity = 0.78 + Math.sin(time * 2.2) * 0.12;

            cityScanGroup.visible = cityInspectionBlend > 0.01;
            cityScanFloor.material.opacity = cityInspectionBlend * 0.28;
            cityScanPulse.material.opacity = cityInspectionBlend * 0.42;
            cityScanPulse.scale.setScalar(1 + Math.sin(time * 2.1) * 0.18);
            cityScanBuildings.forEach((building, idx) => {
                building.material.opacity = cityInspectionBlend * 0.82;
                building.scale.y = 1 + Math.sin(time * 1.3 + idx * 0.8) * 0.04;
            });

            // Deep zoom on Earth: reduce clutter from outer solar objects and
            // strengthen the near-surface inspection look.
            const hideSolar = earthInspectionMode;
            sunGroup.visible = !hideSolar;
            sunHalo.visible = !hideSolar;
            planets.forEach((p) => {
                p.group.visible = !hideSolar;
            });
            stars.visible = !hideSolar;
            starsBright.visible = !hideSolar;
            selectedRing.material.opacity = 0.65 + cityInspectionBlend * 0.22;
            selectedRing.scale.setScalar(1 + cityInspectionBlend * 0.18);
            atmosphereMaterial.uniforms.intensity.value += cityInspectionBlend * 0.06;

            // Feed the live sub-solar direction (in root-local space) into the night shader
            // so city lights only show on the dark hemisphere across the terminator.
            {
                const sunWorld = sunLight.position.clone().normalize();
                const sunLocal = sunWorld.clone().applyQuaternion(root.quaternion.clone().invert());
                nightMaterial.uniforms.sunDir.value.copy(sunLocal);
            }

            connectionsGroup.children.forEach((line, idx) => {
                line.material.opacity = 0.16 + (Math.sin(time * 1.8 + idx) + 1) * 0.09;
            });
            shippingTraffic.forEach((item, idx) => {
                if (item.type === "vessel") {
                    const progress = (time * item.speed + item.phase) % 1;
                    const pos = item.curve.getPointAt(progress);
                    item.mesh.position.copy(pos);
                    item.mesh.scale.setScalar(1 + Math.sin(time * 6 + idx) * 0.18);
                    const material = item.mesh.material;
                    material.color.setHex(item.laneColor);
                    material.opacity = 0.78 + Math.sin(time * 4.5 + idx) * 0.14;
                } else if (item.type === "beacon") {
                    item.mesh.material.opacity = item.baseOpacity + Math.sin(time * 3.1 + item.phase) * 0.18;
                    item.mesh.scale.setScalar(1 + Math.sin(time * 2.8 + item.phase) * 0.22);
                }
            });
            markerGroup.children.forEach((anchor, idx) => {
                const pulse = 1 + Math.sin(time * 2.4 + idx) * 0.16;
                const isSelected = anchor.name === selectedMarkerId;
                anchor.userData.halo.scale.setScalar(isSelected ? pulse * 1.45 : pulse);
                anchor.userData.halo.material.opacity = isSelected ? 0.34 : 0.16;
                anchor.userData.shell.scale.setScalar(isSelected ? 1.28 : 1);
            });
            selectedRing.rotation.z += 0.02;

            if (hoverState.visible && hoverCardRef.current && hoverLineRef.current) {
                const rect = renderer.domElement.getBoundingClientRect();
                const anchor = getHoverAnchor(rect, hoverState.worldPos);
                if (!anchor.visible) {
                    hideHover();
                } else {
                    const px = anchor.px;
                    const py = anchor.py;
                    const cardWidth = 228;
                    const cardHeight = 112;
                    const preferLeft = px > rect.width * 0.56;
                    const preferBelow = py < rect.height * 0.3;
                    const cardX = preferLeft
                        ? Math.max(14, px - cardWidth - 24)
                        : Math.min(rect.width - cardWidth - 14, px + 34);
                    const cardY = preferBelow
                        ? Math.min(rect.height - cardHeight - 12, py + 24)
                        : Math.max(12, py - 88);
                    const anchorX = preferLeft ? cardX + cardWidth : cardX;
                    const anchorY = cardY + 26;
                    const dx = anchorX - px;
                    const dy = anchorY - py;
                    const len = Math.hypot(dx, dy);
                    hoverCardRef.current.style.display = "grid";
                    hoverCardRef.current.style.left = `${cardX}px`;
                    hoverCardRef.current.style.top = `${cardY}px`;
                    hoverLineRef.current.style.display = "block";
                    hoverLineRef.current.style.left = `${px}px`;
                    hoverLineRef.current.style.top = `${py}px`;
                    hoverLineRef.current.style.width = `${len}px`;
                    hoverLineRef.current.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
                }
            }

            renderer.render(scene, camera);
            rafId = requestAnimationFrame(animate);
        };
        animate();

        const onResize = () => {
            const nextWidth = Math.max(300, container.clientWidth || width);
            const nextHeight = Math.max(300, container.clientHeight || height);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
            renderer.setSize(nextWidth, nextHeight);
            camera.aspect = nextWidth / nextHeight;
            camera.updateProjectionMatrix();
        };
        window.addEventListener("resize", onResize);
        // Also react to user-driven CSS resize on .globe-frame (resize: both).
        let resizeObserver = null;
        if (typeof ResizeObserver !== "undefined") {
            resizeObserver = new ResizeObserver(() => onResize());
            resizeObserver.observe(container);
        }

        const onClick = (event) => {
            // Skip click handling if it was actually a drag/orbit gesture
            if (event.defaultPrevented) return;
            const movedDuringPress = dragState !== null;
            if (movedDuringPress) return;
            const rect = renderer.domElement.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                return;
            }
            pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(pointer, camera);
            // Include threat markers, market dots, home pin, and live pin as clickable.
            const clickTargets = getInteractiveTargets();
            const hits = raycaster.intersectObjects(clickTargets, true);
            const hit = getVisibleHit(hits);
            const node = hit?.object;
            const data = node?.parent?.userData?.id ? node.parent.userData : node?.userData;

            if (node?.userData?.isPlanet && node.userData.planetEgg) {
                setCityInspectionTarget(null);
                const egg = node.userData.planetEgg;
                const worldPos = node.getWorldPosition(new THREE.Vector3());
                showSpaceEggHover(egg, worldPos);
                // Keep interaction feel similar to other objects by nudging zoom to a readable solar view.
                const targetZoom = egg.name === "Sun" ? 8.4 : 6.4;
                cameraState.targetDistance = Math.max(ZOOM_MIN + 0.25, Math.min(targetZoom, ZOOM_MAX));
                cameraState.userActive = true;
                cameraState.lastInteractionAt = performance.now();
                return;
            }

            if (node?.userData?.shippingLane) {
                setCityInspectionTarget(null);
                const lane = node.userData.shippingLane;
                const worldPos = hit.point.clone();
                showShippingLaneHover(lane, worldPos, node.userData.detailLabel);
                return;
            }

            if (data?.market) {
                // Market city dot
                const m = data.market;
                setCityInspectionTarget({ name: m.city, lat: m.lat, lon: m.lon });
                const status = getMarketStatus(m, new Date());
                showLabel(`${m.name} • ${m.city} • ${status.label}`, m.lat, m.lon);
                cameraState.targetYaw = -(m.lon * Math.PI) / 180;
                cameraState.targetPitch = (m.lat * Math.PI) / 180;
                cameraState.targetDistance = Math.max(ZOOM_MIN + 0.3, Math.min(cameraState.targetDistance, 2.4));
                cameraState.userActive = true;
                cameraState.lastInteractionAt = performance.now();
                return;
            }
            if (data?.id === "home_belgium") {
                setCityInspectionTarget({ name: "Tongeren", lat: HOME_LAT, lon: HOME_LON });
                showLabel("Home • Tongeren 3700, BE", HOME_LAT, HOME_LON);
                cameraState.targetYaw = -(HOME_LON * Math.PI) / 180;
                cameraState.targetPitch = (HOME_LAT * Math.PI) / 180;
                cameraState.targetDistance = Math.max(ZOOM_MIN + 0.3, Math.min(cameraState.targetDistance, 2.4));
                cameraState.lastInteractionAt = performance.now();
                return;
            }
            if (data?.id && onMarkerSelect) {
                const matched = GLOBE_MARKERS.find((item) => item.id === data.id) || data;
                setCityInspectionTarget(CITY_SCAN_MARKERS.has(matched.label)
                    ? { name: matched.label, lat: matched.lat, lon: matched.lon }
                    : null);
                showLabel(matched.label || data.id, matched.lat, matched.lon);
                // Google-Earth style fly-to: orbit camera so the clicked marker faces us, and zoom in.
                const lat = (matched.lat * Math.PI) / 180;
                const lon = (matched.lon * Math.PI) / 180;
                cameraState.targetYaw = -lon;            // yaw rotates around Y; lon is longitude east
                cameraState.targetPitch = lat;
                cameraState.targetDistance = Math.max(ZOOM_MIN + 0.3, Math.min(cameraState.targetDistance, 2.4));
                cameraState.userActive = true;
                cameraState.lastInteractionAt = performance.now();
                onMarkerSelect(matched);
            }
        };
        renderer.domElement.addEventListener("click", onClick);
        const onPointerLeave = () => hideHover();
        renderer.domElement.addEventListener("pointerleave", onPointerLeave);

        return () => {
            window.removeEventListener("resize", onResize);
            if (resizeObserver) {
                try { resizeObserver.disconnect(); } catch (_e) { /* noop */ }
            }
            renderer.domElement.removeEventListener("click", onClick);
            renderer.domElement.removeEventListener("pointerleave", onPointerLeave);
            renderer.domElement.removeEventListener("wheel", onWheel);
            renderer.domElement.removeEventListener("pointerdown", onPointerDown);
            renderer.domElement.removeEventListener("pointermove", onPointerMove);
            renderer.domElement.removeEventListener("pointerup", onPointerUp);
            renderer.domElement.removeEventListener("pointercancel", onPointerUp);
            cancelAnimationFrame(rafId);
            starGeometry.dispose();
            stars.material.dispose();
            root.traverse((node) => {
                if (node.geometry) {
                    node.geometry.dispose();
                }
                if (node.material) {
                    if (Array.isArray(node.material)) {
                        node.material.forEach((material) => material.dispose());
                    } else {
                        node.material.dispose();
                    }
                }
            });
            renderer.dispose();
            if (renderer.domElement.parentNode === container) {
                container.removeChild(renderer.domElement);
            }
        };
    }, [onMarkerSelect, selectedMarkerId, liveLocation?.lat, liveLocation?.lon]);

    return React.createElement(
        "section",
        { className: "globe-frame", role: "img", "aria-label": "Three dimensional globe layer" },
        React.createElement("div", { ref: statusChipRef, className: "globe-status-chip" }, "Strategic Mesh Online"),
        React.createElement("div", { ref: containerRef, className: "globe-canvas" }),
        React.createElement("div", { ref: hoverLineRef, className: "globe-hover-line", "aria-hidden": "true" }),
        React.createElement(
            "div",
            { ref: hoverCardRef, className: "globe-hover-card", "aria-hidden": "true" },
            React.createElement("div", { ref: hoverTitleRef, className: "globe-hover-title" }),
            React.createElement("div", { ref: hoverPopRef, className: "globe-hover-row" }),
            React.createElement("div", { ref: hoverCoordsRef, className: "globe-hover-row" }),
            React.createElement("div", { ref: hoverWeatherRef, className: "globe-hover-row" })
        )
    );
}

function SlidePanel({ marker }) {
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

function HudViewport() {
    const [selectedMarker, setSelectedMarker] = React.useState(GLOBE_MARKERS[0]);
    const [dialogueRows, setDialogueRows] = React.useState([]);
    const [dialogueLoading, setDialogueLoading] = React.useState(true);
    const [dialogueError, setDialogueError] = React.useState("");
    const liveLocation = useLiveLocation();
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
        React.createElement("p", { className: "hud-subline" }, "Live node selection, tactical feed stack, and high-contrast HUD overlays anchored to the current React surface."),
        React.createElement(CommandDeck, { marker: selectedMarker }),
        React.createElement(
            "div",
            { className: "hud-theatre hud-theatre-cross" },
            React.createElement(
                "section",
                { className: "hud-side-column hud-left-column" },
                React.createElement(DialogueDatasetPanel, {
                    rows: dialogueRows,
                    loading: dialogueLoading,
                    error: dialogueError,
                }),
                React.createElement(LiveNewsPanel),
                React.createElement(FinancialSocialMissionWidgets, { selectedMarker, liveLocation })
            ),
            React.createElement(
                "section",
                { className: "hud-main-column" },
                React.createElement(GlobeLayer, { onMarkerSelect: setSelectedMarker, selectedMarkerId: selectedMarker.id, liveLocation }),
                React.createElement(MarkerRibbon, {
                    markers: GLOBE_MARKERS,
                    selectedId: selectedMarker.id,
                    onSelect: setSelectedMarker,
                }),
                React.createElement("div", { className: "hud-footnotes" }, `Node mesh: ${GLOBE_MARKERS.map((item) => item.label).join(" • ")}`)
            ),
            React.createElement(
                "section",
                { className: "hud-side-column hud-right-column" },
                React.createElement(LiveLocationBadge, { liveLocation }),
                React.createElement(SlidePanel, { marker: selectedMarker }),
                React.createElement(MarketHoursPanel)
            )
        ),
        React.createElement(
            "div",
            { className: "hud-footer" },
            React.createElement("span", null, `Loaded ${iso}`),
            React.createElement("span", { className: "hud-alert" }, `No critical alerts • ${selectedMarker.priority} focus: ${selectedMarker.label}`)
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) {
    createRoot(rootEl).render(React.createElement(HudViewport));
}
