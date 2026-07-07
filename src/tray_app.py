"""
tray_app.py

Runs quietly in the Windows system tray, checking Outlook for new
printer scans every few minutes so you don't have to run anything
manually as emails come in. New scans are pulled down silently in the
background - open the review window whenever you're ready to go
through them (click the tray icon, or right-click it for the menu).

Run with: python src/tray_app.py
"""

import os
import sys
import subprocess
import threading
import time

import pythoncom
import pystray
from PIL import Image, ImageDraw

import paths
import outlook_watcher


DEFAULT_INTERVAL_MINUTES = 7


def load_check_interval():
    try:
        settings = outlook_watcher.load_settings()
        return settings.get("background_check_interval_minutes", DEFAULT_INTERVAL_MINUTES)
    except Exception:
        return DEFAULT_INTERVAL_MINUTES


def make_icon_image():
    """A simple generated icon so we don't need to ship a separate
    .ico file. Feel free to swap this out for a real icon later - just
    replace this function with one that does Image.open('icon.ico')."""
    size = 64
    image = Image.new("RGB", (size, size), "#2b6cb0")
    draw = ImageDraw.Draw(image)
    draw.rectangle((14, 10, 50, 54), outline="white", width=3)
    draw.line((20, 24, 44, 24), fill="white", width=2)
    draw.line((20, 32, 44, 32), fill="white", width=2)
    draw.line((20, 40, 36, 40), fill="white", width=2)
    return image


def _do_check(icon):
    """The actual Outlook check. COM (which pywin32/Outlook automation
    relies on) needs to be initialized on whatever thread it's used
    from - this isn't the main thread, so we do that explicitly here
    rather than relying on it happening automatically."""
    pythoncom.CoInitialize()
    try:
        settings = outlook_watcher.load_settings()
        saved = outlook_watcher.find_and_save_scans(settings)
        if icon:
            icon.title = f"HOA Doc Filer - {len(saved)} new scan(s) pulled"
    except Exception as e:
        if icon:
            icon.title = f"HOA Doc Filer - check failed: {e}"
    finally:
        pythoncom.CoUninitialize()


def check_now(icon=None, item=None):
    """Tray menu handler - runs a check immediately in its own thread
    so it never freezes the tray icon while Outlook is contacted."""
    threading.Thread(target=_do_check, args=(icon,), daemon=True).start()


def open_review_window(icon=None, item=None):
    """Launches the review window as its own separate process. Keeping
    it fully separate from the tray icon's process avoids a whole
    class of Tkinter/pystray event-loop conflicts."""
    base_dir = paths.get_base_dir()
    main_path = os.path.join(base_dir, "src", "main.py")
    subprocess.Popen([sys.executable, main_path])


def background_loop(icon):
    interval_seconds = load_check_interval() * 60
    while True:
        _do_check(icon)
        time.sleep(interval_seconds)


def quit_app(icon, item):
    icon.stop()


def main():
    icon = pystray.Icon(
        "hoa_doc_filer",
        make_icon_image(),
        "HOA Doc Filer",
        menu=pystray.Menu(
            pystray.MenuItem("Open Review Window", open_review_window, default=True),
            pystray.MenuItem("Check Now", check_now),
            pystray.MenuItem("Quit", quit_app),
        ),
    )

    threading.Thread(target=background_loop, args=(icon,), daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()