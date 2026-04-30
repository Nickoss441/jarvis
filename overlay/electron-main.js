/**
 * Jarvis HUD Overlay - Electron Starter Template
 * 
 * This is a reference implementation for wrapping the Jarvis HUD
 * as a native desktop overlay application.
 * 
 * Future: Replace web browser with this Electron app
 * 
 * Installation:
 *   npm install electron
 *   node main.js (or: npm start)
 */

const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron');
const path = require('path');
const fetch = require('node-fetch');

let mainWindow;
const HUD_URL = 'http://127.0.0.1:8080/hud/cc';

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 720,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false,
        },
        alwaysOnTop: false,
        transparent: false,
        frame: true,
        show: false,
    });

    mainWindow.loadURL(HUD_URL);
    mainWindow.show();

    mainWindow.webContents.openDevTools();
}

app.on('ready', () => {
    createWindow();
    registerGlobalHotkeys();
    setupIPCHandlers();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

// ── Global Hotkeys ──
function registerGlobalHotkeys() {
    globalShortcut.register('CommandOrControl+Shift+J', () => {
        if (mainWindow.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow.show();
            mainWindow.focus();
        }
    });
}

// ── IPC Handlers (bridge between Electron and backend) ──
function setupIPCHandlers() {
    ipcMain.handle('system:open-file', async (event, filePath) => {
        try {
            const res = await fetch('http://127.0.0.1:8080/ipc/system/open-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            return res.json();
        } catch (err) {
            return { error: err.message };
        }
    });

    ipcMain.handle('system:execute-command', async (event, command) => {
        try {
            const res = await fetch('http://127.0.0.1:8080/ipc/system/execute-command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command })
            });
            return res.json();
        } catch (err) {
            return { error: err.message };
        }
    });

    ipcMain.handle('system:list-files', async (event, dirPath) => {
        try {
            const res = await fetch(`http://127.0.0.1:8080/ipc/system/list-files?path=${encodeURIComponent(dirPath)}`);
            return res.json();
        } catch (err) {
            return { error: err.message };
        }
    });

    ipcMain.handle('system:read-file', async (event, filePath) => {
        try {
            const res = await fetch(`http://127.0.0.1:8080/ipc/system/read-file?path=${encodeURIComponent(filePath)}`);
            return res.json();
        } catch (err) {
            return { error: err.message };
        }
    });

    ipcMain.handle('window:toggle-always-on-top', () => {
        const isOnTop = mainWindow.isAlwaysOnTop();
        mainWindow.setAlwaysOnTop(!isOnTop);
        return { alwaysOnTop: !isOnTop };
    });

    ipcMain.handle('window:minimize', () => {
        mainWindow.minimize();
        return { status: 'minimized' };
    });

    ipcMain.handle('window:maximize', () => {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
        return { maximized: mainWindow.isMaximized() };
    });

    ipcMain.handle('overlay:get-manifest', async () => {
        try {
            const res = await fetch('http://127.0.0.1:8080/ipc/overlay-manifest');
            return res.json();
        } catch (err) {
            return { error: err.message };
        }
    });
}
