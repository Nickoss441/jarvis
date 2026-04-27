# HUD Commands

## Purpose

This runbook documents the two current HUD entrypoints shipped in Jarvis:

- the local PyQt overlay via `hud-run`
- the React HUD viewport served by `approvals-api`

## 1. PyQt Overlay HUD

Command:

```bash
python3 -m jarvis hud-run [--width N] [--height N] [--opacity X] [--duration-ms N]
```

Behavior:

- Opens the transparent desktop HUD overlay.
- Returns JSON on exit.
- If PyQt6 is not installed, returns a structured `pyqt_unavailable` error.

Example:

```bash
python3 -m jarvis hud-run --width 680 --height 150 --opacity 0.77 --duration-ms 2500
```

Useful flags:

- `--width N` sets overlay width in pixels.
- `--height N` sets overlay height in pixels.
- `--opacity X` sets base window opacity.
- `--duration-ms N` auto-closes the overlay after the given duration.

Notes:

- Runtime dependency: `PyQt6`
- This is the lightweight desktop overlay scaffold, not the React HUD.

## 2. React HUD Viewport

Start the approval API first:

```bash
python3 -m jarvis approvals-api
```

Then open:

```text
http://127.0.0.1:8080/hud/react
```

Behavior:

- Serves the React-based HUD viewport from the approval API process.
- The standard command-center UI remains available at `/`.
- Static HUD assets are served under `/hud/react/...`.

Important routes:

- `/` — approval command-center UI
- `/hud/react` — React HUD viewport
- `/hud/react/app.js` — React HUD bundle
- `/hud/react/styles.css` — HUD stylesheet
- `/hud/react/data/april_27_dialogue.json` — dialogue dataset used by the HUD

Notes:

- The default host/port come from `JARVIS_APPROVALS_API_HOST` and `JARVIS_APPROVALS_API_PORT`.
- If the requested port is busy, `approvals-api` may fall forward to the next available port.
- The React HUD includes the globe, marker interactions, burst widgets, active-agent loop, dialogue dataset panel, and mission widgets already shipped in the current frontend.

## Recommended Usage

Use `hud-run` when you want a native always-on-top overlay shell.

Use `/hud/react` when you want the richer browser-rendered HUD with the current Three.js and React surfaces.
