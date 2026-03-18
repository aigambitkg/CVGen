/**
 * CVGen Desktop - Preload Script
 *
 * Provides secure, sandboxed access to native APIs from the renderer process.
 * Uses contextBridge to safely expose selected Electron APIs to the web dashboard.
 */

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Safe API object exposed to renderer
 */
const cvgenApi = {
  /**
   * Get the current app version
   */
  getVersion: () => {
    return ipcRenderer.invoke('get-app-version').catch(() => 'unknown');
  },

  /**
   * Get current backend status
   */
  getBackendStatus: () => {
    return ipcRenderer.invoke('get-backend-status');
  },

  /**
   * Get system information
   */
  getSystemInfo: () => {
    return ipcRenderer.invoke('get-system-info');
  },

  /**
   * Restart the Python backend
   */
  restartBackend: () => {
    return ipcRenderer.invoke('restart-backend');
  },

  /**
   * Check for application updates
   */
  checkForUpdates: () => {
    return ipcRenderer.invoke('check-for-updates');
  },

  /**
   * Register a callback for when backend becomes ready
   */
  onBackendReady: (callback) => {
    ipcRenderer.on('backend-ready', (event, data) => {
      callback(data);
    });
  },

  /**
   * Register a callback for when backend status changes
   */
  onBackendStatusChanged: (callback) => {
    ipcRenderer.on('backend-status-changed', (event, isReady) => {
      callback(isReady);
    });
  },

  /**
   * Register a callback for when an update is available
   */
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', () => {
      callback();
    });
  },

  /**
   * Register a callback for when an update is downloaded
   */
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update-downloaded', () => {
      callback();
    });
  },

  /**
   * Register a callback for deep link handling
   */
  onDeepLink: (callback) => {
    ipcRenderer.on('deep-link', (event, url) => {
      callback(url);
    });
  },

  /**
   * Get the current platform
   */
  platform: process.platform,

  /**
   * Get the platform architecture
   */
  arch: process.arch
};

/**
 * Expose safe API to renderer
 */
contextBridge.exposeInMainWorld('cvgen', cvgenApi);

/**
 * Inject some helpful scripts into the renderer
 */
window.addEventListener('DOMContentLoaded', () => {
  // Set up console logging to Electron console for debugging
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;

  console.log = (...args) => {
    originalLog(...args);
    ipcRenderer.send('console-log', args.join(' '));
  };

  console.error = (...args) => {
    originalError(...args);
    ipcRenderer.send('console-error', args.join(' '));
  };

  console.warn = (...args) => {
    originalWarn(...args);
    ipcRenderer.send('console-warn', args.join(' '));
  };
});
