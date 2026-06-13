"""Run a user-selected yt-dlp binary as a subprocess download engine.

Selected when config["ytdlp_path"] points to a valid file. Parses the
binary's stdout for progress (machine-readable --progress-template lines,
with fallbacks for plain [download] and aria2c output), supports cancel
by killing the process tree, and reports through the same ui_queue
protocol as the embedded-API Downloader.
"""

import os
import queue
import re
import signal
import subprocess
import sys
import threading
import logging
from pathlib import Path

from ytdlp_gui.core import DownloadStatus
from ytdlp_gui.core.cli_args_builder import build_cli_args, PROGRESS_PREFIX

logger = logging.getLogger(__name__)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# Fallback: "[download]  42.3% of 50.22MiB at 5.32MiB/s ETA 00:05"
_DL_PERCENT_RE = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d+)?)%")
# aria2c console line: "[#gid 5.2MiB/10MiB(52%) CN:16 DL:2.5MiB ETA:6s]"
_ARIA2_PERCENT_RE = re.compile(r"\((\d{1,3})%\)")
_DESTINATION_RE = re.compile(r"\[download\] Destination: (.+)$")
_POSTPROCESS_PREFIXES = ("[Merger]", "[ExtractAudio]", "[EmbedThumbnail]", "[FixupM3u8]")


def resolve_custom_ytdlp(config: dict) -> str | None:
    """Return custom yt-dlp binary path if configured and valid, else None."""
    path = (config.get("ytdlp_path") or "").strip()
    if path and Path(path).is_file():
        return path
    if path:
        logger.warning("Configured yt-dlp path not found, using built-in engine: %s", path)
    return None


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class CliDownloader:
    """Same interface as Downloader, backed by an external yt-dlp binary."""

    def __init__(
        self,
        config: dict,
        cancel_event: threading.Event,
        ui_queue: queue.Queue,
        download_id: str,
        ytdlp_path: str,
    ):
        self._config = config
        self._cancel_event = cancel_event
        self._ui_queue = ui_queue
        self._download_id = download_id
        self._ytdlp_path = ytdlp_path
        self._temp_cookie_path: Path | None = None
        self._seen_temp_files: set[Path] = set()

    def download(self, url: str, folder: str, filename: str) -> None:
        """Run download (blocking). Call from worker thread only."""
        os.makedirs(folder, exist_ok=True)
        logger.info("Starting CLI download %s with %s: %s", self._download_id, self._ytdlp_path, url)

        args, self._temp_cookie_path = build_cli_args(self._config, folder, filename)
        cmd = [self._ytdlp_path, *args, "--", url]

        try:
            proc = self._spawn(cmd)
        except OSError as e:
            logger.error("Failed to launch yt-dlp binary: %s", e)
            self._send_status(DownloadStatus.FAILED.value, f"Cannot run yt-dlp binary: {e}")
            self._cleanup_temp_cookie()
            return

        watcher = threading.Thread(target=self._watch_cancel, args=(proc,), daemon=True)
        watcher.start()

        last_error = ""
        try:
            for raw_line in proc.stdout:
                line = _ANSI_RE.sub("", raw_line).rstrip()
                if not line:
                    continue
                err = self._handle_line(line)
                if err:
                    last_error = err
            returncode = proc.wait()
        finally:
            self._cleanup_temp_cookie()

        if self._cancel_event.is_set():
            logger.info("Download %s cancelled by user", self._download_id)
            self._cleanup_part_files(folder, filename)
            self._send_status(DownloadStatus.CANCELLED.value, "")
        elif returncode == 0:
            logger.info("Download %s completed", self._download_id)
            self._send_progress_done()
            self._send_status(DownloadStatus.COMPLETED.value, "")
        else:
            error = last_error or f"yt-dlp exited with code {returncode}"
            logger.error("Download %s failed: %s", self._download_id, error)
            self._send_status(DownloadStatus.FAILED.value, error)

    # --- Process control ---

    def _spawn(self, cmd: list[str]) -> subprocess.Popen:
        kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            # New session so the whole tree (yt-dlp + aria2c) can be killed
            kwargs["start_new_session"] = True
        return subprocess.Popen(cmd, **kwargs)

    def _watch_cancel(self, proc: subprocess.Popen) -> None:
        """Kill process tree when the user cancels."""
        while proc.poll() is None:
            if self._cancel_event.wait(0.5):
                self._kill_tree(proc)
                return

    def _kill_tree(self, proc: subprocess.Popen) -> None:
        try:
            if sys.platform == "win32":
                # /T kills children too (aria2c spawned by yt-dlp)
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError) as e:
            logger.debug("Kill process tree for %s: %s", self._download_id, e)

    # --- Output parsing ---

    def _handle_line(self, line: str) -> str:
        """Parse one output line; return error text if line is an error."""
        if line.startswith(PROGRESS_PREFIX):
            self._handle_progress_template(line)
            return ""

        if line.startswith("ERROR:"):
            self._send_log("error", line)
            return line[len("ERROR:"):].strip()

        if line.startswith("WARNING:"):
            self._send_log("warning", line)
            return ""

        dest = _DESTINATION_RE.search(line)
        if dest:
            try:
                self._seen_temp_files.add(Path(dest.group(1).strip()))
            except OSError:
                pass
            return ""

        if line.startswith(_POSTPROCESS_PREFIXES):
            self._ui_queue.put({
                "type": "status",
                "id": self._download_id,
                "status": "postprocessing",
                "error": "",
            })
            return ""

        m = _DL_PERCENT_RE.search(line) or _ARIA2_PERCENT_RE.search(line)
        if m:
            percent = min(float(m.group(1)) / 100.0, 1.0)
            self._ui_queue.put({
                "type": "progress",
                "id": self._download_id,
                "percent": percent,
                "speed": 0,
                "eta": 0,
                "filename": "",
            })
        return ""

    def _handle_progress_template(self, line: str) -> None:
        """Parse CKPROG|downloaded|total|estimate|speed|eta|filename."""
        parts = line[len(PROGRESS_PREFIX):].split("|")
        if len(parts) < 6:
            return
        downloaded = _to_float(parts[0]) or 0
        total = _to_float(parts[1]) or _to_float(parts[2])
        speed = _to_float(parts[3]) or 0
        eta = _to_float(parts[4]) or 0
        filename = parts[5]
        if filename:
            try:
                self._seen_temp_files.add(Path(filename))
            except OSError:
                pass

        if total and total > 0:
            self._ui_queue.put({
                "type": "progress",
                "id": self._download_id,
                "percent": min(downloaded / total, 1.0),
                "speed": speed,
                "eta": eta,
                "filename": filename,
            })
        elif downloaded > 0:
            self._ui_queue.put({
                "type": "progress_no_total",
                "id": self._download_id,
                "downloaded_bytes": downloaded,
                "speed": speed,
                "eta": eta,
                "filename": filename,
            })
        else:
            self._ui_queue.put({"type": "indeterminate", "id": self._download_id})

    # --- UI queue helpers ---

    def _send_progress_done(self) -> None:
        self._ui_queue.put({
            "type": "progress",
            "id": self._download_id,
            "percent": 1.0,
            "speed": 0,
            "eta": 0,
            "filename": "",
        })

    def _send_status(self, status: str, error: str) -> None:
        self._ui_queue.put({
            "type": "status",
            "id": self._download_id,
            "status": status,
            "error": error,
        })

    def _send_log(self, level: str, message: str) -> None:
        self._ui_queue.put({
            "type": "log",
            "id": self._download_id,
            "level": level,
            "message": message,
        })

    # --- Cleanup ---

    def _cleanup_temp_cookie(self) -> None:
        if self._temp_cookie_path and self._temp_cookie_path.exists():
            try:
                self._temp_cookie_path.unlink()
            except OSError as e:
                logger.debug("Failed to remove temp cookie: %s", e)

    def _cleanup_part_files(self, folder: str, filename: str) -> None:
        """Delete only this download's temp files left by cancellation."""
        try:
            folder_path = Path(folder)

            for path in self._seen_temp_files:
                candidate = path if path.is_absolute() else (folder_path / path)
                if candidate.parent != folder_path:
                    continue
                for junk in (candidate, candidate.with_name(candidate.name + ".part"),
                             candidate.with_name(candidate.name + ".aria2")):
                    if ".part" in junk.name or junk.suffix in (".ytdl", ".aria2"):
                        logger.debug("Cleaning up tracked temp: %s", junk)
                        junk.unlink(missing_ok=True)

            if filename:
                base_name = Path(filename).stem or filename
                for pattern in (f"{base_name}*.part*", f"{base_name}*.ytdl", f"{base_name}*.aria2"):
                    for junk_file in folder_path.glob(pattern):
                        logger.debug("Cleaning up pattern-matched temp: %s", junk_file)
                        junk_file.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("Error during temp file cleanup: %s", e)
