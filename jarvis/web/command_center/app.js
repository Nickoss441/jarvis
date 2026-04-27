import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

const ORBIT_RADIUS = 175;
const PANEL_W = 120;
const PANEL_H = 52;

const INNER_PANELS = [
    { label: "Social",   bars: [8, 14, 10, 18, 12, 16] },
    { label: "Markets",  bars: [18, 12, 8,  14, 16, 10] },
    { label: "Crypto",   bars: [10, 16, 14, 8,  18, 12] },
    { label: "Signals",  bars: [14, 10, 12, 16, 8,  18] },
    { label: "Comms",    bars: [16, 18, 10, 12, 14, 8]  },
    { label: "Feeds",    bars: [12, 8,  16, 10, 14, 18] },
];

const CHROME_TEXT =
    "SYSTEM ONLINE • NODE MESH ACTIVE • 7 AGENTS DEPLOYED • MONITORING GLOBAL FEEDS " +
    "• THREAT LEVEL: NOMINAL • BTCUSD $79,016 • OIL +1.8% • GOLD +3.2% " +
    "• SOCIAL +356 • P1 PROTOCOLS LOADED • [+] CROSSHAIR LOCK [+] ORBITAL COMMAND VIEWPORT " +
    "• 69% PROFITABLE • 2 EVENTS TO ATTEND • HOLD STEADY • ACCELERATING • ";

/* ── chrome bars ── */
function ChromeBar({ position }) {
    const full = CHROME_TEXT + CHROME_TEXT;
    return React.createElement(
        "div",
        { className: `cc-chrome ${position}` },
        React.createElement("span", { className: "cc-chrome-cross" }, "[+]"),
        React.createElement(
            "div",
            { className: "cc-chrome-scroll" },
            React.createElement("span", { className: "cc-chrome-scroll-inner" }, full)
        ),
        React.createElement("span", { className: "cc-chrome-cross" }, "[+]")
    );
}

/* ── reusable bar graph ── */
function BarGraph({ heights, color }) {
    const max = Math.max(...heights);
    return React.createElement(
        "div",
        { className: "cc-bar-graph" },
        ...heights.map((h, i) =>
            React.createElement("div", {
                key: i,
                className: "cc-bar",
                style: {
                    height: `${Math.round((h / max) * 34)}px`,
                    background: color,
                    boxShadow: `0 0 5px ${color}`,
                },
            })
        )
    );
}

/* ── bitcoin sparkline ── */
function BitcoinChart() {
    const linePts = "M0,55 L15,47 L30,50 L45,34 L60,29 L75,17 L90,11 L105,6 L120,3";
    const fillPts = `${linePts} L120,60 L0,60 Z`;
    return React.createElement(
        "div",
        { className: "cc-chart" },
        React.createElement(
            "svg",
            { viewBox: "0 0 120 60", preserveAspectRatio: "none" },
            React.createElement(
                "defs",
                null,
                React.createElement(
                    "linearGradient",
                    { id: "btcFill", x1: "0%", y1: "0%", x2: "0%", y2: "100%" },
                    React.createElement("stop", { offset: "0%", stopColor: "#00ff00", stopOpacity: "0.32" }),
                    React.createElement("stop", { offset: "100%", stopColor: "#00ff00", stopOpacity: "0" })
                )
            ),
            React.createElement("path", { d: fillPts, fill: "url(#btcFill)" }),
            React.createElement("path", {
                d: linePts,
                fill: "none",
                stroke: "#00ff00",
                strokeWidth: "1.5",
                style: { filter: "drop-shadow(0 0 4px #00ff00)" },
            })
        )
    );
}

/* ── four corner HUD panels ── */
function SocialPanel() {
    return React.createElement(
        "div",
        { className: "cc-panel top-left" },
        React.createElement("div", { className: "cc-panel-title" }, "Social Monitoring"),
        React.createElement("div", { className: "cc-panel-number" }, "+356"),
        React.createElement("div", { className: "cc-panel-sub" }, "Accelerating"),
        React.createElement("div", { className: "cc-panel-sub" }, "New Opportunities"),
        React.createElement(BarGraph, {
            heights: [22, 38, 28, 48, 32, 52, 40, 44],
            color: "rgba(0,255,255,0.65)",
        })
    );
}

function BitcoinPanel() {
    return React.createElement(
        "div",
        { className: "cc-panel bottom-left" },
        React.createElement("div", { className: "cc-panel-title" }, "Bitcoin"),
        React.createElement("div", { className: "cc-panel-number" }, "$79,016"),
        React.createElement(BitcoinChart),
        React.createElement("div", { className: "cc-panel-sub", style: { marginTop: 5 } }, "Hold Steady")
    );
}

function TradingPanel() {
    return React.createElement(
        "div",
        { className: "cc-panel top-right" },
        React.createElement(
            "div",
            { className: "cc-title-row" },
            React.createElement("div", { className: "cc-panel-title" }, "Oil & Gold"),
            React.createElement("span", { className: "cc-badge green" }, "+3.2%")
        ),
        React.createElement("div", { className: "cc-profit" }, "69% Profitable"),
        React.createElement(
            "div",
            { className: "cc-badge-row", style: { marginTop: 8 } },
            React.createElement("span", { className: "cc-badge cyan" }, "Active"),
            React.createElement("span", { className: "cc-badge hot" }, "Hot")
        ),
        React.createElement(BarGraph, {
            heights: [28, 42, 35, 52, 38, 48, 55, 44],
            color: "rgba(0,200,100,0.6)",
        })
    );
}

function StrategyPanel() {
    return React.createElement(
        "div",
        { className: "cc-panel bottom-right" },
        React.createElement("div", { className: "cc-panel-title" }, "Tracking / Strategy"),
        React.createElement("div", { className: "cc-panel-number" }, "2"),
        React.createElement("div", { className: "cc-event-sub" }, "Events to Attend"),
        React.createElement(
            "div",
            { className: "cc-badge-row", style: { marginTop: 10 } },
            React.createElement("span", { className: "cc-badge cyan" }, "Today"),
            React.createElement("span", { className: "cc-badge green" }, "Confirmed")
        )
    );
}

/* ── radar core ── */
function RadarCore() {
    return React.createElement(
        React.Fragment,
        null,
        React.createElement("div", { className: "cc-radar-ring" }),
        React.createElement("div", { className: "cc-radar-ring" }),
        React.createElement("div", { className: "cc-radar-ring" }),
        React.createElement(
            "div",
            { className: "cc-radar-core" },
            React.createElement("div", { className: "cc-radar-sweep" }),
            React.createElement("div", { className: "cc-radar-crosshair-h" }),
            React.createElement("div", { className: "cc-radar-crosshair-v" })
        )
    );
}

/* ── orbit mini panel ── */
function OrbitPanel({ index, total, data }) {
    const angle = (index / total) * Math.PI * 2 - Math.PI / 2;
    const cx = Math.round(Math.cos(angle) * ORBIT_RADIUS);
    const cy = Math.round(Math.sin(angle) * ORBIT_RADIUS);
    const maxH = Math.max(...data.bars);
    return React.createElement(
        "div",
        {
            className: "cc-orbit-panel",
            style: {
                left: 0,
                top: 0,
                transform: `translate(${cx - PANEL_W / 2}px, ${cy - PANEL_H / 2}px)`,
            },
        },
        React.createElement("div", { className: "cc-orbit-label" }, data.label),
        React.createElement(
            "div",
            { className: "cc-orbit-bars" },
            ...data.bars.map((h, i) =>
                React.createElement("div", {
                    key: i,
                    className: "cc-orbit-bar",
                    style: { height: `${Math.round((h / maxH) * 20)}px` },
                })
            )
        )
    );
}

/* ── center core + orbit ── */
function CenterCore() {
    return React.createElement(
        "div",
        { className: "cc-center-wrapper" },
        React.createElement(RadarCore),
        ...INNER_PANELS.map((panel, i) =>
            React.createElement(OrbitPanel, {
                key: panel.label,
                index: i,
                total: INNER_PANELS.length,
                data: panel,
            })
        )
    );
}

/* ── root ── */
function CommandCenter() {
    return React.createElement(
        React.Fragment,
        null,
        React.createElement("div", { className: "cc-bg" }),
        React.createElement(ChromeBar, { position: "top" }),
        React.createElement(ChromeBar, { position: "bottom" }),
        React.createElement(
            "div",
            { className: "cc-root" },
            React.createElement(CenterCore),
            React.createElement(SocialPanel),
            React.createElement(BitcoinPanel),
            React.createElement(TradingPanel),
            React.createElement(StrategyPanel)
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) {
    createRoot(rootEl).render(React.createElement(CommandCenter));
}
