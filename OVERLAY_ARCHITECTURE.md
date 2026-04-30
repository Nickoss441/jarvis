# Jarvis HUD Overlay Architecture

## Overview

The Jarvis HUD is architected to transition from a **web-based application** (viewed in a browser) to a **native desktop overlay** (Electron app) without changing the core UI or backend logic.

```
Current (Web Browser)          Future (Native Overlay)
┌──────────────────┐           ┌──────────────────┐
│  Chrome/Firefox  │           │   Electron App   │
│   (displays HTML)│           │  (native window) │
└────────┬─────────┘           └────────┬─────────┘
         │                              │
         └──────────────────┬───────────┘
                           │
                    HTTP Server (Jarvis)
                  - /hud/cc (React HUD)
                  - /hud/ask (Agent queries)
                  - /ipc/* (Overlay IPC endpoints)
```

## Architecture Layers

### 1. **Frontend (No Changes Required)**
- React-based UI in `jarvis/web/command_center/app.js`
- Vanilla ESM imports from `https://esm.sh` CDN
- CSS styling in `jarvis/web/command_center/styles.css`
- **Currently works in:** Web browser at `http://127.0.0.1:8080/hud/cc`
- **Will work in:** Electron window (same URL, just different host)

### 2. **HTTP Server (Backend)**
- `approval_api.py` — handles all endpoints
- **Existing endpoints:**
  - `/hud/cc` — Serves Command Center HTML
  - `/hud/ask` — Chat/agent queries
  - `/hud/tts` — Text-to-speech synthesis
  - `/hud/agent-knowledge/*` — Shared knowledge store
  - `/hud/agent-query` — Agent-to-agent communication

- **New IPC endpoints (for Electron app):**
  - `/ipc/system/open-file` — Open files with default app
  - `/ipc/system/execute-command` — Run shell commands (whitelist-safe)
  - `/ipc/system/list-files` — Browse directories
  - `/ipc/system/read-file` — Read file contents
  - `/ipc/overlay-manifest` — Get app metadata

### 3. **Electron Wrapper (Future)**
Located in `overlay/`:
- `electron-main.js` — Main process, window manager, IPC handlers
- `electron-preload.js` — Security bridge between web and native
- `package.json` — Build configuration
- `electron-manifest.json` — Overlay app metadata (NOT YET CREATED)

## Migration Path

### Phase 1: Framework Setup (Current)
✅ Backend HTTP server supports both browser and Electron clients
✅ IPC endpoints implemented in approval_api.py
✅ Electron starter template in place
✅ Overlay manifest schema defined

### Phase 2: Electron App
1. Install Electron in `overlay/`:
   ```bash
   cd overlay
   npm install electron electron-builder node-fetch
   ```

2. Run Electron dev server:
   ```bash
   npm start
   ```

3. The HUD UI will load in a native window instead of browser

### Phase 3: Enhanced Features
Once running in Electron, enable:
- **Global hotkey:** Ctrl+Shift+J to toggle overlay (already coded)
- **Always-on-top:** Window stays above other apps
- **System tray:** Minimize to tray for quick access
- **Drag-and-drop:** Files from desktop to Jarvis
- **Clipboard monitoring:** Auto-process clipboard content
- **Voice commands:** Listen for voice even when window is hidden

### Phase 4: Distribution
Build standalone executables:
```bash
npm run build:win   # Windows portable .exe
npm run build:mac   # macOS .dmg
npm run build:linux # Linux AppImage
```

## IPC Communication Flow

```
Web Page (React HUD)
        │
        ├─ jarvisOverlay.system.openFile(path)
        │  → ipcRenderer.invoke('system:open-file')
        │  → electron-main.js (IPC handler)
        │  → fetch('http://127.0.0.1:8080/ipc/system/open-file')
        │  → approval_api.py (backend)
        │  → subprocess.Popen(['open', path])  ← Opens file
        │
        └─ jarvisOverlay.window.toggleAlwaysOnTop()
           → ipcRenderer.invoke('window:toggle-always-on-top')
           → mainWindow.setAlwaysOnTop(!isOnTop)
```

## Current Implementation Status

### ✅ Completed
- IPC endpoint handlers in approval_api.py
- Electron starter template (main + preload)
- Overlay manifest schema
- System integration functions (open-file, execute, list-files, read-file)
- IPC-safe preload script with context isolation

### 🔄 In Progress
- Electron app development (template ready, not yet tested)
- Frontend integration with `jarvisOverlay` global API

### ⏳ TODO (Future)
- Global hotkey registration and testing
- System tray integration
- Drag-and-drop file handling
- Clipboard monitoring
- Voice command background listening
- Windows/macOS code signing for distribution
- Auto-update mechanism

## File Structure

```
jarvis/
├── approval_api.py          # Backend with new /ipc/* endpoints
├── web/
│   ├── command_center/      # React HUD (no changes needed)
│   │   ├── app.js
│   │   └── styles.css
│   └── overlay-manifest.json # App metadata + capabilities
└── overlay/
    ├── electron-main.js     # Electron main process
    ├── electron-preload.js  # Security preload script
    ├── package.json         # Build + dependency config
    └── main.js              # (legacy, can be removed)
```

## Testing the IPC Layer

### In Browser (current):
```javascript
// These won't work yet (no window.jarvisOverlay in browser)
// But you can test endpoints directly:
fetch('http://127.0.0.1:8080/ipc/system/list-files?path=.')
  .then(r => r.json())
  .then(data => console.log(data))
```

### In Electron (future):
```javascript
// Preload script exposes this safe API
window.jarvisOverlay.system.listFiles('.')
  .then(data => console.log(data))
```

## Security Considerations

- **Context Isolation:** `contextIsolation: true` in Electron prevents web code from accessing Node.js APIs
- **Preload Script:** Only specific safe methods exposed via `contextBridge`
- **Command Whitelist:** `/ipc/system/execute-command` restricted to safe commands (python, npm, git, etc.)
- **File Size Limits:** Read-file limited to 5MB to prevent memory exhaustion
- **Path Validation:** All file paths must exist and be within allowed directories

## Usage Examples (Future Electron App)

```javascript
// In React component inside Electron app

// Open a file explorer window at a path
async function browseFiles() {
  const result = await window.jarvisOverlay.system.listFiles('/home/user/documents');
  console.log(result.files);
}

// Execute a safe command
async function runScript() {
  const result = await window.jarvisOverlay.system.executeCommand('python my_script.py');
  console.log(result.stdout);
}

// Toggle always-on-top
async function togglePin() {
  const result = await window.jarvisOverlay.window.toggleAlwaysOnTop();
  console.log(`Always on top: ${result.alwaysOnTop}`);
}

// Get app capabilities
async function getInfo() {
  const manifest = await window.jarvisOverlay.app.getManifest();
  console.log(`IPC Endpoints:`, manifest.ipc_endpoints);
}
```

## Next Steps

1. **Test backend IPC endpoints** — Verify `/ipc/*` endpoints work with curl
2. **Develop Electron app** — Set up and test electron-main.js
3. **Integrate preload API** — Connect React HUD to `jarvisOverlay` global
4. **Add frontend UI** — Create buttons/commands for system operations
5. **Testing** — Verify window controls, file operations, command execution
6. **Build & distribute** — Create installers for Windows/Mac/Linux

---

**Reference:** This architecture allows Jarvis HUD to run as:
- Web app in browser (current)
- Native overlay in Electron (coming)
- Mobile app in React Native (future)
- Desktop app in PyQt/Tkinter (future)

All without changing the core UI or backend logic.
