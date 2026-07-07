"""
main.py

The single entry point for the whole app. This is what gets packaged
into the .exe - one double-click does everything:

1. Checks Outlook for new printer scan emails and pulls down any PDFs
2. Opens the review window so you can confirm/correct and file them

Run with: python src/main.py
(or just double-click the packaged .exe once it's built)
"""

import sys
import tkinter as tk
from tkinter import messagebox

import outlook_watcher
import review_app


def main():
    # Step 1: pull any new scans from Outlook first, so the review
    # window has the latest PDFs to work through.
    try:
        settings = outlook_watcher.load_settings()
        saved = outlook_watcher.find_and_save_scans(settings)
        print(f"Pulled {len(saved)} new PDF(s) from Outlook.")
    except Exception as e:
        # Don't let an Outlook hiccup block you from reviewing PDFs
        # you already have sitting in the downloads folder - just warn
        # and continue into the review window.
        print(f"Warning: couldn't check Outlook for new scans: {e}")

    # Step 2: open the review window
    root = tk.Tk()
    try:
        app = review_app.ReviewApp(root)
    except Exception as e:
        messagebox.showerror("Startup error", f"Couldn't start the review window:\n{e}")
        sys.exit(1)
    root.mainloop()


if __name__ == "__main__":
    main()