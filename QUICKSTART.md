# CVGen Desktop - Quick Start Guide

Get your CVGen desktop application built and running in 5 minutes.

## What You Get

After following this guide, you'll have:
- A Windows installer (.exe), macOS DMG (.dmg), or Linux AppImage (.AppImage)
- Auto-updates via GitHub Releases
- System tray icon
- Beautiful splash screen
- One-click installation for users

## Prerequisites (2 minutes)

### Install Node.js 18+
- **Windows/macOS:** Download from https://nodejs.org/
- **Linux:** `sudo apt install nodejs npm` (Ubuntu/Debian)

### Install Python 3.11+
- **Windows/macOS:** Download from https://www.python.org/
- **Linux:** `sudo apt install python3.11`

### Verify Installation
```bash
node --version   # Should be 18.0.0 or higher
npm --version    # Should be 9.0.0 or higher
python --version # Should be 3.11.0 or higher
```

## Step 1: Build Python Backend (3 minutes)

### macOS/Linux
```bash
cd /home/kevin/CVGEN/cvgen-build/desktop
chmod +x build-python.sh
./build-python.sh
```

### Windows
```bash
cd C:\path\to\cvgen-build\desktop
build-python.bat
```

## Step 2: Install Electron Dependencies (2 minutes)

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop
npm install
```

## Step 3: Test Locally (1 minute)

```bash
cd /home/kevin/CVGEN/cvgen-build/desktop
npm run dev
```

## Step 4: Build for Your Platform (5-10 minutes)

### For Windows
```bash
npm run build:win
```

### For macOS
```bash
npm run build:mac
```

### For Linux
```bash
npm run build:linux
```

## Done!

Installers are in the `dist/` folder. Users can download and install with one click.

---

For detailed information, see `DESKTOP_BUILD.md`.
