# CVGen Desktop Application

A native desktop application for CVGen - Quantum Computing for Every Device.

The desktop application is built with Electron and wraps the FastAPI backend Python server, providing a seamless one-click installation and launch experience.

## Architecture

```
┌─────────────────────────────────────────┐
│        Electron Main Process            │
│  • Window management                    │
│  • System tray integration              │
│  • Auto-updates                         │
│  • IPC communication                    │
└──────────────┬──────────────────────────┘
               │
               ├─► Python FastAPI Backend (child process)
               │   • Quantum circuit execution
               │   • AI agent orchestration
               │   • REST API endpoints
               │
               └─► Web Dashboard (BrowserWindow)
                   • React/Vue UI
                   • Real-time updates
                   • System information

```

## Prerequisites

### For Building

- **Node.js 18+** - Download from https://nodejs.org/
- **Python 3.11+** - Download from https://www.python.org/
- **Platform-specific tools:**
  - Windows: Visual C++ Build Tools
  - macOS: Xcode Command Line Tools (`xcode-select --install`)
  - Linux: build-essential, libx11-dev

### For Running

- Python 3.11+ with FastAPI and Uvicorn installed
- Electron runtime (bundled in the application)

## Development Setup

### 1. Install Node Dependencies

```bash
cd desktop
npm install
```

### 2. Build Python Backend

#### On macOS/Linux:
```bash
chmod +x build-python.sh
./build-python.sh
```

#### On Windows:
```bash
build-python.bat
```

This creates a `dist-python/` directory with the bundled Python executable.

### 3. Run in Development Mode

```bash
npm run dev
```

This starts the Electron app in development mode with:
- DevTools open for debugging
- Hot reload for any file changes
- Backend running with `python -m uvicorn`

## Building for Production

### Windows
```bash
npm run build:win
```
Creates: `dist/CVGen Setup 1.0.0.exe`

### macOS
```bash
npm run build:mac
```
Creates: `dist/CVGen-1.0.0.dmg`

### Linux
```bash
npm run build:linux
```
Creates: `dist/CVGen-1.0.0.AppImage` and `dist/cvgen_1.0.0_amd64.deb`

### All Platforms
```bash
npm run build:all
```

## File Structure

```
desktop/
├── main.js                 # Electron main process
├── preload.js              # Secure preload script for IPC
├── splash.html             # Beautiful loading screen
├── package.json            # NPM dependencies & build config
├── build-python.sh         # Python build script (Unix)
├── build-python.bat        # Python build script (Windows)
├── resources/              # App icons and assets
│   ├── icon.svg
│   ├── icon.ico
│   ├── icon.icns
│   └── icon.png
└── README.md               # This file

../src/cvgen/
├── desktop_entry.py        # PyInstaller entry point
└── launcher.py             # Pure Python launcher (tkinter)

```

## Key Features

### Auto-Updates
- Checks GitHub Releases on startup
- Downloads updates in background
- Prompts user before installing
- Configurable update channels

### System Tray Integration
- Minimize to tray (on first close shows notification)
- Status indicator (Running/Offline)
- Quick access menu
- One-click restart backend

### Backend Management
- Automatic backend startup
- Health checks every 500ms
- Graceful shutdown (30s timeout)
- Error recovery and logging
- IPC communication for status

### Security
- Context isolation enabled
- Sandbox mode for renderer
- Node integration disabled
- Secure preload bridge
- No eval/inline scripts

## Configuration

### Environment Variables

```bash
# Backend
CVGEN_PORT=8765              # Server port
CVGEN_HOST=127.0.0.1         # Server host
CVGEN_LOG_LEVEL=info         # Logging level

# Electron
DEBUG=cvgen:*                # Enable debug logging
ELECTRON_ENABLE_SANDBOX=1    # Sandbox mode
```

### Package.json Build Settings

The `build` section in `package.json` controls:

```json
{
  "build": {
    "appId": "com.aigambit.cvgen",
    "productName": "CVGen",
    "directories": {
      "output": "dist",
      "buildResources": "resources"
    },
    "files": [
      "main.js",
      "preload.js",
      "splash.html",
      "resources/**/*"
    ],
    "extraResources": [
      {
        "from": "../dist-python/",
        "to": "python-backend"
      }
    ]
  }
}
```

## Troubleshooting

### Backend Not Starting

**Symptoms:** "Backend did not respond" error

**Solutions:**
1. Verify Python 3.11+ is installed: `python --version`
2. Check FastAPI is installed: `pip install fastapi uvicorn`
3. Check port 8765 isn't in use: `lsof -i :8765` (macOS/Linux)
4. Look at logs in Help → Open DevTools → Console

### Blank Window / Failed to Load

**Symptoms:** Window appears but shows blank/error page

**Solutions:**
1. Ensure backend is running: Check console for "Backend is healthy"
2. Check http://localhost:8765 in browser manually
3. Check static files exist in `dist-python/cvgen-backend/cvgen/web/static`
4. Look at Network tab in DevTools

### Port Already in Use

**Symptoms:** "Error: Port 8765 is already in use"

**Solutions:**
1. Find process using port: `lsof -i :8765` (macOS/Linux)
2. Kill process: `kill -9 <PID>`
3. Or change port: Edit `main.js` and `preload.js`

### Can't Build Python Backend

**Symptoms:** PyInstaller build fails

**Solutions:**
1. Verify Python version: `python --version` (needs 3.11+)
2. Install PyInstaller: `pip install pyinstaller`
3. Check for required dependencies: `pip install -r requirements.txt`
4. Clear old builds: `rm -rf build/ dist/ *.spec`

### Icon Not Showing

**Symptoms:** App has default Windows/system icon

**Solutions:**
1. Ensure icon files exist in `resources/`
2. Windows: Must be `.ico` format
3. macOS: Must be `.icns` format
4. Linux: Can be `.png` or `.svg`
5. Rebuild: Delete `dist/` and `npm run build:win`

## Deep Linking

The app supports `cvgen://` protocol links for integration with other apps:

```bash
# On Windows
start cvgen://circuit/new

# On macOS
open cvgen://circuit/new

# On Linux
xdg-open cvgen://circuit/new
```

## Logging

Logs are stored in:

```
Windows:  %APPDATA%/CVGen/logs/
macOS:    ~/Library/Logs/CVGen/
Linux:    ~/.config/CVGen/logs/
```

View logs in the app: Help → DevTools → Console

## Performance Tips

1. **Disable DevTools in production:**
   - Remove `.openDevTools()` from `main.js`
   - Build with `--publish always` for auto-updates

2. **Optimize bundle size:**
   - Use `npm prune --production`
   - Remove dev dependencies before building
   - PyInstaller UPX compression (optional)

3. **Memory usage:**
   - Monitor with system tray status
   - Restart backend if memory grows: right-click tray → Restart

## Contributing

To contribute to the desktop app:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test: `npm run dev`
4. Submit a pull request

## Known Issues

- First launch takes longer due to backend startup
- Windows Defender may scan the executable on first run
- Linux requires glibc 2.29+ (older systems may need rebuilding)

## License

MIT - See LICENSE file

## Support

- GitHub Issues: https://github.com/aigambitkg/CVGen/issues
- Documentation: https://github.com/aigambitkg/CVGen/wiki
- Email: support@aigambit.io

## Changelog

### v1.0.0
- Initial release
- Electron 28+ support
- Auto-update via GitHub Releases
- System tray integration
- Graceful backend management
- Beautiful splash screen
- Cross-platform support
