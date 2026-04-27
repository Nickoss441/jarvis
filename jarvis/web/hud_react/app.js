import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";

function MetricCard({ label, value }) {
    return React.createElement(
        "section",
        { className: "hud-card" },
        React.createElement("div", { className: "hud-label" }, label),
        React.createElement("div", { className: "hud-value" }, value)
    );
}

function HudViewport() {
    const now = new Date();
    const iso = now.toISOString();

    return React.createElement(
        "main",
        { className: "hud-shell" },
        React.createElement("h1", { className: "hud-title" }, "Jarvis React HUD"),
        React.createElement(
            "p",
            { className: "hud-subline" },
            "Viewport scaffold online for upcoming Three.js globe and marker wiring."
        ),
        React.createElement(
            "div",
            { className: "hud-grid" },
            React.createElement(MetricCard, { label: "Active Agents", value: "03" }),
            React.createElement(MetricCard, { label: "Pending Approvals", value: "00" }),
            React.createElement(MetricCard, { label: "Runtime Mode", value: "paper" }),
            React.createElement(MetricCard, { label: "Viewport Rev", value: "v0" })
        ),
        React.createElement(
            "div",
            { className: "hud-footer" },
            React.createElement("span", null, `Loaded ${iso}`),
            React.createElement("span", { className: "hud-alert" }, "No critical alerts")
        )
    );
}

const rootEl = document.getElementById("root");
if (rootEl) {
    createRoot(rootEl).render(React.createElement(HudViewport));
}
