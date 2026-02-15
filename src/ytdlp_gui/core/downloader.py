import os
import queue
import threading
import logging
from pathlib import Path

import yt_dlp

from ytdlp_gui.core import DownloadStatus
from ytdlp_gui.utils.tool_checker import find_ffmpeg, find_aria2c
from ytdlp_gui.utils.cookie_converter import save_json_cookies_to_temp
from ytdlp_gui.utils.sanitize import sanitize_filename

logger = logging.getLogger(__name__)

# Constants
SOCKET_TIMEOUT = 30
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
ARIA2C_CHUNK_SIZE = "1M"


class DownloadCancelled(Exception):
    pass


class GuiLogger:
    """Redirects yt-dlp logs to the UI queue."""

    def __init__(self, ui_queue: queue.Queue, download_id: str):
        self._ui_queue = ui_queue
        self._download_id = download_id

    def debug(self, msg):
        if msg.startswith("[debug] "):
            pass
        else:
            self.info(msg)

    def info(self, msg):
        pass

    def warning(self, msg):
        self._ui_queue.put({
            "type": "log",
            "id": self._download_id,
            "level": "warning",
            "message": msg
        })

    def error(self, msg):
        self._ui_queue.put({
            "type": "log",
            "id": self._download_id,
            "level": "error",
            "message": msg
        })


class Downloader:
    """Wraps yt-dlp Python API with progress hooks and cancel support."""

    def __init__(
        self,
        config: dict,
        cancel_event: threading.Event,
        ui_queue: queue.Queue,
        download_id: str,
    ):
        self._config = config
        self._cancel_event = cancel_event
        self._ui_queue = ui_queue
        self._download_id = download_id
        self._seen_temp_files: set[Path] = set()
        self._temp_cookie_path: Path | None = None

    def build_opts(self, folder: str, filename: str) -> dict:
        """Build yt-dlp options dict from config."""
        
        # Base options — override format when audio extraction is enabled
        is_audio_extract = self._config.get("audio_extract")
        opts = {
            "format": (
                "bestaudio/best"
                if is_audio_extract
                else self._config.get("format_string", DEFAULT_FORMAT)
            ),
            "merge_output_format": None if is_audio_extract else "mp4",
            "continuedl": True,
            "ignoreerrors": True,
            "retries": self._config.get("retries", 3),
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "logger": GuiLogger(self._ui_queue, self._download_id),
            "noprogress": True,
            "quiet": True,  # handled by GuiLogger
            "socket_timeout": SOCKET_TIMEOUT,
            "fragment_retries": self._config.get("fragment_retries", 10),
        }

        # Sub-configurations
        self._configure_output(opts, folder, filename)
        self._configure_network(opts)
        self._configure_auth(opts)
        self._configure_postprocessing(opts)
        self._configure_external_tools(opts)

        return opts

    def _configure_output(self, opts: dict, folder: str, filename: str):
        if filename:
            safe_name = sanitize_filename(filename)
            if not safe_name or safe_name == "download":
                safe_name = "%(title)s"
            outtmpl = str(Path(folder) / safe_name)
            if not Path(safe_name).suffix:
                outtmpl += ".%(ext)s"
        else:
            outtmpl = str(Path(folder) / "%(title)s.%(ext)s")
        opts["outtmpl"] = outtmpl

        # Metadata & Subtitles
        if self._config.get("write_metadata"):
            opts["writeinfojson"] = True
        
        subtitle_langs = self._config.get("subtitle_langs", "")
        if subtitle_langs:
            opts["subtitleslangs"] = [l.strip() for l in subtitle_langs.split(",") if l.strip()]
            opts["writesubtitles"] = True

    def _configure_network(self, opts: dict):
        # Proxy
        proxy = self._config.get("proxy", "")
        if proxy:
            opts["proxy"] = proxy

        # HTTP Headers
        http_headers = {}
        user_agent = self._config.get("user_agent", "")
        if user_agent:
            http_headers["User-Agent"] = user_agent
        referer = self._config.get("referer", "")
        if referer:
            http_headers["Referer"] = referer
        
        custom_headers = self._config.get("custom_headers", "")
        if custom_headers:
            for line in custom_headers.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    http_headers[key.strip()] = val.strip()
        
        if http_headers:
            opts["http_headers"] = http_headers

        # Rate Limit
        rate_limit = self._config.get("rate_limit", 0)
        if rate_limit and rate_limit > 0:
            opts["ratelimit"] = rate_limit * 1024
            
        # Throttling / Anti-block
        sleep_requests = self._config.get("sleep_requests", 0)
        if sleep_requests and sleep_requests > 0:
            opts["sleep_interval_requests"] = sleep_requests

        sleep_subtitles = self._config.get("sleep_subtitles", 0)
        if sleep_subtitles and sleep_subtitles > 0:
            opts["sleep_interval_subtitles"] = sleep_subtitles

    def _configure_auth(self, opts: dict):
        # Cookies
        cookie_mode = self._config.get("cookie_mode", "none")
        if cookie_mode == "browser":
            browser = self._config.get("cookie_browser", "chrome")
            opts["cookiesfrombrowser"] = (browser, None, None, None)
        elif cookie_mode == "file":
            cookie_file = self._config.get("cookie_file", "")
            if cookie_file:
                opts["cookiefile"] = cookie_file
        elif cookie_mode == "json":
            json_str = self._config.get("cookie_json", "")
            if json_str:
                tmp_path = save_json_cookies_to_temp(json_str)
                if tmp_path:
                    opts["cookiefile"] = tmp_path
                    self._temp_cookie_path = Path(tmp_path)

        # Impersonate
        if self._config.get("impersonate_enabled"):
            opts["impersonate"] = self._config.get("impersonate_browser", "chrome")

    def _configure_postprocessing(self, opts: dict):
        postprocessors = []

        if self._config.get("audio_extract"):
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": self._config.get("audio_format", "mp3"),
                "preferredquality": str(self._config.get("audio_quality", 5)),
            })

        if self._config.get("embed_thumbnail"):
            opts["writethumbnail"] = True
            postprocessors.append({"key": "EmbedThumbnail"})

        if postprocessors:
            opts["postprocessors"] = postprocessors

    def _configure_external_tools(self, opts: dict):
        # FFmpeg
        ffmpeg_path = find_ffmpeg(self._config.get("ffmpeg_path", ""))
        if ffmpeg_path:
            opts["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
            # Prefer ffmpeg for HLS to avoid native downloader warnings
            opts["hls_prefer_native"] = False

        # Aria2c
        if self._config.get("aria2c_enabled"):
            aria2c_path = find_aria2c(self._config.get("aria2c_path", ""))
            if aria2c_path:
                connections = self._config.get("aria2c_connections", 16)
                opts["external_downloader"] = {"default": aria2c_path}
                opts["external_downloader_args"] = {
                    "default": [f"-x{connections}", f"-s{connections}", f"-k{ARIA2C_CHUNK_SIZE}"]
                }

    def _progress_hook(self, d: dict) -> None:
        """Called by yt-dlp with download progress."""
        self._track_temp_paths(d)

        if self._cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user")

        status = d.get("status")
        did = self._download_id

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            filename = d.get("filename", "")

            if total and total > 0:
                percent = downloaded / total
                self._ui_queue.put({
                    "type": "progress",
                    "id": did,
                    "percent": min(percent, 1.0),
                    "speed": speed,
                    "eta": eta,
                    "filename": filename,
                })
            else:
                # Try to parse percent from yt-dlp's own _percent_str
                percent_str = d.get("_percent_str", "").strip()
                parsed_percent = None
                if percent_str:
                    try:
                        parsed_percent = float(percent_str.replace("%", "")) / 100.0
                    except (ValueError, TypeError):
                        pass

                if parsed_percent is not None:
                    self._ui_queue.put({
                        "type": "progress",
                        "id": did,
                        "percent": min(max(parsed_percent, 0.0), 1.0),
                        "speed": speed,
                        "eta": eta,
                        "filename": filename,
                    })
                elif downloaded > 0:
                    self._ui_queue.put({
                        "type": "progress_no_total",
                        "id": did,
                        "downloaded_bytes": downloaded,
                        "speed": speed,
                        "eta": eta,
                        "filename": filename,
                    })
                else:
                    self._ui_queue.put({"type": "indeterminate", "id": did})
            
            # Send completion signal if we hit 100% logic, 
            # but yt-dlp usually sends 'finished' status next.

        elif status == "finished":
            # Just to be sure we show 100%
            self._ui_queue.put({
                "type": "progress",
                "id": did,
                "percent": 1.0,
                "speed": 0,
                "eta": 0,
                "filename": d.get("filename", ""),
            })

        elif status == "error":
            error_msg = d.get("error", "Unknown error")
            logger.error("Download %s error: %s", did, error_msg)
            self._ui_queue.put({
                "type": "status",
                "id": did,
                "status": DownloadStatus.FAILED.value,
                "error": str(error_msg),
            })

    def _track_temp_paths(self, data: dict) -> None:
        """Collect file paths reported by yt-dlp so cancel cleanup is scoped."""
        for key in ("tmpfilename", "filename"):
            raw_path = data.get(key)
            if not raw_path or not isinstance(raw_path, str):
                continue
            try:
                self._seen_temp_files.add(Path(raw_path))
            except OSError as e:
                logger.debug("Could not track temp path %s: %s", raw_path, e)
                continue

    def _postprocessor_hook(self, d: dict) -> None:
        """Called by yt-dlp during post-processing."""
        if self._cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user")

        status = d.get("status")
        if status == "started":
            pp_name = d.get("postprocessor", "unknown")
            logger.debug("Post-processing started (%s) for %s", pp_name, self._download_id)
            self._ui_queue.put({
                "type": "status",
                "id": self._download_id,
                "status": "postprocessing",
                "error": "",
            })
        elif status == "finished":
            pp_name = d.get("postprocessor", "unknown")
            logger.debug("Post-processing finished (%s) for %s", pp_name, self._download_id)
        elif status == "error":
            pp_name = d.get("postprocessor", "unknown")
            error_msg = d.get("error", "Post-processing error")
            logger.error("Post-processing error (%s) for %s: %s", pp_name, self._download_id, error_msg)

    def download(self, url: str, folder: str, filename: str) -> None:
        """Run download (blocking). Call from worker thread only."""
        os.makedirs(folder, exist_ok=True)
        logger.info("Starting download %s: %s", self._download_id, url)

        opts = self.build_opts(folder, filename)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            if not self._cancel_event.is_set():
                logger.info("Download %s completed", self._download_id)
                self._ui_queue.put({
                    "type": "status",
                    "id": self._download_id,
                    "status": DownloadStatus.COMPLETED.value,
                    "error": "",
                })

        except DownloadCancelled:
            logger.info("Download %s cancelled by user", self._download_id)
            self._cleanup_part_files(folder, filename)
            self._ui_queue.put({
                "type": "status",
                "id": self._download_id,
                "status": DownloadStatus.CANCELLED.value,
                "error": "",
            })

        except Exception as e:
            if self._cancel_event.is_set():
                logger.info("Download %s cancelled (via exception)", self._download_id)
                self._cleanup_part_files(folder, filename)
                self._ui_queue.put({
                    "type": "status",
                    "id": self._download_id,
                    "status": DownloadStatus.CANCELLED.value,
                    "error": "",
                })
            else:
                logger.error("Download %s failed: %s", self._download_id, e)
                self._ui_queue.put({
                    "type": "status",
                    "id": self._download_id,
                    "status": DownloadStatus.FAILED.value,
                    "error": str(e),
                })
        finally:
            if self._temp_cookie_path and self._temp_cookie_path.exists():
                try:
                    self._temp_cookie_path.unlink()
                except OSError as e:
                    logger.debug("Failed to remove temp cookie: %s", e)

    def _cleanup_part_files(self, folder: str, filename: str) -> None:
        """Delete only this download's temp files left by cancellation.

        Only removes files tracked by yt-dlp hooks (self._seen_temp_files)
        and, as a fallback, files matching the specific filename pattern.
        Never performs a broad recursive glob to avoid deleting files
        belonging to other concurrent downloads.
        """
        try:
            folder_path = Path(folder)

            # 1. Remove tracked temp files (scoped to this download)
            for path in self._seen_temp_files:
                candidate = path if path.is_absolute() else (folder_path / path)
                if candidate.parent != folder_path:
                    continue
                if ".part" in candidate.name or candidate.suffix == ".ytdl":
                    logger.debug("Cleaning up tracked temp: %s", candidate)
                    candidate.unlink(missing_ok=True)

            # 2. Fallback: remove files matching this download's filename
            if filename:
                base_name = Path(filename).stem or filename
                for pattern in (f"{base_name}*.part*", f"{base_name}*.ytdl"):
                    for junk_file in folder_path.glob(pattern):
                        logger.debug("Cleaning up pattern-matched temp: %s", junk_file)
                        junk_file.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("Error during temp file cleanup: %s", e)
