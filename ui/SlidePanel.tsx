import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";

export type SlidePanelAgent = "Strategic Intel" | "Market Bot" | "Echo Core";

export type SlidePanelMarker = {
    id: string;
    title: string;
    latitude: number;
    longitude: number;
    summary: string;
    agent: SlidePanelAgent;
    timestamp?: string;
};

export type SlidePanelProps = {
    open: boolean;
    marker: SlidePanelMarker | null;
    onClose: () => void;
};

const agentAccent: Record<SlidePanelAgent, string> = {
    "Strategic Intel": "#ffb347",
    "Market Bot": "#00f2ff",
    "Echo Core": "#7cf29c",
};

const panelVariants = {
    hidden: {
        opacity: 0,
        y: "12vh",
        scale: 0.96,
    },
    visible: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: {
            duration: 0.28,
            ease: [0.16, 1, 0.3, 1],
        },
    },
    exit: {
        opacity: 0,
        y: "10vh",
        scale: 0.98,
        transition: {
            duration: 0.2,
            ease: [0.4, 0, 1, 1],
        },
    },
};

export function SlidePanel({ open, marker, onClose }: SlidePanelProps) {
    React.useEffect(() => {
        if (!open) {
            return undefined;
        }

        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                onClose();
            }
        };

        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [open, onClose]);

    return (
        <AnimatePresence>
            {open && marker ? (
                <motion.aside
                    aria-label="Echo event detail panel"
                    initial="hidden"
                    animate="visible"
                    exit="exit"
                    variants={panelVariants}
                    style={{
                        position: "fixed",
                        left: "50%",
                        bottom: "5vh",
                        transform: "translateX(-50%)",
                        width: "60vw",
                        minHeight: "18vh",
                        maxHeight: "34vh",
                        padding: "2.2vh 2vw",
                        borderRadius: "1.8vw",
                        overflow: "hidden",
                        color: "#eafcff",
                        background:
                            "linear-gradient(135deg, rgba(6, 16, 24, 0.82), rgba(7, 24, 38, 0.56) 58%, rgba(20, 48, 62, 0.78))",
                        backdropFilter: "blur(12px)",
                        WebkitBackdropFilter: "blur(12px)",
                        border: "1px solid rgba(0, 242, 255, 0.3)",
                        boxShadow: "0 1.2vh 4vh rgba(0, 0, 0, 0.35), inset 0 0 0 0.1vh rgba(255, 255, 255, 0.08)",
                        zIndex: 40,
                    }}
                >
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "1fr auto",
                            gap: "1.2vh 1vw",
                            alignItems: "start",
                            height: "100%",
                        }}
                    >
                        <div>
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.8vw",
                                    marginBottom: "1.2vh",
                                }}
                            >
                                <span
                                    style={{
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        minWidth: "7.2vw",
                                        padding: "0.45vh 0.9vw",
                                        borderRadius: "999px",
                                        fontSize: "0.78vw",
                                        letterSpacing: "0.14em",
                                        textTransform: "uppercase",
                                        color: agentAccent[marker.agent],
                                        background: "rgba(255, 255, 255, 0.04)",
                                        border: `1px solid ${agentAccent[marker.agent]}55`,
                                    }}
                                >
                                    {marker.agent}
                                </span>
                                <span
                                    style={{
                                        fontSize: "0.84vw",
                                        letterSpacing: "0.12em",
                                        textTransform: "uppercase",
                                        color: "rgba(234, 252, 255, 0.62)",
                                    }}
                                >
                                    Echo Detail Feed
                                </span>
                            </div>

                            <h2
                                style={{
                                    margin: 0,
                                    fontSize: "1.55vw",
                                    lineHeight: 1.1,
                                    fontWeight: 600,
                                }}
                            >
                                {marker.title}
                            </h2>

                            <p
                                style={{
                                    margin: "1.4vh 0 0",
                                    fontSize: "1vw",
                                    lineHeight: 1.55,
                                    color: "rgba(234, 252, 255, 0.88)",
                                    maxWidth: "44vw",
                                }}
                            >
                                {marker.summary}
                            </p>
                        </div>

                        <button
                            type="button"
                            aria-label="Close detail panel"
                            onClick={onClose}
                            style={{
                                width: "2.4vw",
                                height: "2.4vw",
                                minWidth: "40px",
                                minHeight: "40px",
                                borderRadius: "50%",
                                border: "1px solid rgba(0, 242, 255, 0.22)",
                                background: "rgba(255, 255, 255, 0.05)",
                                color: "#eafcff",
                                cursor: "pointer",
                                fontSize: "1vw",
                            }}
                        >
                            ×
                        </button>

                        <div
                            style={{
                                gridColumn: "1 / -1",
                                display: "grid",
                                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                                gap: "1vw",
                                marginTop: "1vh",
                            }}
                        >
                            <PanelMetric label="Latitude" value={`${marker.latitude.toFixed(1)}°`} />
                            <PanelMetric label="Longitude" value={`${marker.longitude.toFixed(1)}°`} />
                            <PanelMetric label="Timestamp" value={marker.timestamp ?? "Live"} />
                        </div>
                    </div>
                </motion.aside>
            ) : null}
        </AnimatePresence>
    );
}

function PanelMetric({ label, value }: { label: string; value: string }) {
    return (
        <div
            style={{
                padding: "1vh 0.9vw",
                borderRadius: "1vw",
                background: "rgba(255, 255, 255, 0.035)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
            }}
        >
            <div
                style={{
                    marginBottom: "0.45vh",
                    fontSize: "0.72vw",
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    color: "rgba(234, 252, 255, 0.54)",
                }}
            >
                {label}
            </div>
            <div
                style={{
                    fontSize: "0.94vw",
                    color: "#f6fbff",
                }}
            >
                {value}
            </div>
        </div>
    );
}

export const echoHudMarkers: SlidePanelMarker[] = [
    {
        id: "hormuz",
        title: "Strait of Hormuz",
        latitude: 26.5,
        longitude: 55.5,
        summary: "The Strait of Hormuz remains under controlled transit.",
        agent: "Strategic Intel",
        timestamp: "27 Apr 2026",
    },
    {
        id: "kabul-border",
        title: "Kabul Border",
        latitude: 34.0,
        longitude: 71.5,
        summary: "Kabul border clashes reported with 4 dead, 70 injured.",
        agent: "Echo Core",
        timestamp: "27 Apr 2026",
    },
];
