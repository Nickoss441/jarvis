const el = {
    seed: document.getElementById("seedText"),
    maxTurns: document.getElementById("maxTurns"),
    delayMs: document.getElementById("delayMs"),
    startAgent: document.getElementById("startAgent"),
    splitToggle: document.getElementById("splitToggle"),
    startBtn: document.getElementById("startBtn"),
    stopBtn: document.getElementById("stopBtn"),
    clearBtn: document.getElementById("clearBtn"),
    statusBar: document.getElementById("statusBar"),
    columns: document.getElementById("dialogueColumns"),
    jarvisCol: document.getElementById("jarvisCol"),
    evaCol: document.getElementById("evaCol"),
};

let pollTimer = null;

function setStatus(text) {
    el.statusBar.textContent = text;
}

function toggleSplit() {
    el.columns.classList.toggle("split-enabled", !!el.splitToggle.checked);
}

function formatTime(ts) {
    if (!ts) return "--:--:--";
    try {
        return new Date(ts).toLocaleTimeString();
    } catch (_) {
        return "--:--:--";
    }
}

function messageNode(item) {
    const box = document.createElement("div");
    const kindClass = item.kind === "error" ? "error" : (item.agent === "eva" ? "eva" : "jarvis");
    box.className = `dh-msg ${kindClass}`;
    const who = item.agent === "eva" ? "EVA" : (item.agent === "jarvis" ? "JARVIS" : "SYSTEM");
    box.textContent = `[${formatTime(item.ts)}] ${who}\n${item.text || ""}`;
    return box;
}

function render(state) {
    const messages = Array.isArray(state?.messages) ? state.messages : [];
    el.jarvisCol.innerHTML = "";
    el.evaCol.innerHTML = "";

    for (const item of messages) {
        if (item.agent === "eva") {
            el.evaCol.appendChild(messageNode(item));
        } else if (item.agent === "jarvis") {
            el.jarvisCol.appendChild(messageNode(item));
        }
    }

    el.jarvisCol.scrollTop = el.jarvisCol.scrollHeight;
    el.evaCol.scrollTop = el.evaCol.scrollHeight;

    const base = state?.running
        ? `Running turn ${state.turn}/${state.max_turns}`
        : `Stopped at turn ${state?.turn || 0}`;
    const err = state?.last_error ? ` | last error handled: ${state.last_error}` : "";
    setStatus(base + err);
}

async function fetchState() {
    try {
        const r = await fetch("/hud/dialogue/state", { cache: "no-store" });
        if (!r.ok) throw new Error(`state ${r.status}`);
        const state = await r.json();
        render(state);
    } catch (err) {
        setStatus(`State update error (recovered): ${err}`);
    }
}

async function startDialogue() {
    try {
        const payload = {
            seed: el.seed.value,
            max_turns: Number(el.maxTurns.value || 24),
            delay_ms: Number(el.delayMs.value || 1200),
            start_agent: el.startAgent.value,
        };
        const r = await fetch("/hud/dialogue/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const body = await r.json();
        if (!r.ok) throw new Error(body.error || `start ${r.status}`);
        render(body);
    } catch (err) {
        setStatus(`Start failed (handled): ${err}`);
    }
}

async function stopDialogue() {
    try {
        const r = await fetch("/hud/dialogue/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
        });
        const body = await r.json();
        if (!r.ok) throw new Error(body.error || `stop ${r.status}`);
        render(body);
    } catch (err) {
        setStatus(`Stop failed (handled): ${err}`);
    }
}

el.startBtn.addEventListener("click", startDialogue);
el.stopBtn.addEventListener("click", stopDialogue);
el.clearBtn.addEventListener("click", () => {
    el.jarvisCol.innerHTML = "";
    el.evaCol.innerHTML = "";
    setStatus("Screen cleared. Loop state remains on server.");
});
el.splitToggle.addEventListener("change", toggleSplit);

toggleSplit();
fetchState();
pollTimer = setInterval(fetchState, 1200);
window.addEventListener("beforeunload", () => {
    if (pollTimer) clearInterval(pollTimer);
});
