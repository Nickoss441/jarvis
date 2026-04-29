const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const http = require('http');

const HUD_URL = 'http://127.0.0.1:8081/hud/cc';
const SHOW_HIDE_HOTKEY = 'Ctrl+Shift+J';
const POLL_INTERVAL_MS = 2000;

let win = null;
let tray = null;
let visible = true;

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 800,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.loadURL(HUD_URL);
  win.setIgnoreMouseEvents(false);

  win.on('closed', () => { win = null; });
}

function toggleVisibility() {
  if (!win) return;
  if (visible) {
    win.hide();
    visible = false;
  } else {
    win.show();
    win.focus();
    visible = true;
  }
}

function pollHudEndpoints() {
  const check = (path, action) => {
    http.get(`http://127.0.0.1:8081${path}`, (res) => {
      if (res.statusCode === 200) action();
      res.resume();
    }).on('error', () => {});
  };

  setInterval(() => {
    check('/hud/show', () => { if (!visible && win) { win.show(); win.focus(); visible = true; } });
    check('/hud/hide', () => { if (visible && win) { win.hide(); visible = false; } });
  }, POLL_INTERVAL_MS);
}

function createTray() {
  const iconPath = path.join(__dirname, 'build', 'tray.png');
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
  } catch {
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
  tray.setToolTip('Jarvis HUD');

  const menu = Menu.buildFromTemplate([
    { label: 'Show / Hide  (Ctrl+Shift+J)', click: toggleVisibility },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setContextMenu(menu);
  tray.on('click', toggleVisibility);
}

app.whenReady().then(() => {
  createWindow();
  createTray();

  globalShortcut.register(SHOW_HIDE_HOTKEY, toggleVisibility);

  pollHudEndpoints();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// Keep app alive when all windows are closed (tray-only mode).
app.on('window-all-closed', (e) => e.preventDefault());
