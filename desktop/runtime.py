"""Platform paths shared by the desktop host and frozen entry point."""
import os
from pathlib import Path
import sys


def default_data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Mystery"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Mystery"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "Mystery"


def bundled_node():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    binary = root / "runtime" / ("node.exe" if sys.platform == "win32" else "node")
    return str(binary) if binary.is_file() else None


def webview_gui():
    return {"win32": "edgechromium", "darwin": "cocoa"}.get(sys.platform)
