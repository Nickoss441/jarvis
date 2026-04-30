/**
 * Preload Script for Jarvis HUD Overlay
 * 
 * Provides safe, context-isolated IPC communication
 * between the renderer process (web app) and main process (Electron).
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose safe API to web renderer
contextBridge.exposeInMainWorld('jarvisOverlay', {
    // System operations
    system: {
        openFile: (filePath) => ipcRenderer.invoke('system:open-file', filePath),
        executeCommand: (command) => ipcRenderer.invoke('system:execute-command', command),
        listFiles: (dirPath) => ipcRenderer.invoke('system:list-files', dirPath),
        readFile: (filePath) => ipcRenderer.invoke('system:read-file', filePath),
    },

    // Window controls
    window: {
        toggleAlwaysOnTop: () => ipcRenderer.invoke('window:toggle-always-on-top'),
        minimize: () => ipcRenderer.invoke('window:minimize'),
        maximize: () => ipcRenderer.invoke('window:maximize'),
    },

    // App metadata
    app: {
        getManifest: () => ipcRenderer.invoke('overlay:get-manifest'),
        isElectron: true,
    },

    // Events
    on: (channel, callback) => {
        ipcRenderer.on(channel, (event, ...args) => callback(...args));
    },

    removeListener: (channel, callback) => {
        ipcRenderer.removeListener(channel, callback);
    },
});
