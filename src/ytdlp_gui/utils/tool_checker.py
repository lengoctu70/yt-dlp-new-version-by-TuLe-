import shutil
from pathlib import Path


def find_tool(name: str, custom_path: str = "") -> str | None:
    """Find a tool by custom path or system PATH."""
    if custom_path and Path(custom_path).is_file():
        return custom_path
    return shutil.which(name)


def find_ffmpeg(custom_path: str = "") -> str | None:
    return find_tool("ffmpeg", custom_path)


def find_aria2c(custom_path: str = "") -> str | None:
    return find_tool("aria2c", custom_path)
