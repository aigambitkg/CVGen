"""
CVGen Desktop Entry Point

This is the entry point for the PyInstaller-bundled CVGen backend.
It's used when building the standalone executable for the Electron desktop app.

When PyInstaller bundles this script, all imports are collected and included
in the binary, making it a complete, self-contained application.
"""

import sys
import os
import logging

# Configure logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Configure environment for bundled execution."""
    # Detect if running as PyInstaller bundle
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        bundle_dir = sys._MEIPASS
        logger.info(f"Running as bundled application from {bundle_dir}")

        # Set up static files path
        static_dir = os.path.join(bundle_dir, "cvgen", "web", "static")
        if os.path.exists(static_dir):
            os.environ.setdefault("CVGEN_STATIC_DIR", static_dir)
            logger.info(f"Static files directory: {static_dir}")
    else:
        # Running in development mode
        logger.info("Running in development mode")


def main():
    """Main entry point for the desktop application."""
    try:
        # Set up environment
        setup_environment()

        # Import FastAPI and uvicorn after environment is configured
        import uvicorn
        from cvgen.api.app import app

        # Get configuration from environment
        port = int(os.environ.get("CVGEN_PORT", "8765"))
        host = os.environ.get("CVGEN_HOST", "127.0.0.1")
        log_level = os.environ.get("CVGEN_LOG_LEVEL", "info")

        logger.info(f"Starting CVGen backend on {host}:{port}")
        logger.info("Quantum Computing for Every Device")

        # Run uvicorn server
        uvicorn.run(
            app, host=host, port=port, log_level=log_level, access_log=True, use_colors=True
        )

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Please ensure all dependencies are installed:")
        logger.error("  pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
