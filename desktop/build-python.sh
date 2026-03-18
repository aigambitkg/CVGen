#!/bin/bash
#
# CVGen Desktop - Python Backend Build Script (macOS/Linux)
#
# Builds the CVGen Python backend into a standalone executable
# using PyInstaller. The executable is then bundled into the Electron app.

set -e

cd "$(dirname "$0")/.."

echo
echo "========================================"
echo "CVGen Python Backend Build"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python: $PYTHON_VERSION"

# Check Python version is 3.11+
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11 or later is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "Installing PyInstaller..."
pip3 install pyinstaller --quiet

echo "Building CVGen Python Backend..."
echo

# Build with PyInstaller
python3 -m PyInstaller \
  --name cvgen-backend \
  --onedir \
  --noconfirm \
  --clean \
  --add-data "src/cvgen/web/static:cvgen/web/static" \
  --hidden-import uvicorn \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import cvgen.api.app \
  --hidden-import cvgen.api.routes.circuits \
  --hidden-import cvgen.api.routes.agents \
  --hidden-import cvgen.api.routes.backends \
  --hidden-import cvgen.api.routes.jobs \
  --hidden-import cvgen.api.routes.quantum_ask \
  --hidden-import cvgen.api.websocket \
  --hidden-import cvgen.backends.simulator \
  --hidden-import cvgen.backends.origin_pilot \
  --hidden-import cvgen.agents \
  --hidden-import cvgen.orchestrator \
  --hidden-import cvgen.bridge \
  --hidden-import cvgen.rag \
  --collect-all cvgen \
  src/cvgen/desktop_entry.py

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: PyInstaller build failed!"
    exit 1
fi

echo
echo "Creating output directory..."
rm -rf dist-python
mkdir -p dist-python

echo "Copying Python backend..."
cp -r dist/cvgen-backend/* dist-python/

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to copy backend executable"
    exit 1
fi

echo
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo
echo "Output location: dist-python/"
echo
echo "Next steps:"
echo "1. npm install"
echo "2. npm run build:$(uname -s | tr '[:upper:]' '[:lower:]' | sed 's/darwin/mac/')"
echo
