"""
MemoMe Launcher
===============
Entry point for the packaged app (PyInstaller).

What this does:
  1. Checks Ollama is reachable — shows a friendly dialog if not
  2. Starts the FastAPI server (uvicorn) in a background thread
  3. Waits up to 8 seconds for the server to accept connections
  4. Opens http://localhost:8765 in the user's default browser
  5. Shows a system tray icon with Open / Quit menu
  6. On Quit: stops uvicorn cleanly, exits the process

Compatible with: Windows 10/11, macOS 12+
Requires:        pystray, Pillow  (both bundled by PyInstaller)
"""

from __future__ import annotations
import multiprocessing
multiprocessing.freeze_support()   # MUST be first on Windows

import os
import sys
import time
import socket
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

# ── Resolve paths whether running frozen or from source ─────────────────────
if getattr(sys, "frozen", False):
    # Running inside a PyInstaller bundle
    BASE_DIR = sys._MEIPASS          # unpacked bundle temp dir
    DATA_DIR = os.path.dirname(sys.executable)   # next to the .exe / .app
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

os.chdir(BASE_DIR)   # server.py resolves "static/" and "data/" relative to cwd

# Put bundled packages on the path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

PORT = 8765
URL  = f"http://localhost:{PORT}"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _port_open(host: str = "localhost", port: int = PORT) -> bool:
    """Return True if something is accepting connections on the port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _wait_for_server(timeout: float = 12.0) -> bool:
    """Poll until the server is up or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open():
            return True
        time.sleep(0.3)
    return False


def _check_ollama() -> bool:
    """Return True if Ollama's API port (11434) is reachable."""
    return _port_open("localhost", 11434)


def _show_error(title: str, msg: str) -> None:
    """Display a Tkinter error dialog (works without a visible window)."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, msg)
    root.destroy()


# ── Server thread ─────────────────────────────────────────────────────────────
_server_thread: threading.Thread | None = None
_shutdown_event = threading.Event()


def _run_server() -> None:
    """Run uvicorn in this thread. Exits when _shutdown_event is set."""
    import uvicorn

    # server.py imports config from core/, so make sure BASE_DIR is in path
    config = uvicorn.Config(
        "server:app",
        host="127.0.0.1",   # localhost only — not exposed to LAN
        port=PORT,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    # Run in a way we can stop cleanly
    loop_thread = threading.Thread(target=server.run, daemon=True)
    loop_thread.start()

    _shutdown_event.wait()   # block until Quit is clicked
    server.should_exit = True
    loop_thread.join(timeout=5)


# ── System tray ───────────────────────────────────────────────────────────────
def _make_icon():
    """Draw the MemoMe tray icon programmatically (no external image file)."""
    from PIL import Image, ImageDraw
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Purple filled circle
    draw.ellipse([4, 4, size - 4, size - 4], fill=(124, 58, 237, 255))
    # White inner circle
    draw.ellipse([20, 20, size - 20, size - 20], fill=(255, 255, 255, 200))
    return img


def _open_browser(icon=None, item=None) -> None:
    webbrowser.open(URL)


def _quit_app(icon, item) -> None:
    icon.stop()
    _shutdown_event.set()
    # Give server a moment to shut down before hard exit
    time.sleep(1.5)
    os._exit(0)


def _start_tray() -> None:
    """Build the system tray icon and start its event loop (blocking)."""
    import pystray

    icon = pystray.Icon(
        name  = "MemoMe",
        icon  = _make_icon(),
        title = "MemoMe — Running",
        menu  = pystray.Menu(
            pystray.MenuItem("Open MemoMe",  _open_browser, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",         _quit_app),
        ),
    )
    icon.run()   # blocks — must be called from main thread


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    # 1. Warn if Ollama is not running (non-blocking — user can start it later)
    if not _check_ollama():
        _show_error(
            "Ollama not found",
            "MemoMe needs Ollama to translate speech.\n\n"
            "Please:\n"
            "  1. Download Ollama from https://ollama.com\n"
            "  2. Install and start it\n"
            "  3. Run:  ollama pull qwen3.5:9b\n\n"
            "MemoMe will still start — you can open it once Ollama is ready.\n"
            "The status badge will show 'Ready' when everything is connected."
        )

    # 2. Start the FastAPI server in a background thread
    global _server_thread
    _server_thread = threading.Thread(target=_run_server, daemon=True, name="uvicorn")
    _server_thread.start()

    # 3. Wait for server, then open browser
    def _open_when_ready():
        if _wait_for_server(timeout=12):
            webbrowser.open(URL)
        else:
            _show_error(
                "MemoMe failed to start",
                f"The server did not respond on port {PORT} within 12 seconds.\n\n"
                "Check that nothing else is using that port, then try again."
            )

    threading.Thread(target=_open_when_ready, daemon=True).start()

    # 4. Show system tray icon (blocks main thread — required by macOS)
    _start_tray()


if __name__ == "__main__":
    main()
