const SURFACES = [
    {
        id: "globe",
        label: "Strategic Globe",
        href: "/hud/react",
        tag: "Live Sphere",
        summary: "Trade lanes, threat mesh, and planetary telemetry.",
        signal: "Nominal",
        latency: "42 ms",
        uptime: "99.98%",
        route: "Transit / Risk",
    },
    {
        id: "cc",
        label: "Command Center",
        href: "/hud/cc",
        tag: "Operations Core",
        summary: "Runtime health, controls, and execution boards.",
        signal: "Monitoring",
        latency: "58 ms",
        uptime: "99.92%",
        route: "Runtime / Control",
    },
    {
        id: "ops",
        label: "Ops Wallboard",
        href: "/hud/ops",
        tag: "Wall Mode",
        summary: "Single-screen ambient watch mode for status at a glance.",
        signal: "Standby",
        latency: "37 ms",
        uptime: "99.99%",
        route: "Status / Overview",
    },
];

const BOOT_LINES = [
    "Authenticating command mesh",
    "Syncing launch deck telemetry",
    "Wiring strategic surface routes",
    "Calibrating control channels",
    "Jarvis launch deck online",
];

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string") node.textContent = text;
    return node;
}

function signalClass(signal) {
    if (signal === "Monitoring") return "is-monitoring";
    if (signal === "Standby") return "is-standby";
    return "is-nominal";
}

const app = document.getElementById("app");
const currentPath = window.location.pathname;

const shell = el("div", "lh-shell");

const mast = el("header", "lh-mast");
const backBtn = document.createElement("button");
backBtn.type = "button";
backBtn.className = "lh-back-btn";
backBtn.textContent = "Back";
backBtn.addEventListener("click", () => {
    if (window.history.length > 1) {
        window.history.back();
        return;
    }
    window.location.href = "/";
});

const mastMain = el("div", "lh-mast-main");
const eyebrow = el("div", "lh-kick", "Jarvis Landing");
const title = el("h1", "lh-title", "Surface Launch Deck");
const sub = el("p", "lh-sub", "Switch between your three live HUD surfaces with direct navigation and mission context in one place.");
mastMain.append(eyebrow, title, sub);

const mastMeta = el("div", "lh-mast-meta");
const linkState = el("div", "lh-live");
linkState.innerHTML = "<span class='lh-live-dot'></span><span>Link Stable</span>";
const clock = el("div", "lh-clock");
const updateClock = () => {
    const now = new Date();
    clock.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};
updateClock();
window.setInterval(updateClock, 1000);
mastMeta.append(linkState, clock);
mast.append(backBtn, mastMain, mastMeta);

const layout = el("div", "lh-layout");

// --- Jarvis Animated Core ---
const jarvisCore = document.createElement("div");
jarvisCore.className = "jarvis-animated-core";
const pulse1 = document.createElement("div");
pulse1.className = "jarvis-pulse";
const pulse2 = document.createElement("div");
pulse2.className = "jarvis-pulse";
pulse2.style.animationDelay = "1.1s";
const coreDot = document.createElement("div");
coreDot.className = "jarvis-core-dot";
jarvisCore.appendChild(pulse1);
jarvisCore.appendChild(pulse2);
jarvisCore.appendChild(coreDot);
layout.appendChild(jarvisCore);
const rail = el("aside", "lh-rail");
const railTitle = el("div", "lh-rail-title", "Launch Surfaces");
const railMeta = el("div", "lh-rail-meta");
railMeta.innerHTML = `<span>${SURFACES.length} routes</span><span>Direct link mode</span>`;
const launchList = el("nav", "lh-launch-list");

SURFACES.forEach((surface) => {
    const link = document.createElement("a");
    link.href = surface.href;
    link.className = "lh-launch";
    if (currentPath === surface.href) {
        link.classList.add("is-active");
        link.setAttribute("aria-current", "page");
    }
    link.innerHTML = `<span class="lh-launch-label">${surface.label}</span><span class="lh-launch-tag">${surface.tag}</span>`;
    launchList.appendChild(link);
});

const railHint = el("p", "lh-rail-hint", "Sidebar tabs open each surface directly in this tab.");
rail.append(railTitle, railMeta, launchList, railHint);

const main = el("main", "lh-main");
const hero = el("section", "lh-hero");
const heroKicker = el("div", "lh-hero-kicker", "Command Routing");
const heroTitle = el("div", "lh-hero-title", "Direct Surface Launch");
const heroSub = el("p", "lh-hero-sub", "Pick a surface below. No embedded windows. The page routes straight into the target HUD.");
const heroStats = el("div", "lh-hero-stats");
heroStats.innerHTML = `
    <div class="lh-hero-stat"><span>Routes</span><strong>${SURFACES.length}</strong></div>
    <div class="lh-hero-stat"><span>Protocol</span><strong>Direct</strong></div>
    <div class="lh-hero-stat"><span>Session</span><strong>Stable</strong></div>
`;
const heroActions = el("div", "lh-hero-actions");
const primary = document.createElement("a");
primary.href = "/hud/react";
primary.className = "lh-btn lh-btn-primary";
primary.textContent = "Open Globe";
const secondary = document.createElement("a");
secondary.href = "/hud/ops";
secondary.className = "lh-btn lh-btn-secondary";
secondary.textContent = "Open Wallboard";
heroActions.append(primary, secondary);
hero.append(heroKicker, heroTitle, heroSub, heroStats, heroActions);

const cards = el("section", "lh-cards");
SURFACES.forEach((surface) => {
    const card = document.createElement("a");
    card.href = surface.href;
    card.className = "lh-card";
    card.setAttribute("data-route", surface.id);
    card.innerHTML = `
        <div class="lh-card-top">
            <span class="lh-card-label-wrap">
                <span class="lh-card-label">${surface.label}</span>
                <span class="lh-card-route">${surface.route}</span>
            </span>
            <span class="lh-card-signal ${signalClass(surface.signal)}">${surface.signal}</span>
        </div>
        <div class="lh-card-tag">${surface.tag}</div>
        <p class="lh-card-summary">${surface.summary}</p>
        <div class="lh-card-metrics">
            <span>Latency <strong>${surface.latency}</strong></span>
            <span>Uptime <strong>${surface.uptime}</strong></span>
        </div>
        <span class="lh-card-open">Open Surface</span>
    `;
    cards.appendChild(card);
});

const utility = el("section", "lh-utility");
const notes = el("article", "lh-note");
notes.innerHTML = "<div class='lh-note-title'>System Notes</div><p>Use this deck as the default entry point. Launch decisions stay quick, consistent, and phone-friendly.</p>";
const quick = el("article", "lh-note");
const quickTitle = el("div", "lh-note-title", "Quick Launch");
const quickList = el("div", "lh-quick-list");
SURFACES.forEach((surface) => {
    const link = document.createElement("a");
    link.href = surface.href;
    link.className = "lh-quick-link";
    link.textContent = surface.label;
    quickList.appendChild(link);
});
quick.append(quickTitle, quickList);
utility.append(notes, quick);

main.append(hero, cards, utility);
layout.append(rail, main);
shell.append(mast, layout);
app.appendChild(shell);

const boot = el("div", "lh-boot");
const bootInner = el("div", "lh-boot-inner");
const bootEyebrow = el("div", "lh-boot-eyebrow", "Jarvis Core");
const bootTop = el("div", "lh-boot-top");
const bootRing = el("div", "lh-boot-ring");
const bootTitleWrap = el("div", "lh-boot-title-wrap");
const bootTitle = el("div", "lh-boot-title", "Initializing Launch Deck");
const bootPercent = el("div", "lh-boot-percent", "0%");
bootTitleWrap.append(bootTitle, bootPercent);
bootTop.append(bootRing, bootTitleWrap);
const bootBar = el("div", "lh-boot-bar");
const bootFill = el("div", "lh-boot-fill");
bootBar.appendChild(bootFill);
const bootLine = el("div", "lh-boot-line", BOOT_LINES[0]);
const bootSub = el("div", "lh-boot-sub", "Preparing tactical interfaces");
const bootSkip = document.createElement("button");
bootSkip.type = "button";
bootSkip.className = "lh-boot-skip";
bootSkip.textContent = "Skip";
bootInner.append(bootEyebrow, bootTop, bootBar, bootLine, bootSub, bootSkip);
boot.appendChild(bootInner);
app.appendChild(boot);

let bootClosed = false;
function closeBoot() {
    if (bootClosed) return;
    bootClosed = true;
    boot.classList.add("is-leaving");
    window.setTimeout(() => {
        boot.remove();
        // Redirect to Jarvis Command Center after boot animation
        window.location.href = "/hud/cc";
    }, 500);
}

BOOT_LINES.forEach((line, idx) => {
    window.setTimeout(() => {
        if (bootClosed) return;
        bootLine.textContent = line;
        const pct = Math.round(((idx + 1) / BOOT_LINES.length) * 100);
        bootFill.style.width = `${pct}%`;
        bootPercent.textContent = `${pct}%`;
        if (idx === BOOT_LINES.length - 1) {
            window.setTimeout(closeBoot, 420);
        }
    }, 320 + idx * 520);
});

bootSkip.addEventListener("click", closeBoot);
