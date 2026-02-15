from typing import Callable

import customtkinter as ctk

from ytdlp_gui.core import DownloadItem, DownloadStatus


def format_speed(speed_bps: float) -> str:
    if speed_bps >= 1_048_576:
        return f"{speed_bps / 1_048_576:.1f} MB/s"
    elif speed_bps >= 1024:
        return f"{speed_bps / 1024:.1f} KB/s"
    return f"{speed_bps:.0f} B/s"


def format_eta(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_size(size_bytes: float) -> str:
    """Format bytes into human-readable size string."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes:.0f} B"


class DownloadRow(ctk.CTkFrame):
    """Single download item row with progress bar, speed, ETA, cancel."""

    def __init__(self, master, item: DownloadItem, on_cancel: Callable, **kwargs):
        super().__init__(master, corner_radius=6, **kwargs)
        self._item = item
        self._on_cancel = on_cancel
        self._current_status = "pending"
        self._is_indeterminate = False
        self._error_msg = ""

        # Top row: filename + cancel
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(8, 4))

        self._filename_label = ctk.CTkLabel(
            top,
            text=item.filename or item.url[:60],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self._filename_label.pack(side="left", fill="x", expand=True)

        self._cancel_btn = ctk.CTkButton(
            top,
            text="Cancel",
            command=lambda: self._on_cancel(item.id),
            width=60,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            hover_color=("#c62828", "#ef5350"),
        )
        self._cancel_btn.pack(side="right")

        # Middle row: progress bar + stats
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="x", padx=12, pady=(0, 4))

        self._progress_bar = ctk.CTkProgressBar(mid, height=8)
        self._progress_bar.set(0)
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._percent_label = ctk.CTkLabel(
            mid, text="0%", font=ctk.CTkFont(size=11), width=40
        )
        self._percent_label.pack(side="left", padx=(0, 8))

        self._speed_label = ctk.CTkLabel(
            mid, text="", font=ctk.CTkFont(size=11), width=80, text_color=("gray50", "gray60")
        )
        self._speed_label.pack(side="left", padx=(0, 8))

        self._eta_label = ctk.CTkLabel(
            mid, text="", font=ctk.CTkFont(size=11), width=60, text_color=("gray50", "gray60")
        )
        self._eta_label.pack(side="left")

        # Bottom row: status
        self._status_label = ctk.CTkLabel(
            self,
            text="Waiting...",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=12, pady=(0, 8))

    def update_progress(self, percent: float, speed: float, eta: int):
        # Switch back to determinate mode if needed
        if getattr(self, "_is_indeterminate", False):
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate")
            self._is_indeterminate = False
        self._progress_bar.set(percent)
        self._percent_label.configure(text=f"{int(percent * 100)}%")
        self._speed_label.configure(text=format_speed(speed) if speed else "")
        self._eta_label.configure(text=f"ETA: {format_eta(eta)}" if eta else "")
        self._status_label.configure(text="Downloading...", text_color=("gray50", "gray60"))

    def set_status(self, status: str, error_msg: str = ""):
        self._current_status = status
        self._error_msg = error_msg
        terminal_statuses = (
            DownloadStatus.COMPLETED.value,
            DownloadStatus.FAILED.value,
            DownloadStatus.CANCELLED.value,
        )
        if status in terminal_statuses and self._is_indeterminate:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate")
            self._is_indeterminate = False
        status_map = {
            DownloadStatus.DOWNLOADING.value: ("Downloading...", ("gray50", "gray60")),
            "postprocessing": ("Post-processing...", ("gray50", "gray60")),
            DownloadStatus.COMPLETED.value: ("Done", ("#2e7d32", "#4caf50")),
            DownloadStatus.FAILED.value: (f"Failed: {error_msg}" if error_msg else "Failed", ("#c62828", "#ef5350")),
            DownloadStatus.CANCELLED.value: ("Cancelled", ("gray50", "gray60")),
        }
        text, color = status_map.get(status, (status, ("gray50", "gray60")))
        self._status_label.configure(text=text, text_color=color)

        if status == DownloadStatus.COMPLETED.value:
            self._cancel_btn.pack_forget()
            self._progress_bar.set(1.0)
            self._percent_label.configure(text="100%")
            self._progress_bar.configure(progress_color=("#2e7d32", "#4caf50"))
        elif status in (DownloadStatus.FAILED.value, DownloadStatus.CANCELLED.value):
            self._cancel_btn.pack_forget()

    def set_indeterminate(self):
        self._progress_bar.configure(mode="indeterminate")
        self._progress_bar.start()
        self._is_indeterminate = True
        self._status_label.configure(text="Downloading...")

    def update_progress_no_total(self, downloaded_bytes: float, speed: float, eta: int):
        """Update UI when total size is unknown but downloaded bytes are available."""
        # Switch to indeterminate mode if not already
        if not getattr(self, "_is_indeterminate", False):
            self._progress_bar.configure(mode="indeterminate")
            self._progress_bar.start()
            self._is_indeterminate = True
        self._percent_label.configure(text="--")
        self._status_label.configure(
            text=f"Downloading: {format_size(downloaded_bytes)}",
            text_color=("gray50", "gray60"),
        )
        self._speed_label.configure(text=format_speed(speed) if speed else "")
        self._eta_label.configure(text=f"ETA: {format_eta(eta)}" if eta else "")

    def update_filename(self, filename: str):
        if filename:
            display = filename.split("/")[-1].split("\\")[-1]
            if len(display) > 60:
                display = display[:57] + "..."
            self._filename_label.configure(text=display)


class QueueFrame(ctk.CTkScrollableFrame):
    """Download queue displaying DownloadRows."""

    def __init__(self, master, on_cancel_item: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self._on_cancel_item = on_cancel_item
        self._rows: dict[str, DownloadRow] = {}

        self._empty_label = ctk.CTkLabel(
            self,
            text="No downloads queued",
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=13),
        )
        self._empty_label.pack(pady=20)

    def add_item(self, item: DownloadItem):
        self._empty_label.pack_forget()
        row = DownloadRow(self, item, self._on_cancel_item)
        row.pack(fill="x", pady=(0, 8))
        self._rows[item.id] = row

    def update_progress(self, download_id: str, percent: float, speed: float, eta: int):
        row = self._rows.get(download_id)
        if row:
            row.update_progress(percent, speed, eta)

    def update_status(self, download_id: str, status: str, error_msg: str = ""):
        row = self._rows.get(download_id)
        if row:
            row.set_status(status, error_msg)

    def set_indeterminate(self, download_id: str):
        row = self._rows.get(download_id)
        if row:
            row.set_indeterminate()

    def update_progress_no_total(self, download_id: str, downloaded_bytes: float, speed: float, eta: int):
        row = self._rows.get(download_id)
        if row:
            row.update_progress_no_total(downloaded_bytes, speed, eta)

    def update_filename(self, download_id: str, filename: str):
        row = self._rows.get(download_id)
        if row:
            row.update_filename(filename)

    def clear(self):
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        self._empty_label.pack(pady=20)

    def clear_completed(self):
        """Remove rows with 'completed' status from the queue."""
        to_remove = [
            did for did, row in self._rows.items()
            if getattr(row, "_current_status", "") == DownloadStatus.COMPLETED.value
        ]
        for did in to_remove:
            self._rows[did].destroy()
            del self._rows[did]
        if not self._rows:
            self._empty_label.pack(pady=20)

    def get_failed_items(self) -> list:
        """Return DownloadItems for rows with 'failed' status."""
        failed = []
        for row in self._rows.values():
            if getattr(row, "_current_status", "") == DownloadStatus.FAILED.value:
                failed.append(row._item)
        return failed

    def get_completed_items(self) -> list:
        """Return DownloadItems for rows with 'completed' status."""
        completed = []
        for row in self._rows.values():
            if getattr(row, "_current_status", "") == DownloadStatus.COMPLETED.value:
                completed.append(row._item)
        return completed

    def remove_failed(self) -> None:
        """Remove failed rows after loading them back into input."""
        failed_ids = [
            did for did, row in self._rows.items()
            if getattr(row, "_current_status", "") == DownloadStatus.FAILED.value
        ]
        for did in failed_ids:
            self._rows[did].destroy()
            del self._rows[did]
        if not self._rows:
            self._empty_label.pack(pady=20)
