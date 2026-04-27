# Jarvis — Copilot Instructions

## What this repo is
Jarvis is a personal AI command-and-control system. It runs a local Python server (`jarvis/approval_api.py`) that exposes HTTP endpoints for approvals, chat, and a React-based HUD. The frontend is **vanilla ESM** — no bundler, no npm — all imports come from `https://esm.sh` CDN and are loaded directly by the browser.

## Project layout
```
jarvis/
  approval_api.py      # HTTP server (stdlib BaseHTTPRequestHandler), all routing lives here
  brain.py             # LLM orchestration, tool registry
  tools/               # individual Jarvis tools (retirement_planner, etc.)
  web/
    hud_react/         # Strategic Globe HUD  → served at /hud/react
    command_center/    # Jarvis Command Center → served at /hud/cc
ui/
  SlidePanel.tsx       # standalone TSX component (not part of the web server)
tests/
docs/
```

## The two HUD views

### `/hud/react` — Strategic Globe
- Three.js globe with geopolitical markers (Hormuz, Kabul, Djibouti, Singapore)
- Click a marker to inspect threat level, active feeds, and protocol actions
- Custom CSS only — no Tailwind, no Framer Motion

### `/hud/cc` — Jarvis Command Center  ← **just built**
- Full-screen futuristic dashboard (Jarvis / Iron Man aesthetic)
- Deep-space black background (`#050505`) with a subtle cyan city-grid pattern
- **Glassmorphism panels** (`bg rgba(0,0,0,0.42)`, `backdrop-filter blur`, cyan border)
- **Top/bottom chrome bars** with scrolling monospaced terminal telemetry text
- **Center core**: three concentric radar-pulse rings + rotating sweep + crosshair
- **Six orbit mini-panels** arranged in a hexagonal ring at radius 175 px around the core
- **Four corner HUD panels**:
  - Top-left: SOCIAL MONITORING — `+356`, bar graph, cyan subtext
  - Bottom-left: BITCOIN — `$79,016`, glowing green SVG sparkline, "Hold Steady"
  - Top-right: OIL & GOLD — `+3.2%` badge, "69% Profitable", ACTIVE / HOT badges
  - Bottom-right: TRACKING / STRATEGY — `2` events, cyan/green badges
- Fonts: Inter (thin numerals) + JetBrains Mono (all labels/subtext) via Google Fonts CDN
- All animation via CSS keyframes (`radar-expand`, `sweep`, `marquee`, `hot-blink`)

## Conventions for this frontend
- **No JSX** — all components use `React.createElement(...)` directly
- **No bundler** — import from `https://esm.sh/<package>@<version>`
- **No Tailwind** — all styling is plain CSS in `styles.css` next to `app.js`
- Component names: PascalCase functions returning `React.createElement`
- CSS class names: `cc-*` prefix for command center, `hud-*` for the globe HUD

## Adding a new HUD page
1. Create `jarvis/web/<name>/index.html`, `app.js`, `styles.css`
2. Add a `<NAME>_ASSETS` dict and `<NAME>_DIR` path constant near the top of `approval_api.py`
3. Add a `_load_<name>_asset()` helper modelled on `_load_react_hud_asset()`
4. Add two `if parsed.path` blocks inside `do_GET` (exact match for index, prefix match for assets)

## Server notes
- The server is a plain `ThreadingHTTPServer` — no framework
- All routing is `if/elif` chains inside `do_GET` in `ApprovalApiHandler`
- Static assets are read from disk on every request (no caching layer)
- Port defaults to `8080`, host `127.0.0.1`
