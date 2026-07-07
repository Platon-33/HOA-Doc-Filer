"""
paths.py

One shared function for finding the project's base folder (the one that
contains config/, downloads/, sorted/, logs/). This needs special
handling because of how the app will eventually run in two different
modes:

1. As plain Python scripts (what we've been doing so far) - the base
   folder is one level up from this src/ folder.

2. As a packaged .exe (via PyInstaller) - all the Python files get
   bundled INSIDE the .exe and extracted to a temporary folder at
   runtime. If we used the old "__file__" trick in that mode, every
   config/downloads/sorted path would point into that temp folder and
   vanish when the program closes. Instead, we want those folders to
   live next to the actual .exe file on disk, so your config edits and
   downloaded PDFs persist between runs.

Every other file that needs to find config/downloads/sorted should
import get_base_dir() from here instead of doing its own __file__ math.
"""

import os
import sys


def get_base_dir():
    if getattr(sys, "frozen", False):
        # Running as a packaged .exe - use the folder the .exe itself is sitting in.
        return os.path.dirname(sys.executable)
    # Running as a plain script - src/paths.py -> go up one level.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))