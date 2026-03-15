"""Entry point for PyInstaller-bundled backend.

This file is used as the PyInstaller entry point because backend/main.py
uses relative imports that don't work as a direct script.
"""
import sys
import os
from pathlib import Path

# When frozen (PyInstaller), store data in AppData instead of temp dir
if getattr(sys, "frozen", False):
    DATA_DIR = Path(os.environ.get("APPDATA", "")) / "ITManager-Dashboard"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["ITMANAGER_DATA_DIR"] = str(DATA_DIR)

import uvicorn
from backend.main import app  # noqa: E402

if __name__ == "__main__":
    port = 8010
    # Allow --port argument from Tauri sidecar
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
