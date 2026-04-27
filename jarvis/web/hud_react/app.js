import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import * as THREE from "https://esm.sh/three@0.167.1";

const GLOBE_MARKERS = [
    {
        id: "hormuz",
        label: "Strait of Hormuz",
        lat: 26.56,
        lon: 56.25,
        color: 0xff7b95,
        region: "Maritime chokepoint",
        threat: "Elevated",
        status: "Monitoring tanker lane volatility and escort posture.",
        agents: 7,
        confidence: "91%",
        priority: "P1",
        window: "06m",
        feeds: ["AIS", "Brent", "LNG", "Maritime SIGINT"],
        protocols: ["Reroute hedges", "Escalation review", "Supply shock watch"],
    },
    {
        id: "kabul",
        label: "Kabul",
        lat: 34.5553,
        lon: 69.2075,
        color: 0xffd166,
        region: "Regional stability node",
        threat: "Guarded",
        status: "Tracking diplomatic movement, air corridor chatter, and aid logistics.",
        agents: 4,
        confidence: "84%",
        priority: "P2",
        window: "11m",
        feeds: ["Flight radar", "OSINT", "Embassy cable", "News delta"],
        protocols: ["Aid routing", "Travel hold", "Narrative watch"],
    },
    {
        id: "djibouti",
        label: "Djibouti",
        lat: 11.5721,
        lon: 43.1456,
        color: 0x53e6c1,
        region: "Port relay",
        threat: "Stable",
        status: "Observing Red Sea spillover and port throughput anomalies.",
        agents: 5,
        confidence: "88%",
        priority: "P2",
        window: "14m",
        feeds: ["Port ops", "Shipping queue", "FX spread"],
        protocols: ["Harbor alert", "Convoy timing", "Insurance spread"],
    },
    {
        id: "singapore",
        label: "Singapore",
        lat: 1.3521,
        lon: 103.8198,
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
];

const GLOBE_CONNECTIONS = [
    ["hormuz", "djibouti"],
    ["hormuz", "singapore"],
    ["kabul", "djibouti"],
    ["kabul", "singapore"],
];

const ACTIVE_AGENTS = ["Planner", "Trader", "Comms"];
const SOCIAL_MISSION_WIDGETS = [
    { id: "education", title: "Education Fund", impact: "42 grants", progress: 68 },
    { id: "microcredit", title: "Microcredit Pool", impact: "$84k deployed", progress: 54 },
    { id: "food", title: "Food Relief", impact: "1,920 meals", progress: 81 },
];

function latLonToVector3(latDeg, lonDeg, radius) {
    const lat = (latDeg * Math.PI) / 180;
    const lon = (lonDeg * Math.PI) / 180;
    const x = radius * Math.cos(lat) * Math.sin(lon);
    const y = radius * Math.sin(lat);
    const z = radius * Math.cos(lat) * Math.cos(lon);
    return new THREE.Vector3(x, y, z);
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

function FinancialSocialMissionWidgets() {
    return React.createElement(
        "section",
        { className: "hud-mission-grid", "aria-label": "Financial social mission widgets" },
        ...SOCIAL_MISSION_WIDGETS.map((widget) =>
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

function GlobeLayer({ onMarkerSelect, selectedMarkerId }) {
    const containerRef = React.useRef(null);

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
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height);
        container.appendChild(renderer.domElement);

        const root = new THREE.Group();
        scene.add(root);

        const coreSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.02, 48, 48),
            new THREE.MeshPhongMaterial({
                color: 0x0d2740,
                emissive: 0x052235,
                emissiveIntensity: 1.4,
                transparent: true,
                opacity: 0.92,
                shininess: 24,
            })
        );
        root.add(coreSphere);

        const wireSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.06, 48, 48),
            new THREE.MeshBasicMaterial({
                color: 0x5bc8ff,
                wireframe: true,
                transparent: true,
                opacity: 0.34,
            })
        );
        root.add(wireSphere);

        const glowSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.18, 48, 48),
            new THREE.MeshBasicMaterial({
                color: 0x62d8ff,
                transparent: true,
                opacity: 0.12,
                side: THREE.BackSide,
            })
        );
        root.add(glowSphere);

        scene.add(new THREE.AmbientLight(0x69d0ff, 1.5));
        const rimLight = new THREE.PointLight(0x5bc8ff, 2.6, 12);
        rimLight.position.set(3.4, 2.5, 4.2);
        scene.add(rimLight);
        const pinkLight = new THREE.PointLight(0xff6688, 1.2, 9);
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

        const starGeometry = new THREE.BufferGeometry();
        const starData = [];
        for (let i = 0; i < 220; i += 1) {
            const phi = Math.random() * Math.PI * 2;
            const costheta = Math.random() * 2 - 1;
            const theta = Math.acos(costheta);
            const radius = 1.45 + Math.random() * 0.4;
            starData.push(
                radius * Math.sin(theta) * Math.cos(phi),
                radius * Math.sin(theta) * Math.sin(phi),
                radius * Math.cos(theta)
            );
        }
        starGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starData, 3));
        const stars = new THREE.Points(
            starGeometry,
            new THREE.PointsMaterial({ color: 0xb7efff, size: 0.02, transparent: true, opacity: 0.75 })
        );
        scene.add(stars);

        const connectionsGroup = new THREE.Group();
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
        scene.add(connectionsGroup);

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

        const selectedRing = new THREE.Mesh(
            new THREE.TorusGeometry(0.11, 0.008, 12, 48),
            new THREE.MeshBasicMaterial({ color: selectedMarker.color, transparent: true, opacity: 0.92 })
        );
        selectedRing.position.copy(latLonToVector3(selectedMarker.lat, selectedMarker.lon, 1.12));
        selectedRing.lookAt(new THREE.Vector3(0, 0, 0));
        root.add(selectedRing);

        const raycaster = new THREE.Raycaster();
        const pointer = new THREE.Vector2();
        let rafId = 0;

        const animate = () => {
            const time = performance.now() * 0.001;
            root.rotation.y += 0.0028;
            wireSphere.rotation.y += 0.0015;
            glowSphere.rotation.y -= 0.0011;
            stars.rotation.y += 0.00045;
            connectionsGroup.children.forEach((line, idx) => {
                line.material.opacity = 0.16 + (Math.sin(time * 1.8 + idx) + 1) * 0.09;
            });
            markerGroup.children.forEach((anchor, idx) => {
                const pulse = 1 + Math.sin(time * 2.4 + idx) * 0.16;
                const isSelected = anchor.name === selectedMarkerId;
                anchor.userData.halo.scale.setScalar(isSelected ? pulse * 1.45 : pulse);
                anchor.userData.halo.material.opacity = isSelected ? 0.34 : 0.16;
                anchor.userData.shell.scale.setScalar(isSelected ? 1.28 : 1);
            });
            selectedRing.rotation.z += 0.02;
            renderer.render(scene, camera);
            rafId = requestAnimationFrame(animate);
        };
        animate();

        const onResize = () => {
            const nextWidth = Math.max(300, container.clientWidth || width);
            const nextHeight = Math.max(360, container.clientHeight || height);
            renderer.setSize(nextWidth, nextHeight);
            camera.aspect = nextWidth / nextHeight;
            camera.updateProjectionMatrix();
        };
        window.addEventListener("resize", onResize);

        const onClick = (event) => {
            const rect = renderer.domElement.getBoundingClientRect();
            if (!rect.width || !rect.height) {
                return;
            }
            pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(pointer, camera);
            const hits = raycaster.intersectObjects(markerGroup.children, true);
            const hit = hits.find((item) => item.object?.parent?.userData?.id || item.object?.userData?.id);
            const markerData = hit?.object?.parent?.userData?.id ? hit.object.parent.userData : hit?.object?.userData;
            if (markerData?.id && onMarkerSelect) {
                onMarkerSelect(GLOBE_MARKERS.find((item) => item.id === markerData.id) || markerData);
            }
        };
        renderer.domElement.addEventListener("click", onClick);

        return () => {
            window.removeEventListener("resize", onResize);
            renderer.domElement.removeEventListener("click", onClick);
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
    }, [onMarkerSelect, selectedMarkerId]);

    return React.createElement(
        "section",
        { className: "globe-frame", role: "img", "aria-label": "Three dimensional globe layer" },
        React.createElement("div", { className: "globe-status-chip" }, "Strategic Mesh Online"),
        React.createElement("div", { className: "globe-scanline" }),
        React.createElement("div", { ref: containerRef, className: "globe-canvas" })
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
    const [activeAgentIndex, setActiveAgentIndex] = React.useState(0);
    const [dialogueRows, setDialogueRows] = React.useState([]);
    const [dialogueLoading, setDialogueLoading] = React.useState(true);
    const [dialogueError, setDialogueError] = React.useState("");
    const iso = new Date().toISOString();

    React.useEffect(() => {
        const timer = window.setInterval(() => {
            setActiveAgentIndex((current) => (current + 1) % ACTIVE_AGENTS.length);
        }, 1400);
        return () => window.clearInterval(timer);
    }, []);

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
        React.createElement("div", { className: "hud-eyebrow" }, "Orbital command viewport"),
        React.createElement("h1", { className: "hud-title" }, "Jarvis Strategic Globe"),
        React.createElement("p", { className: "hud-subline" }, "Live node selection, tactical feed stack, and high-contrast HUD overlays anchored to the current React surface."),
        React.createElement(CommandDeck, { marker: selectedMarker }),
        React.createElement(MarkerRibbon, {
            markers: GLOBE_MARKERS,
            selectedId: selectedMarker.id,
            onSelect: setSelectedMarker,
        }),
        React.createElement(
            "div",
            { className: "hud-theatre" },
            React.createElement(
                "section",
                { className: "hud-main-column" },
                React.createElement(GlobeLayer, { onMarkerSelect: setSelectedMarker, selectedMarkerId: selectedMarker.id }),
                React.createElement("div", { className: "hud-footnotes" }, `Node mesh: ${GLOBE_MARKERS.map((item) => item.label).join(" • ")}`),
                React.createElement(BurstWidgetStrip),
                React.createElement(ActiveAgentLoop, { activeIndex: activeAgentIndex })
            ),
            React.createElement(
                "section",
                { className: "hud-side-column" },
                React.createElement(SlidePanel, { marker: selectedMarker }),
                React.createElement(DialogueDatasetPanel, {
                    rows: dialogueRows,
                    loading: dialogueLoading,
                    error: dialogueError,
                }),
                React.createElement(FinancialSocialMissionWidgets)
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
