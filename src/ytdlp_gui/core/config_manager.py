import json
import logging
import os
import tempfile
from pathlib import Path

from ytdlp_gui.utils.platform_utils import get_config_dir, get_default_download_dir

DEFAULT_CONFIG = {
    "default_folder": "",
    "theme": "dark",
    "ytdlp_path": "",
    "ffmpeg_path": "",
    "aria2c_path": "",
    "aria2c_enabled": False,
    "aria2c_connections": 16,
    "cookie_mode": "none",
    "cookie_browser": "chrome",
    "cookie_file": "",
    "cookie_json": "",
    "proxy": "",
    "impersonate_enabled": False,
    "impersonate_browser": "chrome",
    "user_agent": "",
    "referer": "",
    "custom_headers": "",
    "quality_preset": "Best MP4",
    "format_string": "bestvideo+bestaudio/best",
    "rate_limit": 0,
    "retries": 3,
    "concurrent_limit": 3,
    "audio_extract": False,
    "audio_format": "mp3",
    "audio_quality": 5,
    "embed_thumbnail": False,
    "write_metadata": False,
    "subtitle_langs": "",
    "sleep_interval": 0,
    "sleep_interval_max": 0,
    "sleep_requests": 0,
    "sleep_subtitles": 0,
    "fragment_retries": 10,
    "anti_block_mode": False,
}


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> dict:
    """Load config from disk, merging saved values over defaults."""
    config = dict(DEFAULT_CONFIG)
    path = get_config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger(__name__).warning(
                "Config file corrupted or unreadable, using defaults: %s", e
            )

    # Fill default_folder if empty
    if not config["default_folder"]:
        config["default_folder"] = str(get_default_download_dir())

    return config


def save_config(config: dict) -> None:
    """Write config dict to disk as JSON (atomic write)."""
    path = get_config_path()
    try:
        # Write to temp file in same directory, then rename for atomicity
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, suffix=".tmp", prefix="config_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, path)
        except BaseException:
            # Clean up temp file on any error
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except OSError as e:
        logging.getLogger(__name__).warning("Failed to save config: %s", e)
