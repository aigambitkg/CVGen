# CVGen Desktop Application - Complete Build Guide

This guide walks you through building a complete, production-ready Electron desktop application for CVGen that users can install with one click.

## Overview

The CVGen Desktop Application consists of:

1. **Electron Main Process** - Window management, system tray, backend management
2. **Python FastAPI Backend** - Bundled as a standalone executable
3. **Web Dashboard** - Loaded in the Electron BrowserWindow
4. **Auto-Updater** - GitHub Release-based updates
5. **System Integration** - Tray icons, deep links, protocol handlers

Users download ONE installer, double-click, and everything works without any setup.

## Prerequisites

### Required

- **Node.js 18+** - https://nodejs.org/ (includes npm)
- **Python 3.11+** - https://www.python.org/
- **Git** - For cloning and version control

### Platform-Specific

#### Windows
- Visual C++ Build Tools (for native modules)
  - Download: https://visualstudio.microsoft.com/downloads/
  - Select "Desktop development with C++"
- Windows 7 SP1 or later (for app to run)

#### macOS
- Xcode Command Line Tools: `xcode-select --install`
- macOS 10.11 or later (for app to run)

#### Linux
- Build tools: `sudo apt-get install build-essential libx11-dev libxss-dev`
- Glibc 2.29+ (Ubuntu 20.04 LTS or later recommended)

## Step 1: Verify Installation

```bash
# Check Node.js and npm
node --version    # Should be 18.0.0 or higher
npm --version     # Should be 9.0.0 or higher

# Check Python
python --version  # Should be 3.11.0 or higher

# Check Git
git --version     # Should be 2.30.0 or higher
```

## Step 2: Prepare the Project

```bash
cd /home/kevin/CVGEN/cvgen-build

# Install Python dependencies
pip install -r requirements.txt

# Verify FastAPI is installed
python -c "import fastapi; print(fastapi.__version__)"

# Verify Uvicorn is installed
pip install uvicorn
```

## Step 3: Build Python Backend

The Python backend needs to be compiled into a standalone executable using PyInstaller.

### On macOS/Linux:

```bash
cd desktop

# Make script executable
chmod +x build-python.sh

# Run build
./build-python.sh
```

Expected output:
```
========================================
CVGen Python Backend Build
========================================
Found Python: 3.11.x
Installing PyInstaller...
Building CVGen Python Backend...
...
========================================
Build Complete!
========================================

Output location: dist-python/
```

### On Windows:

```bash
cd desktop

# Run batch file
build-python.bat
```

Expected output:
```
========================================
CVGen Python Backend Build
========================================
Installing PyInstaller...
Building CVGen Python Backend...
...
========================================
Build Complete!
========================================

Output location: dist-python/
```

### Verify Python Build

After the build completes, verify the output:

```bash
# Check that dist-python exists
ls -la dist-python/

# You should see:
# cvgen-backend/
#   ├── cvgen-backend (or .exe on Windows)
#   ├── libcvgen/ or similar
#   └── ... other bundled files
```

## Step 4: Install Electron Dependencies

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

# Install Node modules
npm install

# This installs:
# - electron (the app framework)
# - electron-builder (for creating installers)
# - electron-updater (for auto-updates)
# - electron-log (for logging)
```

Expected time: 2-5 minutes depending on internet speed.

## Step 5: Test in Development Mode

Before building for production, test that everything works:

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

npm run dev
```

This will:
1. Start the Electron app
2. Show the splash screen
3. Start the Python backend (via `python -m uvicorn`)
4. Open DevTools for debugging
5. Load the dashboard at http://localhost:8765

**Testing checklist:**
- [ ] Splash screen appears
- [ ] Status updates: "Starting quantum backend..." → "Initializing AI agents..." → "Ready!"
- [ ] Dashboard loads and displays correctly
- [ ] Click buttons and interact with the dashboard
- [ ] Open DevTools (Ctrl+Shift+I) and check for errors
- [ ] System tray icon appears
- [ ] Right-click tray → "Show Dashboard" brings window back
- [ ] Right-click tray → "Quit" closes properly

If issues occur, see Troubleshooting section below.

## Step 6: Build for Your Platform

Choose your target platform:

### For Windows

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

npm run build:win
```

This creates:
- `dist/CVGen Setup 1.0.0.exe` - NSIS installer
- `dist/CVGen 1.0.0.exe` - Portable executable

**Installer features:**
- One-click installation
- Adds "Add/Remove Programs" entry
- Creates Start menu shortcuts
- Creates desktop shortcut
- Registers protocol handler (cvgen://)

**Testing the installer:**
```bash
# Run the installer
dist/CVGen\ Setup\ 1.0.0.exe

# It will install to:
# C:\Users\<username>\AppData\Local\Programs\CVGen\
```

### For macOS

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

npm run build:mac
```

This creates:
- `dist/CVGen-1.0.0.dmg` - Disk image
- `dist/CVGen-1.0.0.zip` - Zipped app

**DMG features:**
- Drag-to-install interface
- Auto-opens in Finder
- Copies to Applications folder

**Testing:**
```bash
# Open the DMG
open dist/CVGen-1.0.0.dmg

# Or drag CVGen.app to Applications
# Then launch from Launchpad or Applications folder
```

### For Linux

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

npm run build:linux
```

This creates:
- `dist/CVGen-1.0.0.AppImage` - Universal AppImage
- `dist/cvgen_1.0.0_amd64.deb` - Debian package

**AppImage features:**
- No installation required
- Just download and run
- Auto-update support

**Debian package features:**
```bash
# Install the .deb
sudo apt install ./dist/cvgen_1.0.0_amd64.deb

# Launch from application menu or:
cvgen

# Uninstall:
sudo apt remove cvgen
```

### Build All Platforms

To build for all platforms at once (requires all platform dependencies):

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop

npm run build:all
```

## Step 7: Create GitHub Release (Optional)

For auto-updates to work, publish builds to GitHub Releases:

```bash
# First, create a GitHub repo and push your code
git init
git add .
git commit -m "CVGen Desktop v1.0.0"
git branch -M main
git remote add origin https://github.com/yourusername/CVGen.git
git push -u origin main

# Then create a release
gh release create v1.0.0 dist/* --title "CVGen Desktop v1.0.0" --notes "Initial release"
```

Or manually:
1. Go to https://github.com/yourusername/CVGen/releases
2. Click "New Release"
3. Tag: `v1.0.0`
4. Upload files from `dist/` folder
5. Publish

The `electron-updater` will automatically:
- Check for new releases on startup
- Download updates in background
- Prompt user to install
- Auto-restart to apply update

## Advanced: Customization

### Change App Name

Edit `desktop/package.json`:
```json
{
  "name": "my-cvgen",
  "productName": "My CVGen App",
  "build": {
    "appId": "com.mycompany.cvgen"
  }
}
```

### Change Icons

Replace icon files in `desktop/resources/`:
- `icon.ico` - Windows (256x256 or larger)
- `icon.icns` - macOS (1024x1024)
- `icon.png` - Linux (512x512 or larger)
- `icon.svg` - Used internally

Tools for creating icons:
- Windows: FastStone Image Viewer, ImageMagick
- macOS: IconUtility, ImageMagick
- Cross-platform: GIMP, ImageMagick

### Change Splash Screen

Edit `desktop/splash.html` to customize:
- Colors
- Logo
- Text
- Loading animation

### Change Update Server

Edit `desktop/package.json`:
```json
{
  "build": {
    "publish": {
      "provider": "github",
      "owner": "yourusername",
      "repo": "CVGen"
    }
  }
}
```

Or use other providers:
- Generic HTTP: `{ "provider": "generic", "url": "https://myserver.com/updates" }`
- S3: `{ "provider": "s3", "bucket": "my-releases" }`
- Bintray: `{ "provider": "bintray", "owner": "me" }`

## Troubleshooting

### Issue: "Python backend executable not found"

**Cause:** Build step was skipped or failed

**Solution:**
```bash
cd desktop
# macOS/Linux:
chmod +x build-python.sh && ./build-python.sh

# Windows:
build-python.bat

# Verify output exists:
ls dist-python/cvgen-backend/
```

### Issue: "Cannot find module 'electron'"

**Cause:** npm dependencies not installed

**Solution:**
```bash
cd desktop
npm install
```

### Issue: Port 8765 already in use

**Cause:** Another instance is running or different service on that port

**Solution:**
```bash
# Find process using port (macOS/Linux):
lsof -i :8765
kill -9 <PID>

# Windows:
netstat -ano | findstr :8765
taskkill /PID <PID> /F
```

### Issue: "Uvicorn not found" or "ModuleNotFoundError"

**Cause:** Python dependencies not installed

**Solution:**
```bash
pip install fastapi uvicorn pydantic
pip install -r requirements.txt
```

### Issue: Installer fails on Windows

**Cause:** Missing Visual C++ Runtime or conflicting software

**Solution:**
1. Install Visual C++ Redistributable: https://support.microsoft.com/en-us/help/2977003/
2. Run installer with admin privileges
3. Try portable exe instead: `dist/CVGen 1.0.0.exe`

### Issue: App won't start after installation

**Cause:** Python backend path incorrect or .exe permissions

**Solution:**
1. Check installation folder exists: `C:\Users\<user>\AppData\Local\Programs\CVGen`
2. Look for error in logs: `%APPDATA%\CVGen\logs\`
3. Try dev mode to get more detailed errors:
   ```bash
   npm run dev
   ```

### Issue: DevTools not appearing

**Cause:** DevTools disabled in production or renderer not loaded

**Solution:**
```bash
# Edit main.js and ensure this line exists:
if (isDevelopment) {
  mainWindow.webContents.openDevTools();
}

# Or open manually:
# Ctrl+Shift+I (Windows/Linux)
# Cmd+Option+I (macOS)
```

### Issue: Auto-updates not working

**Cause:** GitHub repo not configured or releases not published

**Solution:**
1. Verify `publish` settings in `package.json`:
   ```json
   "publish": {
     "provider": "github",
     "owner": "yourusername",
     "repo": "CVGen"
   }
   ```

2. Create GitHub releases:
   ```bash
   gh release create v1.1.0 dist/* --title "CVGen v1.1.0"
   ```

3. Check for updates in app: Help → Check for Updates

## Distribution

### For Internal/Company Use

1. Build the installer
2. Host on internal server or share drive
3. Users download and run

### For Public Distribution

1. Create GitHub releases
2. Link from website: `https://github.com/yourusername/CVGen/releases/latest`
3. Set up auto-updates (see Advanced section)
4. Consider hosting on app stores:
   - Windows Store (requires Microsoft account)
   - Mac App Store (requires Apple Developer account)
   - Snap Store for Linux (free)

### Create Installer Badge

```html
<!-- Link to latest installer -->
<a href="https://github.com/yourusername/CVGen/releases/latest">
  <img src="https://img.shields.io/github/v/release/yourusername/CVGen?label=Download%20CVGen&style=for-the-badge">
</a>
```

## Performance Benchmarks

Typical startup times after build:

| Step | Time | Notes |
|------|------|-------|
| Installer runs | 10-30s | First-time install |
| App launches | 2-5s | Windows/macOS |
| Python backend starts | 3-8s | Depends on system |
| Dashboard loads | 1-3s | Network/rendering |
| **Total** | **6-15s** | Average cold start |

After first launch (warm start): 2-5s

## Security Checklist

Before releasing:

- [ ] Remove `openDevTools()` for production
- [ ] Enable code signing (Windows: SignTool, macOS: codesign)
- [ ] Enable auto-updates for patch distribution
- [ ] Set appropriate file permissions (755 for executables)
- [ ] Test on clean machine without dev tools
- [ ] Review electron-builder security options
- [ ] Audit Python dependencies for vulnerabilities
- [ ] Enable notarization on macOS if distributing outside App Store

## Performance Optimization

1. **Reduce installer size:**
   ```bash
   # Use UPX compression (optional, may break on some systems)
   pip install pyinstaller[bootloader_mu]

   # Or remove unused Python modules before PyInstaller
   pip uninstall -y pytest black flake8 mypy
   ```

2. **Optimize Electron bundle:**
   ```bash
   # Use asar archive (done automatically by electron-builder)
   # Already enabled in package.json
   ```

3. **Reduce startup time:**
   - Lazy-load dashboard modules
   - Pre-generate quantum circuit templates
   - Cache frequently accessed data

## Next Steps

1. **Customize** - Update app name, icons, colors
2. **Test** - Run on multiple machines and OS versions
3. **Sign** - Code sign installers for distribution
4. **Release** - Publish to GitHub/website with badges
5. **Monitor** - Track crashes, feedback, usage with error reporting
6. **Update** - Regularly check for security updates

## Support & Resources

- **Electron Docs:** https://www.electronjs.org/docs
- **Electron Builder:** https://www.electron.build/
- **PyInstaller Docs:** https://pyinstaller.readthedocs.io/
- **CVGen GitHub:** https://github.com/aigambitkg/CVGen

## Contributing

To improve the desktop build:

1. Test on multiple platforms
2. Report issues with full error logs
3. Submit pull requests with improvements
4. Update documentation for changes

---

**Last Updated:** March 2026
**CVGen Version:** 1.0.0
**Electron Version:** 28.0.0
