import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import * as THREE from "https://esm.sh/three@0.167.1";

const GLOBE_MARKERS = [
    { id: "hormuz", label: "Hormuz", lat: 26.56, lon: 56.25, color: 0xff7b95 },
    { id: "kabul", label: "Kabul", lat: 34.5553, lon: 69.2075, color: 0xffd166 },
];

function latLonToVector3(latDeg, lonDeg, radius) {
    const lat = (latDeg * Math.PI) / 180;
    const lon = (lonDeg * Math.PI) / 180;
    const x = radius * Math.cos(lat) * Math.sin(lon);
    const y = radius * Math.sin(lat);
    const z = radius * Math.cos(lat) * Math.cos(lon);
    return new THREE.Vector3(x, y, z);
}

function MetricCard({ label, value }) {
    return React.createElement(
        "section",
        { className: "hud-card" },
        React.createElement("div", { className: "hud-label" }, label),
        React.createElement("div", { className: "hud-value" }, value)
    );
}

function GlobeLayer() {
    const containerRef = React.useRef(null);

    React.useEffect(() => {
        const container = containerRef.current;
        if (!container) {
            return undefined;
        }

        const width = Math.max(240, container.clientWidth || 240);
        const height = 280;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        camera.position.z = 3.2;

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(width, height);
        container.appendChild(renderer.domElement);

        const sphereGeometry = new THREE.SphereGeometry(1.05, 40, 40);
        const sphereMaterial = new THREE.MeshBasicMaterial({
            color: 0x2fd1ff,
            wireframe: true,
            transparent: true,
            opacity: 0.6,
        });
        const globe = new THREE.Mesh(sphereGeometry, sphereMaterial);
        scene.add(globe);

        const glowGeometry = new THREE.SphereGeometry(1.16, 40, 40);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0x68deff,
            transparent: true,
            opacity: 0.15,
            side: THREE.BackSide,
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        scene.add(glow);

        const pointsGeometry = new THREE.BufferGeometry();
        const starData = [];
        for (let i = 0; i < 120; i += 1) {
            const phi = Math.random() * Math.PI * 2;
            const costheta = Math.random() * 2 - 1;
            const theta = Math.acos(costheta);
            const radius = 1.22;
            const x = radius * Math.sin(theta) * Math.cos(phi);
            const y = radius * Math.sin(theta) * Math.sin(phi);
            const z = radius * Math.cos(theta);
            starData.push(x, y, z);
        }
        pointsGeometry.setAttribute("position", new THREE.Float32BufferAttribute(starData, 3));
        const pointsMaterial = new THREE.PointsMaterial({
            color: 0x9fefff,
            size: 0.025,
            transparent: true,
            opacity: 0.95,
        });
        const points = new THREE.Points(pointsGeometry, pointsMaterial);
        scene.add(points);

        const markerGroup = new THREE.Group();
        markerGroup.name = "geo_markers";
        GLOBE_MARKERS.forEach((marker) => {
            const markerGeometry = new THREE.SphereGeometry(0.04, 14, 14);
            const markerMaterial = new THREE.MeshBasicMaterial({
                color: marker.color,
                transparent: true,
                opacity: 0.96,
            });
            const markerMesh = new THREE.Mesh(markerGeometry, markerMaterial);
            markerMesh.position.copy(latLonToVector3(marker.lat, marker.lon, 1.08));
            markerMesh.name = marker.id;
            markerMesh.userData = { ...marker };
            markerGroup.add(markerMesh);
        });
        scene.add(markerGroup);

        let rafId = 0;
        const animate = () => {
            globe.rotation.y += 0.0035;
            globe.rotation.x += 0.0008;
            glow.rotation.y -= 0.0023;
            points.rotation.y += 0.0017;
            markerGroup.rotation.y += 0.0035;
            renderer.render(scene, camera);
            rafId = requestAnimationFrame(animate);
        };
        animate();

        const onResize = () => {
            const nextWidth = Math.max(240, container.clientWidth || width);
            renderer.setSize(nextWidth, height);
            camera.aspect = nextWidth / height;
            camera.updateProjectionMatrix();
        };
        window.addEventListener("resize", onResize);

        return () => {
            window.removeEventListener("resize", onResize);
            cancelAnimationFrame(rafId);
            pointsGeometry.dispose();
            pointsMaterial.dispose();
            markerGroup.children.forEach((child) => {
                if (child.geometry) {
                    child.geometry.dispose();
                }
                if (child.material) {
                    child.material.dispose();
                }
            });
            sphereGeometry.dispose();
            sphereMaterial.dispose();
            glowGeometry.dispose();
            glowMaterial.dispose();
            renderer.dispose();
            if (renderer.domElement.parentNode === container) {
                container.removeChild(renderer.domElement);
            }
        };
    }, []);

    return React.createElement("div", {
        ref: containerRef,
        className: "globe-frame",
        role: "img",
        "aria-label": "Three dimensional globe layer",
    });
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
        React.createElement(GlobeLayer),
        React.createElement(
            "div",
            { className: "hud-footnotes" },
            "Marker Targets: Hormuz, Kabul"
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
