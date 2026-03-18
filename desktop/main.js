/**
 * CVGen Desktop - Electron Main Process
 *
 * Manages the application window, Python backend process,
 * system tray integration, and auto-updates.
 */

const { app, BrowserWindow, Menu, Tray, dialog, ipcMain } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const http = require('http');
const log = require('electron-log');
const { autoUpdater } = require('electron-updater');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

// Constants
const isDevelopment = process.argv.includes('--dev');
const BACKEND_PORT = 8765;
const BACKEND_HOST = '127.0.0.1';
const HEALTH_CHECK_INTERVAL = 500;
const HEALTH_CHECK_TIMEOUT = 30000;
const APP_NAME = 'CVGen';

// Global state
let mainWindow;
let tray;
let backendProcess;
let backendReady = false;
let isQuitting = false;
let backendStartTime = 0;

/**
 * Create the main application window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      enableRemoteModule: false,
      nodeIntegration: false,
      sandbox: true
    },
    show: false,
    icon: getAppIcon()
  });

  // Show window once ready
  mainWindow.once('ready-to-show', () => {
    if (!isQuitting) {
      mainWindow.show();
      if (isDevelopment) {
        mainWindow.webContents.openDevTools();
      }
    }
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Handle minimize to tray
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      showTrayNotification();
    }
  });

  // Load splash screen initially
  const splashPath = path.join(__dirname, 'splash.html');
  if (fs.existsSync(splashPath)) {
    mainWindow.loadFile(splashPath);
  }
}

/**
 * Show system tray icon and menu
 */
function createTray() {
  const iconPath = getAppIcon();
  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Dashboard',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Backend Status',
      submenu: [
        {
          label: backendReady ? '● Running' : '● Offline',
          enabled: false
        },
        {
          label: 'Restart Backend',
          click: () => {
            ipcMain.emit('restart-backend-request');
          }
        }
      ]
    },
    {
      label: 'Check for Updates',
      click: () => {
        autoUpdater.checkForUpdatesAndNotify();
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.setToolTip(`${APP_NAME} - Quantum Computing for Every Device`);

  // Click tray icon to show/hide
  tray.on('click', () => {
    if (mainWindow && mainWindow.isVisible()) {
      mainWindow.hide();
    } else if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

/**
 * Get the appropriate icon for this platform
 */
function getAppIcon() {
  let iconPath;
  if (process.platform === 'win32') {
    iconPath = path.join(__dirname, 'resources', 'icon.ico');
  } else if (process.platform === 'darwin') {
    iconPath = path.join(__dirname, 'resources', 'icon.icns');
  } else {
    iconPath = path.join(__dirname, 'resources', 'icon.png');
  }

  // Fallback to a built-in icon if custom doesn't exist
  if (!fs.existsSync(iconPath)) {
    return null;
  }
  return iconPath;
}

/**
 * Show tray notification on first minimize
 */
function showTrayNotification() {
  if (tray && mainWindow) {
    tray.displayBalloon({
      title: APP_NAME,
      content: 'CVGen is running. Click the tray icon to restore the window.'
    });
  }
}

/**
 * Get Python backend executable path
 */
function getPythonBackendPath() {
  let execName = 'cvgen-backend';
  if (process.platform === 'win32') {
    execName += '.exe';
  }

  // In production, look in resources
  if (!isDevelopment) {
    const bundledPath = path.join(process.resourcesPath, 'python-backend', 'cvgen-backend', execName);
    if (fs.existsSync(bundledPath)) {
      return bundledPath;
    }
  }

  // Fallback to dev mode or local dist-python
  const distPath = path.join(__dirname, '..', 'dist-python', 'cvgen-backend', execName);
  if (fs.existsSync(distPath)) {
    return distPath;
  }

  return null;
}

/**
 * Start the Python FastAPI backend
 */
function startBackend() {
  return new Promise((resolve, reject) => {
    try {
      let command;
      let args;

      if (isDevelopment) {
        // Development: run directly with Python
        command = 'python';
        args = ['-m', 'uvicorn', 'cvgen.api.app:app', '--port', BACKEND_PORT.toString(), '--host', BACKEND_HOST];

        log.info('Starting backend in development mode:', { command, args });
      } else {
        // Production: use bundled executable
        const backendPath = getPythonBackendPath();
        if (!backendPath) {
          const error = new Error('Python backend executable not found. Please rebuild the application.');
          log.error(error.message);
          return reject(error);
        }

        command = backendPath;
        args = [];

        log.info('Starting backend from bundled executable:', { command });
      }

      backendStartTime = Date.now();
      backendProcess = spawn(command, args, {
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
        env: {
          ...process.env,
          CVGEN_PORT: BACKEND_PORT.toString(),
          CVGEN_HOST: BACKEND_HOST
        }
      });

      backendProcess.stdout.on('data', (data) => {
        log.info('[Backend]', data.toString().trim());
      });

      backendProcess.stderr.on('data', (data) => {
        log.warn('[Backend]', data.toString().trim());
      });

      backendProcess.on('error', (error) => {
        log.error('Failed to start backend process:', error);
        reject(error);
      });

      backendProcess.on('exit', (code, signal) => {
        log.warn(`Backend process exited with code ${code} and signal ${signal}`);
        backendReady = false;
        if (mainWindow && !isQuitting) {
          mainWindow.webContents.send('backend-status-changed', false);
        }
      });

      // Wait for health check to pass
      waitForBackendHealthy()
        .then(() => {
          backendReady = true;
          log.info('Backend is healthy and ready');
          resolve();
        })
        .catch(reject);
    } catch (error) {
      log.error('Error starting backend:', error);
      reject(error);
    }
  });
}

/**
 * Poll the backend health endpoint until it's ready
 */
function waitForBackendHealthy() {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const healthUrl = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1/health`;

    const checkHealth = () => {
      const elapsed = Date.now() - startTime;

      if (elapsed > HEALTH_CHECK_TIMEOUT) {
        const error = new Error(`Backend did not become healthy within ${HEALTH_CHECK_TIMEOUT}ms`);
        log.error(error.message);
        return reject(error);
      }

      http
        .get(healthUrl, (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            setTimeout(checkHealth, HEALTH_CHECK_INTERVAL);
          }
        })
        .on('error', () => {
          setTimeout(checkHealth, HEALTH_CHECK_INTERVAL);
        });
    };

    checkHealth();
  });
}

/**
 * Kill the backend process gracefully
 */
function killBackend() {
  return new Promise((resolve) => {
    if (!backendProcess) {
      return resolve();
    }

    const timeout = setTimeout(() => {
      log.warn('Backend did not exit gracefully, force killing...');
      try {
        if (process.platform === 'win32') {
          execSync(`taskkill /PID ${backendProcess.pid} /F`);
        } else {
          process.kill(-backendProcess.pid);
        }
      } catch (error) {
        log.error('Error force killing backend:', error);
      }
      resolve();
    }, 5000);

    backendProcess.on('exit', () => {
      clearTimeout(timeout);
      resolve();
    });

    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /PID ${backendProcess.pid}`);
      } else {
        process.kill(-backendProcess.pid);
      }
    } catch (error) {
      log.error('Error killing backend:', error);
      clearTimeout(timeout);
      resolve();
    }
  });
}

/**
 * Create application menu
 */
function createMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Exit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            isQuitting = true;
            app.quit();
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => {
            if (mainWindow) {
              mainWindow.reload();
            }
          }
        },
        {
          label: 'Toggle Developer Tools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.toggleDevTools();
            }
          }
        },
        { type: 'separator' },
        {
          label: 'Zoom In',
          accelerator: 'CmdOrCtrl+=',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.setZoomLevel(mainWindow.webContents.getZoomLevel() + 0.5);
            }
          }
        },
        {
          label: 'Zoom Out',
          accelerator: 'CmdOrCtrl+-',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.setZoomLevel(mainWindow.webContents.getZoomLevel() - 0.5);
            }
          }
        },
        {
          label: 'Reset Zoom',
          accelerator: 'CmdOrCtrl+0',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.setZoomLevel(0);
            }
          }
        }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About CVGen',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About CVGen',
              message: 'CVGen - Quantum Computing for Every Device',
              detail: `Version: ${app.getVersion()}\nAuthor: AI-Gambit (PNB Solutions)\nLicense: MIT`
            });
          }
        },
        {
          label: 'Check for Updates',
          click: () => {
            autoUpdater.checkForUpdatesAndNotify();
          }
        },
        {
          label: 'Documentation',
          click: async () => {
            const { shell } = require('electron');
            await shell.openExternal('https://github.com/aigambitkg/CVGen/wiki');
          }
        },
        {
          label: 'Report Issue',
          click: async () => {
            const { shell } = require('electron');
            await shell.openExternal('https://github.com/aigambitkg/CVGen/issues');
          }
        }
      ]
    }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

/**
 * Setup IPC handlers for renderer communication
 */
function setupIpcHandlers() {
  ipcMain.handle('get-backend-status', () => {
    return {
      ready: backendReady,
      url: `http://${BACKEND_HOST}:${BACKEND_PORT}`,
      uptime: backendReady ? Date.now() - backendStartTime : 0
    };
  });

  ipcMain.handle('get-system-info', () => {
    return {
      platform: process.platform,
      arch: process.arch,
      cpuCount: os.cpus().length,
      totalMemory: os.totalmem(),
      freeMemory: os.freemem(),
      nodeVersion: process.versions.node,
      electronVersion: process.versions.electron,
      appVersion: app.getVersion()
    };
  });

  ipcMain.handle('restart-backend', async () => {
    log.info('Restarting backend...');
    await killBackend();
    backendReady = false;
    if (mainWindow) {
      mainWindow.webContents.send('backend-status-changed', false);
    }
    try {
      await startBackend();
      if (mainWindow) {
        mainWindow.webContents.send('backend-status-changed', true);
      }
      return { success: true };
    } catch (error) {
      log.error('Failed to restart backend:', error);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('check-for-updates', async () => {
    try {
      const result = await autoUpdater.checkForUpdates();
      return result;
    } catch (error) {
      log.error('Failed to check for updates:', error);
      return { error: error.message };
    }
  });

  ipcMain.on('restart-backend-request', () => {
    ipcMain.emit('restart-backend');
  });
}

/**
 * Setup auto-updater
 */
function setupAutoUpdater() {
  autoUpdater.logger = log;
  autoUpdater.checkForUpdatesAndNotify();

  autoUpdater.on('update-available', () => {
    log.info('Update available');
    if (mainWindow) {
      mainWindow.webContents.send('update-available');
    }
  });

  autoUpdater.on('update-downloaded', () => {
    log.info('Update downloaded');
    if (mainWindow) {
      mainWindow.webContents.send('update-downloaded');
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Update Ready',
        message: 'An update has been downloaded.',
        detail: 'The application will restart to apply the update.',
        buttons: ['Install Now', 'Later']
      }).then((result) => {
        if (result.response === 0) {
          isQuitting = true;
          autoUpdater.quitAndInstall();
        }
      });
    }
  });

  autoUpdater.on('error', (error) => {
    log.error('Auto updater error:', error);
  });
}

/**
 * Handle protocol deep links (cvgen://)
 */
function setupProtocolHandler() {
  if (process.defaultApp) {
    if (process.argv.length >= 2) {
      app.setAsDefaultProtocolClient('cvgen', process.execPath, [path.resolve(process.argv[1])]);
    }
  } else {
    app.setAsDefaultProtocolClient('cvgen');
  }

  app.on('open-url', (event, url) => {
    event.preventDefault();
    log.info('Deep link received:', url);
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
      mainWindow.webContents.send('deep-link', url);
    }
  });
}

/**
 * Enforce single instance
 */
function enforceInstanceLock() {
  const gotTheLock = app.requestSingleInstanceLock();

  if (!gotTheLock) {
    app.quit();
  } else {
    app.on('second-instance', () => {
      if (mainWindow) {
        if (mainWindow.isMinimized()) {
          mainWindow.restore();
        }
        mainWindow.focus();
      }
    });
  }
}

/**
 * App event handlers
 */
app.on('ready', async () => {
  log.info('CVGen Desktop starting...');
  log.info('App details:', {
    version: app.getVersion(),
    isDevelopment,
    platform: process.platform,
    arch: process.arch
  });

  enforceInstanceLock();
  createWindow();
  createTray();
  createMenu();
  setupIpcHandlers();
  setupProtocolHandler();
  setupAutoUpdater();

  // Start backend and load dashboard
  try {
    log.info('Starting Python backend...');
    await startBackend();
    log.info('Backend started successfully');

    // Load the dashboard
    if (mainWindow) {
      const dashboardUrl = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
      mainWindow.loadURL(dashboardUrl);

      // Send ready event to renderer
      mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.send('backend-ready', {
          url: dashboardUrl,
          host: BACKEND_HOST,
          port: BACKEND_PORT
        });
      });
    }
  } catch (error) {
    log.error('Failed to start backend:', error);
    dialog.showErrorBox('Backend Error', `Failed to start CVGen backend:\n\n${error.message}\n\nTroubleshooting:\n1. Ensure Python 3.11+ is installed\n2. Check that all dependencies are installed\n3. Try restarting the application\n4. Check the logs in the developer console`);
    isQuitting = true;
    app.quit();
  }
});

app.on('window-all-closed', () => {
  // On macOS, keep running in tray
  if (process.platform !== 'darwin') {
    isQuitting = true;
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
});

app.on('before-quit', async () => {
  log.info('Cleaning up before quit...');
  isQuitting = true;
  await killBackend();
  log.info('CVGen Desktop shut down cleanly');
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  log.error('Uncaught exception:', error);
  dialog.showErrorBox('Error', `An unexpected error occurred:\n\n${error.message}`);
});
