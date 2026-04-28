const QUICK_LINKS = [
    { label: "Strategic Globe", href: "/hud/react" },
    { label: "Command Center", href: "/hud/cc" },
    { label: "Ops Wallboard", href: "/hud/ops" },
    { label: "Approvals", href: "/" },
];

const SUGGESTIONS = [
    "Show open approvals",
    "Focus the globe on my home",
    "Open command center",
    "Summarize active system state",
];

const STARTUP_STEPS = [
    { label: "Hello. I'm Jarvis.", delay: 260 },
    { label: "Turning on all systems.", delay: 980 },
    { label: "Linking voice and orbital interfaces.", delay: 1720 },
    { label: "Home surface online.", delay: 2480 },
];

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string") node.textContent = text;
    return node;
}

function addMessage(container, role, text) {
    const item = el("div", `jh-msg jh-msg-${role}`);
    const meta = el("div", "jh-msg-meta", role === "user" ? "YOU" : "JARVIS");
    const body = el("div", "jh-msg-body", text);
    item.append(meta, body);
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

function setSpeaking(shell, on) {
    shell.classList.toggle("is-speaking", on);
}

const app = document.getElementById("app");
const shell = el("div", "jh-shell");
shell.classList.add("is-startup");
const sidebar = el("aside", "jh-sidebar");
const brand = el("div", "jh-brand");
brand.innerHTML = "<span>Jarvis</span><strong>Home</strong>";
const sideCopy = el("p", "jh-sidecopy", "A single landing page for globe-first interaction, quick navigation, and voice-style chat flow.");
const nav = el("nav", "jh-nav");
QUICK_LINKS.forEach((item) => {
    const link = el("a", "jh-nav-link", item.label);
    link.href = item.href;
    nav.appendChild(link);
});
const sideFoot = el("div", "jh-sidefoot", "Sidebar splits navigation from the main Jarvis interaction surface.");
sidebar.append(brand, sideCopy, nav, sideFoot);

const main = el("main", "jh-main");
const hero = el("section", "jh-hero");
const heroHeader = el("div", "jh-hero-header");
const heroEyebrow = el("div", "jh-eyebrow", "Jarvis Only");
const heroTitle = el("h1", "jh-title", "Voice-first globe landing view");
const heroSub = el("p", "jh-sub", "The globe is the main character here. When Jarvis speaks, the stage wakes up and the interface leans into the conversation.");
heroHeader.append(heroEyebrow, heroTitle, heroSub);

const stage = el("div", "jh-stage");
const stageHud = el("div", "jh-stage-hud");
const pulse = el("div", "jh-pulse");
const pulseLabel = el("div", "jh-pulse-label", "VOICE LINK");
const status = el("div", "jh-stage-status");
status.innerHTML = "<span class='jh-dot'></span><span id='jh-status-text'>Listening</span>";
stageHud.append(pulse, pulseLabel, status);
const iframeWrap = el("div", "jh-iframe-wrap");
const globeFrame = document.createElement("iframe");
globeFrame.src = "/hud/react";
globeFrame.title = "Jarvis Globe";
iframeWrap.appendChild(globeFrame);
stage.append(stageHud, iframeWrap);
hero.append(heroHeader, stage);

const chat = el("section", "jh-chat");
const chatHeader = el("div", "jh-chat-header");
chatHeader.innerHTML = "<div><div class='jh-chat-kicker'>Conversation</div><h2 class='jh-chat-title'>Chat dock</h2></div><div class='jh-chat-hint'>Press Enter to send</div>";
const suggestions = el("div", "jh-suggestions");
const transcript = el("div", "jh-transcript");
transcript.setAttribute("aria-live", "polite");
addMessage(transcript, "jarvis", "Home surface ready. Ask for a route, a system summary, or globe focus.");
const composer = el("form", "jh-composer");
const input = document.createElement("textarea");
input.className = "jh-input";
input.rows = 2;
input.placeholder = "Talk to Jarvis...";
const actions = el("div", "jh-actions");
const mic = document.createElement("button");
mic.type = "button";
mic.className = "jh-btn jh-btn-secondary";
mic.textContent = "Simulate Voice";
const send = document.createElement("button");
send.type = "submit";
send.className = "jh-btn jh-btn-primary";
send.textContent = "Send";
actions.append(mic, send);
composer.append(input, actions);
chat.append(chatHeader, suggestions, transcript, composer);

SUGGESTIONS.forEach((label) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "jh-suggestion";
    btn.textContent = label;
    btn.addEventListener("click", () => {
        input.value = label;
        input.focus();
    });
    suggestions.appendChild(btn);
});

function speakCycle(userText) {
    const statusText = document.getElementById("jh-status-text");
    setSpeaking(shell, true);
    if (statusText) statusText.textContent = "Speaking";
    window.setTimeout(() => {
        addMessage(transcript, "jarvis", `Routing: ${userText}. Home page framework is ready for deeper Jarvis chat wiring.`);
        setSpeaking(shell, false);
        if (statusText) statusText.textContent = "Listening";
    }, 1400);
}

composer.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(transcript, "user", text);
    input.value = "";
    speakCycle(text);
});

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        composer.requestSubmit();
    }
});

mic.addEventListener("click", () => {
    addMessage(transcript, "user", "Voice simulation requested.");
    speakCycle("voice simulation");
});

main.append(hero, chat);
shell.append(sidebar, main);
app.appendChild(shell);

const startup = el("div", "jh-startup");
const startupInner = el("div", "jh-startup-inner");
const startupEyebrow = el("div", "jh-startup-eyebrow", "System Boot");
const startupTitle = el("div", "jh-startup-title", "JARVIS");
const startupSub = el("div", "jh-startup-sub", "Hello, I'm Jarvis. Turning on all systems and preparing your globe-first home surface.");
const startupProgress = el("div", "jh-startup-progress");
const startupBar = el("div", "jh-startup-bar");
const startupFill = el("div", "jh-startup-fill");
startupBar.appendChild(startupFill);
const startupLog = el("div", "jh-startup-log");
const startupSkip = document.createElement("button");
startupSkip.type = "button";
startupSkip.className = "jh-startup-skip";
startupSkip.textContent = "Skip intro";
startupProgress.append(startupBar, startupLog);
startupInner.append(startupEyebrow, startupTitle, startupSub, startupProgress, startupSkip);
startup.appendChild(startupInner);
app.appendChild(startup);

let startupClosed = false;
function finishStartup() {
    if (startupClosed) return;
    startupClosed = true;
    shell.classList.remove("is-startup");
    startup.classList.add("is-leaving");
    window.setTimeout(() => {
        startup.remove();
    }, 700);
}

STARTUP_STEPS.forEach((step, index) => {
    window.setTimeout(() => {
        if (startupClosed) return;
        startupLog.textContent = step.label;
        startupFill.style.width = `${((index + 1) / STARTUP_STEPS.length) * 100}%`;
        if (index === STARTUP_STEPS.length - 1) {
            startup.classList.add("is-complete");
            window.setTimeout(finishStartup, 900);
        }
    }, step.delay);
});

startupSkip.addEventListener("click", finishStartup);
