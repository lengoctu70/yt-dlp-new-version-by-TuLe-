import logging
import queue

import customtkinter as ctk

from ytdlp_gui.core.config_manager import save_config
from ytdlp_gui.core.queue_manager import QueueManager
from ytdlp_gui.ui.url_input_frame import URLInputFrame
from ytdlp_gui.ui.queue_frame import QueueFrame
from ytdlp_gui.ui.settings_panel import SettingsPanel


class MainWindow(ctk.CTkFrame):
    """Main application window composing all UI sections."""

    def __init__(self, master, config: dict, ui_queue: queue.Queue, queue_manager: QueueManager):
        super().__init__(master, fg_color="transparent")
        self._config = config
        self._ui_queue = ui_queue
        self._queue_manager = queue_manager

        # References
        self._save_timer_id = None

        # Scrollable container
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=24, pady=24)

        self._build_header()
        self._build_url_input()
        self._build_action_buttons()
        self._build_queue()
        self._build_settings()

    def _build_header(self):
        header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header,
            text="yt-dlp Downloader",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")

        self._theme_btn = ctk.CTkButton(
            header,
            text="Light" if ctk.get_appearance_mode() == "Dark" else "Dark",
            command=self._toggle_theme,
            width=70,
            height=28,
            font=ctk.CTkFont(size=13),
        )
        self._theme_btn.pack(side="right")

    def _build_action_buttons(self):
        btn_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner.pack(anchor="center")

        ctk.CTkButton(
            inner, text="Download All", command=self._on_download_all, width=140
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            inner,
            text="Validate",
            command=self._on_validate,
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            inner,
            text="Clear Completed",
            command=self._on_clear_completed,
            width=130,
            fg_color="transparent",
            border_width=1,
            text_color=("#2e7d32", "#4caf50"),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            inner,
            text="Load Failed",
            command=self._on_load_failed,
            width=110,
            fg_color="transparent",
            border_width=1,
            text_color=("#c62828", "#ef5350"),
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            inner,
            text="Clear",
            command=self._on_clear,
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        ).pack(side="left")

    def _build_url_input(self):
        self._url_input = URLInputFrame(self._scroll, self._config)
        self._url_input.pack(fill="x", pady=(0, 16))

    def _build_queue(self):
        self._queue_frame = QueueFrame(
            self._scroll, self._on_cancel_item, height=200
        )
        self._queue_frame.pack(fill="x", pady=(0, 16))

    def _build_settings(self):
        self._settings_panel = SettingsPanel(
            self._scroll, self._config, self._schedule_config_save
        )
        self._settings_panel.pack(fill="x")

    def _schedule_config_save(self):
        """Debounced config save (500ms)."""
        if self._save_timer_id:
            self.after_cancel(self._save_timer_id)
        self._save_timer_id = self.after(500, self._save_config_now)

    def _save_config_now(self):
        self._config.update(self._settings_panel.get_values())
        save_config(self._config)
        self._save_timer_id = None

    def flush_config_from_ui(self):
        """Force-read settings widgets into config and save immediately."""
        if self._save_timer_id:
            self.after_cancel(self._save_timer_id)
        if self._settings_panel:
            self._config.update(self._settings_panel.get_values())
        save_config(self._config)
        self._save_timer_id = None

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="Light" if new_mode == "Dark" else "Dark")
        self._config["theme"] = new_mode.lower()
        save_config(self._config)

    def _on_download_all(self):
        """Validate + queue all items for download."""
        if not self._url_input:
            return
        result = self._url_input.validate_detailed()
        errors = result["errors"]
        warnings = result["warnings"]
        if errors:
            if warnings:
                self._url_input.show_validation_error("\n".join(errors + [""] + warnings))
            else:
                self._url_input.show_validation_error("\n".join(errors))
            return
        if warnings:
            self._url_input.show_validation_error("\n".join(warnings))
        else:
            self._url_input.show_validation_error("")

        items = self._url_input.get_items()
        if not items:
            return

        # Update config from settings if available
        if self._settings_panel:
            self._config.update(self._settings_panel.get_values())
            save_config(self._config)

        for item in items:
            self._queue_frame.add_item(item)

        self._queue_manager.update_config(self._config)
        self._queue_manager.add_items(items)

    def _on_validate(self):
        if not self._url_input:
            return
        result = self._url_input.validate_detailed()
        errors = result["errors"]
        warnings = result["warnings"]
        if errors:
            if warnings:
                self._url_input.show_validation_error("\n".join(errors + [""] + warnings))
            else:
                self._url_input.show_validation_error("\n".join(errors))
        elif warnings:
            self._url_input.show_validation_error("\n".join(warnings))
        else:
            self._url_input.show_validation_error("")

    def _on_clear(self):
        self._queue_manager.cancel_all()
        if self._url_input:
            self._url_input.clear()
        if self._queue_frame:
            self._queue_frame.clear()

    def _on_cancel_item(self, download_id: str):
        self._queue_manager.cancel_item(download_id)

    def _on_clear_completed(self):
        """Remove completed downloads from queue AND input fields."""
        if self._queue_frame:
            # 1. Get completed items before clearing
            completed_items = self._queue_frame.get_completed_items()
            
            # 2. Clear from Queue
            self._queue_frame.clear_completed()
            
            # 3. Clear from Input Frame (sync)
            if self._url_input and completed_items:
                self._url_input.remove_items(completed_items)

    def _on_load_failed(self):
        """Load failed items back into the URL input for editing and retry."""
        if not self._queue_frame or not self._url_input:
            return
        failed_items = self._queue_frame.get_failed_items()
        if not failed_items:
            return
        self._url_input.load_items(failed_items)
        self._queue_frame.remove_failed()

    def handle_queue_message(self, msg: dict):
        """Route queue messages to QueueFrame (called from main thread)."""
        if not self._queue_frame:
            return

        msg_type = msg.get("type")
        did = msg.get("id")

        if msg_type == "progress":
            self._queue_frame.update_progress(
                did, msg.get("percent", 0), msg.get("speed", 0), msg.get("eta", 0)
            )
            # Update filename if provided
            filename = msg.get("filename", "")
            if filename:
                self._queue_frame.update_filename(did, filename)
        elif msg_type == "progress_no_total":
            self._queue_frame.update_progress_no_total(
                did, msg.get("downloaded_bytes", 0), msg.get("speed", 0), msg.get("eta", 0)
            )
            filename = msg.get("filename", "")
            if filename:
                self._queue_frame.update_filename(did, filename)
        elif msg_type == "status":
            self._queue_frame.update_status(did, msg.get("status", ""), msg.get("error", ""))
        elif msg_type == "indeterminate":
            self._queue_frame.set_indeterminate(did)
        elif msg_type == "log":
            level = msg.get("level", "info")
            message = msg.get("message", "")
            log_level = getattr(logging, level.upper(), logging.INFO)
            logging.getLogger("ytdlp_gui.downloader").log(
                log_level, "[%s] %s", did, message
            )
