import logging
import queue
import random
import threading

from ytdlp_gui.core import DownloadItem, DownloadStatus
from ytdlp_gui.core.downloader import Downloader

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages concurrent downloads with a bounded worker pool."""

    def __init__(self, config: dict, ui_queue: queue.Queue):
        self._config = config
        self._ui_queue = ui_queue
        self._job_queue: queue.Queue[DownloadItem | object] = queue.Queue()
        self._active: dict[str, threading.Event] = {}
        self._cancelled_pending: set[str] = set()
        self._lock = threading.Lock()
        self._concurrent_limit = config.get("concurrent_limit", 3)
        self._workers: list[threading.Thread] = []
        self._stop_token = object()
        self._start_workers(self._concurrent_limit)

    def add_items(self, items: list[DownloadItem]) -> None:
        """Queue items for download into the worker pool."""
        for item in items:
            self._job_queue.put(item)

    def _start_workers(self, count: int) -> None:
        for _ in range(max(1, int(count))):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker_loop(self) -> None:
        while True:
            item = self._job_queue.get()
            try:
                if item is self._stop_token:
                    return

                if not isinstance(item, DownloadItem):
                    continue

                cancel_event = threading.Event()
                with self._lock:
                    if item.id in self._cancelled_pending:
                        self._cancelled_pending.remove(item.id)
                        logger.info("Download %s cancelled before start", item.id)
                        self._ui_queue.put({
                            "type": "status",
                            "id": item.id,
                            "status": DownloadStatus.CANCELLED.value,
                            "error": "",
                        })
                        continue
                    self._active[item.id] = cancel_event

                # Inter-download sleep (anti-block)
                sleep_min = self._config.get("sleep_interval", 0)
                sleep_max = self._config.get("sleep_interval_max", 0)
                if sleep_min > 0:
                    if sleep_max > sleep_min:
                        delay = random.uniform(sleep_min, sleep_max)
                    else:
                        delay = sleep_min
                    # Interruptible sleep — returns True if cancelled
                    if cancel_event.wait(delay):
                        logger.info("Download %s cancelled during sleep", item.id)
                        self._ui_queue.put({
                            "type": "status",
                            "id": item.id,
                            "status": DownloadStatus.CANCELLED.value,
                            "error": "",
                        })
                        continue

                self._ui_queue.put({
                    "type": "status",
                    "id": item.id,
                    "status": DownloadStatus.DOWNLOADING.value,
                    "error": "",
                })

                # Use a snapshot copy of config for thread safety
                config_snapshot = dict(self._config)
                downloader = Downloader(config_snapshot, cancel_event, self._ui_queue, item.id)
                downloader.download(item.url, item.folder, item.filename)
            finally:
                if isinstance(item, DownloadItem):
                    with self._lock:
                        self._active.pop(item.id, None)
                self._job_queue.task_done()

    def cancel_item(self, download_id: str) -> None:
        """Signal cancellation for a specific download."""
        with self._lock:
            event = self._active.get(download_id)
            if event:
                event.set()
            else:
                self._cancelled_pending.add(download_id)

    def cancel_all(self) -> None:
        """Signal cancellation for all active downloads."""
        # Cancel active
        with self._lock:
            for event in self._active.values():
                event.set()

        # Drain queued items not yet picked by workers
        while True:
            try:
                item = self._job_queue.get_nowait()
                if isinstance(item, DownloadItem):
                    logger.info("Download %s cancelled (drained from queue)", item.id)
                    self._ui_queue.put({
                        "type": "status",
                        "id": item.id,
                        "status": DownloadStatus.CANCELLED.value,
                        "error": "",
                    })
                self._job_queue.task_done()
            except queue.Empty:
                break

        # Shutdown workers
        for _ in range(len(self._workers)):
            self._job_queue.put(self._stop_token)
        
        # Wait for workers to finish with adequate timeout
        for w in self._workers:
            if w.is_alive():
                w.join(timeout=2.0)
        self._workers.clear()

        # Restart workers so future downloads can proceed
        self._start_workers(self._concurrent_limit)

    def update_config(self, config: dict) -> None:
        """Update config for future downloads."""
        with self._lock:
            self._config = config
            new_limit = config.get("concurrent_limit", 3)
            if new_limit == self._concurrent_limit:
                return
            old_limit = self._concurrent_limit
            self._concurrent_limit = new_limit

        if new_limit > old_limit:
            self._start_workers(new_limit - old_limit)
        elif new_limit < old_limit:
            for _ in range(old_limit - new_limit):
                self._job_queue.put(self._stop_token)
