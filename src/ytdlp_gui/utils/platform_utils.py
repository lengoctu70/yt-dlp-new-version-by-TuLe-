import os
import sys
from pathlib import Path


def get_config_dir() -> Path:
    """Return config directory, respecting XDG on Linux."""
    if sys.platform == "linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            config_dir = Path(xdg) / "ytdlp-gui"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir
    config_dir = Path.home() / ".ytdlp-gui"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_default_download_dir() -> Path:
    """Return ~/Downloads, creating it if missing."""
    download_dir = Path.home() / "Downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir


def ensure_dirs_exist() -> None:
    """Ensure config and download directories exist."""
    get_config_dir()
    get_default_download_dir()
