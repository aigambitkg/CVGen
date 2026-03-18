@echo off
REM CVGen Desktop - Python Backend Build Script (Windows)
REM
REM Builds the CVGen Python backend into a standalone executable
REM using PyInstaller. The executable is then bundled into the Electron app.

setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo.
echo ========================================
echo CVGen Python Backend Build
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or later from https://www.python.org
    pause
    exit /b 1
)

echo Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo Building CVGen Python Backend...
echo.

REM Build with PyInstaller
pyinstaller ^
  --name cvgen-backend ^
  --onedir ^
  --noconfirm ^
  --clean ^
  --add-data "src/cvgen/web/static;cvgen/web/static" ^
  --hidden-import uvicorn ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import cvgen.api.app ^
  --hidden-import cvgen.api.routes.circuits ^
  --hidden-import cvgen.api.routes.agents ^
  --hidden-import cvgen.api.routes.backends ^
  --hidden-import cvgen.api.routes.jobs ^
  --hidden-import cvgen.api.routes.quantum_ask ^
  --hidden-import cvgen.api.websocket ^
  --hidden-import cvgen.backends.simulator ^
  --hidden-import cvgen.backends.origin_pilot ^
  --hidden-import cvgen.agents ^
  --hidden-import cvgen.orchestrator ^
  --hidden-import cvgen.bridge ^
  --hidden-import cvgen.rag ^
  --collect-all cvgen ^
  src/cvgen/desktop_entry.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo Creating output directory...
if exist dist-python rmdir /s /q dist-python
mkdir dist-python

echo Copying Python backend...
xcopy /E /I /Y dist\cvgen-backend dist-python\cvgen-backend
if errorlevel 1 (
    echo ERROR: Failed to copy backend executable
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Output location: dist-python/
echo.
echo Next steps:
echo 1. npm install
echo 2. npm run build:win
echo.
pause
