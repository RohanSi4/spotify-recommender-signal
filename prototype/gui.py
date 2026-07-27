"""Compatibility launcher for the maintained Streamlit interface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    app = Path(__file__).with_name("gui_streamlit.py")
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)]))
