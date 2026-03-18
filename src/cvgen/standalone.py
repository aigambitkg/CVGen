#!/usr/bin/env python3
"""
CVGen Standalone — One-Click Quantum Computing Desktop App.

This is the single entry point for the packaged desktop application.
When the user double-clicks the CVGen executable, this script:
1. Starts the FastAPI server in a background thread
2. Opens the dashboard in the default browser
3. Shows a simple system tray / terminal status
4. Handles graceful shutdown on Ctrl+C or window close
"""

import os
import sys
import time
import signal
import threading
import webbrowser
import socket
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[CVGen] %(message)s"
)
log = logging.getLogger("cvgen.standalone")

# Default port
PORT = 8765
HOST = "127.0.0.1"


def find_free_port(start=8765, end=8800):
    """Find a free port in range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


def wait_for_server(host, port, timeout=30):
    """Wait until the server is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            time.sleep(0.3)
    return False


def start_server(host, port):
    """Start the FastAPI server."""
    import uvicorn
    from cvgen.api.app import app
    uvicorn.run(app, host=host, port=port, log_level="warning")


def print_banner(port):
    """Print startup banner."""
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║                                          ║")
    print("  ║   ⚛  CVGen — Quantum Computing          ║")
    print("  ║      for Every Device                    ║")
    print("  ║                                          ║")
    print(f"  ║   Dashboard: http://localhost:{port}       ║")
    print("  ║                                          ║")
    print("  ║   Press Ctrl+C to quit                   ║")
    print("  ║                                          ║")
    print("  ╚══════════════════════════════════════════╝")
    print()


def main():
    global PORT

    PORT = find_free_port()

    print()
    print("  ⚛  CVGen is starting...")
    print(f"     Port: {PORT}")
    print()

    # Start server in background thread
    server_thread = threading.Thread(
        target=start_server,
        args=(HOST, PORT),
        daemon=True
    )
    server_thread.start()

    # Wait for server to be ready
    print("     Waiting for quantum backend...", end="", flush=True)
    if wait_for_server(HOST, PORT, timeout=30):
        print(" Ready!")
        print_banner(PORT)

        # Open browser
        url = f"http://localhost:{PORT}"
        print(f"  Opening {url} in your browser...")
        webbrowser.open(url)
        print()
        print("  CVGen is running. Press Ctrl+C to stop.")
        print()

        # Keep alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print()
            print("  Shutting down CVGen... Goodbye!")
            sys.exit(0)
    else:
        print(" FAILED!")
        print()
        print("  ERROR: Server did not start within 30 seconds.")
        print("  Please check the logs or try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
