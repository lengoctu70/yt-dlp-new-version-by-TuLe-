import logging
import queue

import customtkinter as ctk

from ytdlp_gui.core.config_manager import load_config
from ytdlp_gui.core.queue_manager import QueueManager
from ytdlp_gui.ui.main_window import MainWindow

# Constants
UI_POLL_INTERVAL_MS = 100  # Milliseconds between UI queue polls


def main():
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    ctk.set_default_color_theme("dark-blue")
    ctk.set_appearance_mode(config.get("theme", "dark"))

    app = ctk.CTk()
    app.title("yt-dlp Downloader")
    app.geometry("900x700")
    app.minsize(900, 700)

    ui_queue = queue.Queue()
    queue_manager = QueueManager(config, ui_queue)

    main_window = MainWindow(app, config, ui_queue, queue_manager)
    main_window.pack(fill="both", expand=True)

    # Poll worker thread messages -> update UI on main thread
    def poll_queue():
        try:
            while True:
                msg = ui_queue.get_nowait()
                main_window.handle_queue_message(msg)
        except queue.Empty:
            pass
        app.after(UI_POLL_INTERVAL_MS, poll_queue)

    app.after(UI_POLL_INTERVAL_MS, poll_queue)

    # Graceful shutdown
    def on_closing():
        queue_manager.cancel_all()
        main_window.flush_config_from_ui()
        # Brief wait for workers to finish cleanup before destroying UI
        app.after(300, app.destroy)

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
