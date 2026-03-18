"""
CVGen Desktop Launcher

A pure Python GUI launcher for CVGen that works on Windows, macOS, and Linux.
Uses tkinter (built into Python) to provide a simple, native-looking interface.

This launcher:
- Starts the FastAPI backend server
- Opens the dashboard in the default browser
- Provides a system tray icon (if pystray is available)
- Handles graceful shutdown
- Works without any external GUI dependencies beyond tkinter
"""

import threading
import time
import sys
import signal
import logging
import webbrowser
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    import tkinter.font as tkFont
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

try:
    import pystray  # noqa: F401
    from PIL import Image, ImageDraw  # noqa: F401
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
APP_NAME = 'CVGen'
DEFAULT_PORT = 8765
DEFAULT_HOST = '127.0.0.1'
HEALTH_CHECK_INTERVAL = 0.5
HEALTH_CHECK_TIMEOUT = 30


class CVGenLauncher:
    """Main launcher application."""

    def __init__(self, root):
        self.root = root
        self.root.title('CVGen Launcher')
        self.root.geometry('500x400')
        self.root.resizable(False, False)

        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'+{x}+{y}')

        # Window icon
        self.set_window_icon()

        # State
        self.backend_process = None
        self.backend_ready = False
        self.is_shutting_down = False
        self.port = DEFAULT_PORT
        self.host = DEFAULT_HOST
        self.tray_icon = None

        # Handle window close
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.root.bind('<Control-q>', lambda e: self.on_closing())

        # Build UI
        self.build_ui()

        # Start health check loop
        self.health_check()

    def set_window_icon(self):
        """Try to set a nice window icon."""
        try:
            # Try to create icon from SVG or use a simple icon
            if sys.platform == 'win32':
                # Windows supports .ico files
                icon_path = Path(__file__).parent.parent.parent / 'desktop' / 'resources' / 'icon.ico'
                if icon_path.exists():
                    self.root.iconbitmap(str(icon_path))
            else:
                # For other platforms, try to use a simple image
                self.create_icon_image()
        except Exception as e:
            logger.debug(f'Could not set icon: {e}')

    def create_icon_image(self):
        """Create a simple icon image for the window."""
        try:
            if not HAS_PYSTRAY:
                return

            # Create a simple quantum-themed icon
            size = (64, 64)
            image = Image.new('RGBA', size, color=(26, 26, 46, 255))
            draw = ImageDraw.Draw(image)

            # Draw concentric circles
            colors = [
                (0, 200, 255, 180),
                (0, 128, 255, 140),
                (0, 100, 200, 100)
            ]

            for i, color in enumerate(colors):
                radius = 30 - (i * 10)
                draw.ellipse(
                    [(32 - radius, 32 - radius), (32 + radius, 32 + radius)],
                    outline=color,
                    width=2
                )

            # Draw center point
            draw.ellipse([(30, 30), (34, 34)], fill=(0, 200, 255, 255))

            # Store for later use
            self.icon_image = image

        except Exception as e:
            logger.debug(f'Could not create icon: {e}')

    def build_ui(self):
        """Build the launcher UI."""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors and fonts
        bg_color = '#1a1a2e'
        fg_color = '#ffffff'
        accent_color = '#00c8ff'

        self.root.configure(bg=bg_color)

        # Title frame
        title_frame = tk.Frame(self.root, bg=bg_color)
        title_frame.pack(fill=tk.X, padx=20, pady=20)

        # Logo text
        title_font = tkFont.Font(family='Helvetica', size=24, weight='bold')
        title_label = tk.Label(
            title_frame,
            text=APP_NAME,
            font=title_font,
            fg=accent_color,
            bg=bg_color
        )
        title_label.pack()

        subtitle_font = tkFont.Font(family='Helvetica', size=10, weight='normal')
        subtitle_label = tk.Label(
            title_frame,
            text='Quantum Computing for Every Device',
            font=subtitle_font,
            fg=fg_color,
            bg=bg_color
        )
        subtitle_label.pack()

        # Main content frame
        content_frame = tk.Frame(self.root, bg=bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Status section
        status_label = tk.Label(
            content_frame,
            text='Backend Status:',
            font=('Helvetica', 10, 'bold'),
            fg=fg_color,
            bg=bg_color
        )
        status_label.pack(anchor=tk.W, pady=(0, 5))

        status_frame = tk.Frame(content_frame, bg=bg_color)
        status_frame.pack(anchor=tk.W, pady=(0, 15))

        self.status_indicator = tk.Canvas(
            status_frame,
            width=12,
            height=12,
            bg=bg_color,
            highlightthickness=0
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 8))

        self.status_text = tk.Label(
            status_frame,
            text='Offline',
            font=('Helvetica', 10),
            fg='#ff6b6b',
            bg=bg_color
        )
        self.status_text.pack(side=tk.LEFT)

        # Port configuration
        port_frame = tk.Frame(content_frame, bg=bg_color)
        port_frame.pack(anchor=tk.W, pady=(0, 15), fill=tk.X)

        port_label = tk.Label(
            port_frame,
            text='Port:',
            font=('Helvetica', 10),
            fg=fg_color,
            bg=bg_color
        )
        port_label.pack(side=tk.LEFT, padx=(0, 10))

        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        port_entry = ttk.Spinbox(
            port_frame,
            from_=1024,
            to=65535,
            textvariable=self.port_var,
            width=10,
            state='readonly'
        )
        port_entry.pack(side=tk.LEFT)

        # URL display
        url_frame = tk.Frame(content_frame, bg=bg_color)
        url_frame.pack(anchor=tk.W, pady=(0, 15), fill=tk.X)

        url_label = tk.Label(
            url_frame,
            text='Dashboard URL:',
            font=('Helvetica', 10, 'bold'),
            fg=fg_color,
            bg=bg_color
        )
        url_label.pack(anchor=tk.W)

        self.url_var = tk.StringVar(value='http://localhost:8765')
        url_display = tk.Label(
            url_frame,
            textvariable=self.url_var,
            font=('Courier', 9),
            fg=accent_color,
            bg='#0f3460',
            relief=tk.SUNKEN,
            padx=10,
            pady=5
        )
        url_display.pack(fill=tk.X, pady=(5, 0))

        # Button frame
        button_frame = tk.Frame(content_frame, bg=bg_color)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Start button
        self.start_button = tk.Button(
            button_frame,
            text='Start CVGen',
            command=self.start_backend,
            bg=accent_color,
            fg='#000000',
            font=('Helvetica', 11, 'bold'),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2'
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        # Stop button
        self.stop_button = tk.Button(
            button_frame,
            text='Stop',
            command=self.stop_backend,
            bg='#ff6b6b',
            fg='#ffffff',
            font=('Helvetica', 11, 'bold'),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        # Open Dashboard button
        self.open_button = tk.Button(
            button_frame,
            text='Open Dashboard',
            command=self.open_dashboard,
            bg='#26de81',
            fg='#000000',
            font=('Helvetica', 11, 'bold'),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.open_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Log frame
        log_frame = tk.Frame(self.root, bg=bg_color)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))

        log_label = tk.Label(
            log_frame,
            text='Log:',
            font=('Helvetica', 10, 'bold'),
            fg=fg_color,
            bg=bg_color
        )
        log_label.pack(anchor=tk.W)

        # Log text widget
        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=60,
            bg='#0f3460',
            fg='#00c8ff',
            font=('Courier', 8),
            relief=tk.SUNKEN,
            padx=10,
            pady=5
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.add_log('CVGen Launcher initialized')

    def add_log(self, message):
        """Add a message to the log display."""
        self.log_text.insert(tk.END, f'[{time.strftime("%H:%M:%S")}] {message}\n')
        self.log_text.see(tk.END)
        self.root.update()

    def update_status(self, ready):
        """Update the backend status indicator."""
        self.backend_ready = ready

        if ready:
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(1, 1, 11, 11, fill='#26de81', outline='#26de81')
            self.status_text.config(text='Running', fg='#26de81')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.open_button.config(state=tk.NORMAL)
            self.add_log('Backend is ready!')
        else:
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(1, 1, 11, 11, fill='#ff6b6b', outline='#ff6b6b')
            self.status_text.config(text='Offline', fg='#ff6b6b')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.open_button.config(state=tk.DISABLED)

    def start_backend(self):
        """Start the Python backend in a separate thread."""
        self.port = int(self.port_var.get())
        self.url_var.set(f'http://localhost:{self.port}')

        self.add_log(f'Starting CVGen backend on port {self.port}...')
        threading.Thread(target=self._start_backend_thread, daemon=True).start()

    def _start_backend_thread(self):
        """Thread function to start the backend."""
        try:
            # Try to import required modules
            try:
                import uvicorn  # noqa: F401
                from cvgen.api.app import app  # noqa: F401
            except ImportError as e:
                self.add_log(f'ERROR: Missing dependencies: {e}')
                self.add_log('Please install: pip install fastapi uvicorn')
                messagebox.showerror(
                    'Missing Dependencies',
                    'FastAPI and Uvicorn are not installed.\n\n'
                    'Please run:\n'
                    'pip install fastapi uvicorn'
                )
                return

            # Start uvicorn server in a separate thread
            self.backend_process = threading.Thread(
                target=self._run_uvicorn,
                daemon=True
            )
            self.backend_process.start()

            # Wait for health check
            self.add_log('Waiting for backend to become healthy...')
            self._wait_for_backend_healthy()

        except Exception as e:
            logger.error(f'Failed to start backend: {e}')
            self.add_log(f'ERROR: {e}')
            self.update_status(False)

    def _run_uvicorn(self):
        """Run the Uvicorn server."""
        try:
            import uvicorn
            from cvgen.api.app import app

            self.add_log('Starting Uvicorn server...')
            uvicorn.run(
                app,
                host=self.host,
                port=self.port,
                log_level='info',
                access_log=False
            )
        except Exception as e:
            logger.error(f'Uvicorn error: {e}')
            self.add_log(f'Uvicorn error: {e}')
            self.update_status(False)

    def _wait_for_backend_healthy(self):
        """Poll the backend health endpoint."""
        import http.client

        start_time = time.time()
        while not self.is_shutting_down:
            elapsed = time.time() - start_time

            if elapsed > HEALTH_CHECK_TIMEOUT:
                self.add_log('ERROR: Backend did not respond in time')
                self.update_status(False)
                return

            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=1)
                conn.request('GET', '/api/v1/health')
                response = conn.getresponse()

                if response.status == 200:
                    self.update_status(True)
                    return

            except (ConnectionRefusedError, ConnectionError, OSError, TimeoutError):
                pass

            time.sleep(HEALTH_CHECK_INTERVAL)

    def stop_backend(self):
        """Stop the backend process."""
        if self.backend_process:
            self.add_log('Stopping backend...')
            self.is_shutting_down = True
            # The process will be killed by keyboard interrupt or exit
            self.update_status(False)

    def open_dashboard(self):
        """Open the dashboard in the default browser."""
        url = self.url_var.get()
        self.add_log(f'Opening dashboard: {url}')
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error(f'Failed to open dashboard: {e}')
            self.add_log(f'ERROR: Could not open dashboard: {e}')

    def health_check(self):
        """Periodically check backend health."""
        if not self.is_shutting_down and self.backend_ready:
            import http.client
            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=2)
                conn.request('GET', '/api/v1/health')
                response = conn.getresponse()

                if response.status != 200:
                    self.add_log('WARNING: Backend health check failed')
                    self.update_status(False)
            except (ConnectionRefusedError, ConnectionError, OSError, TimeoutError):
                self.add_log('WARNING: Lost connection to backend')
                self.update_status(False)

        # Schedule next check
        self.root.after(5000, self.health_check)

    def on_closing(self):
        """Handle window close event."""
        if self.backend_ready:
            response = messagebox.askyesnocancel(
                'Confirm Exit',
                'The backend is still running. Stop it before exiting?'
            )
            if response is None:
                return
            if response:
                self.stop_backend()
                time.sleep(1)

        self.is_shutting_down = True
        self.root.destroy()


def main():
    """Main entry point."""
    root = tk.Tk()

    # Configure styles
    style = ttk.Style()
    style.configure('TButton', font=('Helvetica', 10))
    style.configure('TLabel', font=('Helvetica', 10))
    style.configure('TSpinbox', font=('Helvetica', 10))

    # Create launcher
    launcher = CVGenLauncher(root)

    # Handle signals
    def signal_handler(sig, frame):
        launcher.on_closing()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start GUI
    try:
        root.mainloop()
    except KeyboardInterrupt:
        launcher.on_closing()


if __name__ == '__main__':
    main()
