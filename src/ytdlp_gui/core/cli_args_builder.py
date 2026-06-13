"""Build a yt-dlp CLI argument list from the app config.

Used when the user points the app at a custom downloaded yt-dlp binary.
Mirrors Downloader.build_opts() so both engines behave identically
(referer/headers, cookies, aria2c, audio extraction, throttling).
"""

import logging
from pathlib import Path

from ytdlp_gui.utils.tool_checker import find_ffmpeg, find_aria2c
from ytdlp_gui.utils.cookie_converter import save_json_cookies_to_temp
from ytdlp_gui.utils.sanitize import sanitize_filename

logger = logging.getLogger(__name__)

SOCKET_TIMEOUT = 30
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
ARIA2C_CHUNK_SIZE = "1M"

# Machine-readable progress line emitted via --progress-template.
# Parsed by CliDownloader; fields separated by "|".
PROGRESS_PREFIX = "CKPROG|"
PROGRESS_TEMPLATE = (
    "download:" + PROGRESS_PREFIX
    + "%(progress.downloaded_bytes)s|%(progress.total_bytes)s|"
    + "%(progress.total_bytes_estimate)s|%(progress.speed)s|"
    + "%(progress.eta)s|%(progress.filename)s"
)

_MEDIA_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v",
    ".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma",
    ".srt", ".vtt", ".ass", ".ssa", ".sub",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff",
})


def has_media_extension(name: str) -> bool:
    """Check if filename has a recognized media extension.

    Avoids false positives from dots in titles like '7.1 - Origins'.
    """
    return Path(name).suffix.lower() in _MEDIA_EXTENSIONS


def build_output_template(folder: str, filename: str) -> str:
    """Resolve output template, preserving user extension when present."""
    if filename:
        safe_name = sanitize_filename(filename)
        if not safe_name or safe_name == "download":
            safe_name = "%(title)s"
        outtmpl = str(Path(folder) / safe_name)
        if not has_media_extension(safe_name):
            outtmpl += ".%(ext)s"
        return outtmpl
    return str(Path(folder) / "%(title)s.%(ext)s")


def build_cli_args(config: dict, folder: str, filename: str) -> tuple[list[str], Path | None]:
    """Return (cli args without binary/url, temp cookie path to delete after run)."""
    is_audio_extract = config.get("audio_extract")
    args = [
        "--newline",
        "--progress",
        "--progress-template", PROGRESS_TEMPLATE,
        "--continue",
        "--ignore-errors",
        "--retries", str(config.get("retries", 3)),
        "--fragment-retries", str(config.get("fragment_retries", 10)),
        "--socket-timeout", str(SOCKET_TIMEOUT),
        "-o", build_output_template(folder, filename),
    ]

    # Format selection
    if is_audio_extract:
        args += ["-f", "bestaudio/best"]
        args += ["-x", "--audio-format", config.get("audio_format", "mp3"),
                 "--audio-quality", str(config.get("audio_quality", 5))]
    else:
        args += ["-f", config.get("format_string", DEFAULT_FORMAT)]
        args += ["--merge-output-format", "mp4"]

    _append_network_args(args, config)
    _append_auth_args(args, config)
    temp_cookie = _append_cookie_args(args, config)
    _append_postprocessing_args(args, config, is_audio_extract)
    _append_external_tool_args(args, config)

    return args, temp_cookie


def _append_network_args(args: list[str], config: dict) -> None:
    proxy = config.get("proxy", "")
    if proxy:
        args += ["--proxy", proxy]

    user_agent = config.get("user_agent", "")
    if user_agent:
        args += ["--user-agent", user_agent]

    referer = config.get("referer", "")
    if referer:
        args += ["--referer", referer]

    custom_headers = config.get("custom_headers", "")
    if custom_headers:
        for line in custom_headers.strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                args += ["--add-header", f"{key.strip()}:{val.strip()}"]

    rate_limit = config.get("rate_limit", 0)
    if rate_limit and rate_limit > 0:
        args += ["--limit-rate", f"{rate_limit}K"]

    sleep_requests = config.get("sleep_requests", 0)
    if sleep_requests and sleep_requests > 0:
        args += ["--sleep-requests", str(sleep_requests)]

    sleep_subtitles = config.get("sleep_subtitles", 0)
    if sleep_subtitles and sleep_subtitles > 0:
        args += ["--sleep-subtitles", str(sleep_subtitles)]


def _append_auth_args(args: list[str], config: dict) -> None:
    if config.get("impersonate_enabled"):
        args += ["--impersonate", config.get("impersonate_browser", "chrome")]


def _append_cookie_args(args: list[str], config: dict) -> Path | None:
    """Append cookie flags; return temp cookie file path if one was created."""
    cookie_mode = config.get("cookie_mode", "none")
    if cookie_mode == "browser":
        args += ["--cookies-from-browser", config.get("cookie_browser", "chrome")]
    elif cookie_mode == "file":
        cookie_file = config.get("cookie_file", "")
        if cookie_file:
            args += ["--cookies", cookie_file]
    elif cookie_mode == "json":
        json_str = config.get("cookie_json", "")
        if json_str:
            tmp_path = save_json_cookies_to_temp(json_str)
            if tmp_path:
                args += ["--cookies", str(tmp_path)]
                return Path(tmp_path)
    return None


def _append_postprocessing_args(args: list[str], config: dict, is_audio_extract: bool) -> None:
    if config.get("embed_thumbnail"):
        args += ["--embed-thumbnail"]

    if config.get("write_metadata"):
        args += ["--write-info-json"]

    subtitle_langs = config.get("subtitle_langs", "")
    if subtitle_langs:
        langs = ",".join(l.strip() for l in subtitle_langs.split(",") if l.strip())
        if langs:
            args += ["--write-subs", "--sub-langs", langs]


def _append_external_tool_args(args: list[str], config: dict) -> None:
    ffmpeg_path = find_ffmpeg(config.get("ffmpeg_path", ""))
    if ffmpeg_path:
        args += ["--ffmpeg-location", str(Path(ffmpeg_path).parent)]

    if config.get("aria2c_enabled"):
        aria2c_path = find_aria2c(config.get("aria2c_path", ""))
        if aria2c_path:
            connections = config.get("aria2c_connections", 16)
            args += [
                "--downloader", aria2c_path,
                "--downloader-args",
                f"aria2c:-x{connections} -s{connections} -k{ARIA2C_CHUNK_SIZE}",
            ]
