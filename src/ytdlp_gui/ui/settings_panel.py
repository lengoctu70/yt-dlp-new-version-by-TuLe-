import logging
import re
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

logger = logging.getLogger(__name__)

from ytdlp_gui.ui.collapsible_section import CollapsibleSection
from ytdlp_gui.utils.tool_checker import find_ffmpeg, find_aria2c

QUALITY_PRESETS = {
    "Best MP4": "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]",
    "Audio Only": "bestaudio/best",
}

COOKIE_BROWSERS = ["chrome", "firefox", "edge", "safari", "brave", "vivaldi", "opera"]
IMPERSONATE_BROWSERS = ["chrome", "firefox", "edge", "safari"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac"]

# Proxy URL validation pattern
_PROXY_RE = re.compile(
    r'^(https?|socks[45]h?)://'
    r'([^:@]+:[^:@]+@)?'  # optional user:pass@
    r'[\w.-]+'
    r'(:\d{1,5})?'
    r'/?$'
)

# Validation limits
MAX_RETRIES = 100
MAX_CONNECTIONS = 16
MAX_CONCURRENT = 10
MAX_RATE_LIMIT_KB = 1_000_000  # 1 GB/s


class SettingsPanel(ctk.CTkFrame):
    """5 collapsible settings sections reading/writing to config dict."""

    def __init__(self, master, config: dict, on_config_change: Callable, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._config = config
        self._on_config_change = on_config_change
        self._suppress_callbacks = False

        self._build_tools_section()
        self._build_cookies_section()
        self._build_antibot_section()
        self._build_advanced_section()
        self._build_audio_section()

        # Populate widgets from config
        self._suppress_callbacks = True
        self.set_values(config)
        self._suppress_callbacks = False

        # Bind FocusOut on all entries/textboxes so config saves on edit
        self._bind_entry_focusout()

    def _bind_entry_focusout(self):
        """Bind <FocusOut> on all entry/textbox widgets to trigger config save."""
        entries = [
            self._ffmpeg_entry, self._aria2c_entry,
            self._cookie_file_entry,
            self._proxy_entry, self._ua_entry, self._referer_entry,
            self._format_entry, self._rate_entry, self._retries_entry,
            self._sleep_min_entry, self._sleep_max_entry,
            self._sleep_req_entry, self._frag_retries_entry,
            self._sleep_sub_entry, self._subtitle_entry,
        ]
        for entry in entries:
            entry.bind("<FocusOut>", lambda e: self._on_change())

        textboxes = [self._headers_textbox, self._cookie_json_textbox]
        for tb in textboxes:
            tb.bind("<FocusOut>", lambda e: self._on_change())

    # --- Tools Section (S-04a) ---

    def _build_tools_section(self):
        section = CollapsibleSection(self, "Tools")
        section.pack(fill="x", pady=(0, 8))
        cf = section.content_frame

        # FFmpeg row
        ctk.CTkLabel(cf, text="FFmpeg Path", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 4))
        ffmpeg_row = ctk.CTkFrame(cf, fg_color="transparent")
        ffmpeg_row.pack(fill="x", pady=(0, 4))

        self._ffmpeg_entry = ctk.CTkEntry(ffmpeg_row, placeholder_text="Auto-detected")
        self._ffmpeg_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            ffmpeg_row, text="Browse", width=70, command=self._browse_ffmpeg
        ).pack(side="left", padx=(0, 8))

        self._ffmpeg_status = ctk.CTkLabel(ffmpeg_row, text="", font=ctk.CTkFont(size=11), width=80)
        self._ffmpeg_status.pack(side="left")

        # Aria2c row
        ctk.CTkLabel(cf, text="Aria2c Path", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(8, 4))
        aria2c_row = ctk.CTkFrame(cf, fg_color="transparent")
        aria2c_row.pack(fill="x", pady=(0, 4))

        self._aria2c_entry = ctk.CTkEntry(aria2c_row, placeholder_text="Auto-detected")
        self._aria2c_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            aria2c_row, text="Browse", width=70, command=self._browse_aria2c
        ).pack(side="left", padx=(0, 8))

        self._aria2c_status = ctk.CTkLabel(aria2c_row, text="", font=ctk.CTkFont(size=11), width=80)
        self._aria2c_status.pack(side="left")

        # Aria2c enable switch
        self._aria2c_switch = ctk.CTkSwitch(
            cf, text="Enable aria2c as external downloader", command=self._on_aria2c_toggle
        )
        self._aria2c_switch.pack(anchor="w", pady=(4, 4))

        # Aria2c connections (hidden by default)
        self._aria2c_conn_frame = ctk.CTkFrame(cf, fg_color="transparent")
        conn_label = ctk.CTkLabel(self._aria2c_conn_frame, text="Connections:", font=ctk.CTkFont(size=12))
        conn_label.pack(side="left", padx=(0, 8))

        self._aria2c_conn_slider = ctk.CTkSlider(
            self._aria2c_conn_frame, from_=1, to=16, number_of_steps=15, command=self._on_conn_change
        )
        self._aria2c_conn_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._aria2c_conn_label = ctk.CTkLabel(
            self._aria2c_conn_frame, text="16", font=ctk.CTkFont(size=12), width=30
        )
        self._aria2c_conn_label.pack(side="left")

        self._update_tool_status()

    # --- Cookies Section (S-04b) ---

    def _build_cookies_section(self):
        section = CollapsibleSection(self, "Cookie Settings")
        section.pack(fill="x", pady=(0, 8))
        cf = section.content_frame

        self._cookie_mode_var = ctk.StringVar(value="None")
        self._cookie_seg = ctk.CTkSegmentedButton(
            cf, values=["None", "Browser", "File", "JSON"],
            variable=self._cookie_mode_var,
            command=self._on_cookie_mode_change,
        )
        self._cookie_seg.pack(fill="x", pady=(0, 8))

        # Browser sub-section
        self._cookie_browser_frame = ctk.CTkFrame(cf, fg_color="transparent")
        ctk.CTkLabel(self._cookie_browser_frame, text="Browser:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._cookie_browser_menu = ctk.CTkOptionMenu(
            self._cookie_browser_frame, values=COOKIE_BROWSERS, command=lambda _: self._on_change()
        )
        self._cookie_browser_menu.pack(side="left")

        # Browser DPAPI warning
        self._cookie_browser_warning = ctk.CTkFrame(cf, fg_color="transparent")
        ctk.CTkLabel(
            self._cookie_browser_warning,
            text="⚠️ Browser cookie extraction may fail with DPAPI error.",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#e65100", "#ffb74d"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self._cookie_browser_warning,
            text='Recommended: Use "File" mode with exported cookies.txt instead.',
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(fill="x")

        # File sub-section
        self._cookie_file_frame = ctk.CTkFrame(cf, fg_color="transparent")
        self._cookie_file_entry = ctk.CTkEntry(
            self._cookie_file_frame, placeholder_text="cookies.txt path"
        )
        self._cookie_file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            self._cookie_file_frame, text="Browse", width=70, command=self._browse_cookie_file
        ).pack(side="left")

        # File mode help text
        self._cookie_file_help = ctk.CTkFrame(cf, fg_color="transparent")
        ctk.CTkLabel(
            self._cookie_file_help,
            text="How to get cookies.txt:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray30", "gray80"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self._cookie_file_help,
            text='1. Install Chrome extension "Get cookies.txt locally"',
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self._cookie_file_help,
            text="   chrome.google.com → search 'Get cookies.txt locally'",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self._cookie_file_help,
            text="2. Go to the video site → click extension → Export",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            self._cookie_file_help,
            text='3. Save the .txt file → Browse to it above',
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(fill="x")

        # JSON sub-section
        self._cookie_json_frame = ctk.CTkFrame(cf, fg_color="transparent")
        ctk.CTkLabel(
            self._cookie_json_frame,
            text="Paste JSON cookies (from EditThisCookie / Cookie-Editor):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray30", "gray80"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))
        self._cookie_json_textbox = ctk.CTkTextbox(self._cookie_json_frame, height=120, wrap="word")
        self._cookie_json_textbox.pack(fill="x")
        ctk.CTkLabel(
            self._cookie_json_frame,
            text='Format: [{"domain":".site.com","name":"...","value":"..."},...] or {"cookies":[...]}',
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

    # --- Anti-Bot Section (S-04c) ---

    def _build_antibot_section(self):
        section = CollapsibleSection(self, "Anti-Bot / Bypass")
        section.pack(fill="x", pady=(0, 8))
        cf = section.content_frame

        # Impersonate
        self._impersonate_switch = ctk.CTkSwitch(
            cf, text="Enable browser impersonation", command=self._on_impersonate_toggle
        )
        self._impersonate_switch.pack(anchor="w", pady=(0, 4))

        self._impersonate_frame = ctk.CTkFrame(cf, fg_color="transparent")
        ctk.CTkLabel(self._impersonate_frame, text="Browser:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._impersonate_menu = ctk.CTkOptionMenu(
            self._impersonate_frame, values=IMPERSONATE_BROWSERS, command=lambda _: self._on_change()
        )
        self._impersonate_menu.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            self._impersonate_frame, text="Requires yt-dlp[curl-cffi]",
            font=ctk.CTkFont(size=11), text_color=("gray50", "gray60"),
        ).pack(side="left")

        # Proxy
        ctk.CTkLabel(cf, text="Proxy URL", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(8, 4))
        self._proxy_entry = ctk.CTkEntry(cf, placeholder_text="socks5://user:pass@host:port")
        self._proxy_entry.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(
            cf, text="Stored in plaintext",
            font=ctk.CTkFont(size=11), text_color=("#f57f17", "#ffb74d"),
        ).pack(anchor="w", pady=(0, 4))

        # User-Agent
        ctk.CTkLabel(cf, text="User-Agent", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(4, 4))
        self._ua_entry = ctk.CTkEntry(cf, placeholder_text="Mozilla/5.0 ...")
        self._ua_entry.pack(fill="x", pady=(0, 4))

        # Referer
        ctk.CTkLabel(cf, text="Referer", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(4, 4))
        self._referer_entry = ctk.CTkEntry(cf, placeholder_text="https://...")
        self._referer_entry.pack(fill="x", pady=(0, 4))

        # Custom headers
        ctk.CTkLabel(cf, text="Custom Headers", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(4, 4))
        self._headers_textbox = ctk.CTkTextbox(cf, height=50, wrap="word")
        self._headers_textbox.pack(fill="x")

    # --- Advanced Options Section (S-04d) ---

    def _build_advanced_section(self):
        section = CollapsibleSection(self, "Advanced Options")
        section.pack(fill="x", pady=(0, 8))
        cf = section.content_frame

        # Quality preset
        ctk.CTkLabel(cf, text="Quality Preset", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 4))
        self._quality_var = ctk.StringVar(value="Best MP4")
        self._quality_seg = ctk.CTkSegmentedButton(
            cf, values=list(QUALITY_PRESETS.keys()),
            variable=self._quality_var,
            command=self._on_quality_preset_change,
        )
        self._quality_seg.pack(fill="x", pady=(0, 8))

        # Format string
        ctk.CTkLabel(cf, text="Format String", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(0, 4))
        self._format_entry = ctk.CTkEntry(cf)
        self._format_entry.pack(fill="x", pady=(0, 8))

        # Rate limit
        rate_row = ctk.CTkFrame(cf, fg_color="transparent")
        rate_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(rate_row, text="Rate Limit (KB/s):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._rate_entry = ctk.CTkEntry(rate_row, placeholder_text="0 = unlimited", width=120)
        self._rate_entry.pack(side="left")

        # Retries
        retries_row = ctk.CTkFrame(cf, fg_color="transparent")
        retries_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(retries_row, text="Retries:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._retries_entry = ctk.CTkEntry(retries_row, width=80)
        self._retries_entry.pack(side="left")

        # Concurrent downloads
        concurrent_row = ctk.CTkFrame(cf, fg_color="transparent")
        concurrent_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(concurrent_row, text="Concurrent Downloads:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._concurrent_slider = ctk.CTkSlider(
            concurrent_row, from_=1, to=5, number_of_steps=4, command=self._on_concurrent_change
        )
        self._concurrent_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._concurrent_label = ctk.CTkLabel(concurrent_row, text="3", font=ctk.CTkFont(size=12), width=20)
        self._concurrent_label.pack(side="left")

        # Anti-Block sub-section
        anti_block_label = ctk.CTkLabel(
            cf, text="── Anti-Block ──",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        anti_block_label.pack(anchor="w", pady=(12, 4))

        # Anti-Block Mode toggle
        self._anti_block_switch = ctk.CTkSwitch(
            cf, text="Anti-Block Mode (safe preset)",
            command=self._on_anti_block_toggle,
        )
        self._anti_block_switch.pack(anchor="w", pady=(0, 8))

        # Sleep between downloads (min-max)
        sleep_row = ctk.CTkFrame(cf, fg_color="transparent")
        sleep_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(sleep_row, text="Sleep between downloads:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._sleep_min_entry = ctk.CTkEntry(sleep_row, placeholder_text="0", width=60)
        self._sleep_min_entry.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(sleep_row, text="-", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self._sleep_max_entry = ctk.CTkEntry(sleep_row, placeholder_text="0", width=60)
        self._sleep_max_entry.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(sleep_row, text="sec (0=off)", font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left", padx=(4, 0))

        # Sleep between requests
        req_row = ctk.CTkFrame(cf, fg_color="transparent")
        req_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(req_row, text="Sleep between requests:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._sleep_req_entry = ctk.CTkEntry(req_row, placeholder_text="0", width=60)
        self._sleep_req_entry.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(req_row, text="sec", font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left", padx=(4, 0))

        # Fragment retries
        frag_row = ctk.CTkFrame(cf, fg_color="transparent")
        frag_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(frag_row, text="Fragment retries:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._frag_retries_entry = ctk.CTkEntry(frag_row, placeholder_text="10", width=60)
        self._frag_retries_entry.pack(side="left")

        # Sleep between subtitles
        sub_sleep_row = ctk.CTkFrame(cf, fg_color="transparent")
        sub_sleep_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(sub_sleep_row, text="Sleep subtitles:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._sleep_sub_entry = ctk.CTkEntry(sub_sleep_row, placeholder_text="0", width=60)
        self._sleep_sub_entry.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(sub_sleep_row, text="sec", font=ctk.CTkFont(size=11), text_color=("gray50", "gray60")).pack(side="left", padx=(4, 0))

    # --- Audio & Post-Processing Section (S-04e) ---

    def _build_audio_section(self):
        section = CollapsibleSection(self, "Audio & Post-Processing")
        section.pack(fill="x", pady=(0, 8))
        cf = section.content_frame

        # Extract audio
        self._audio_switch = ctk.CTkSwitch(
            cf, text="Extract audio after download", command=self._on_audio_toggle
        )
        self._audio_switch.pack(anchor="w", pady=(0, 4))

        # Audio options (hidden by default)
        self._audio_opts_frame = ctk.CTkFrame(cf, fg_color="transparent")

        fmt_row = ctk.CTkFrame(self._audio_opts_frame, fg_color="transparent")
        fmt_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(fmt_row, text="Format:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._audio_format_menu = ctk.CTkOptionMenu(
            fmt_row, values=AUDIO_FORMATS, command=lambda _: self._on_change()
        )
        self._audio_format_menu.pack(side="left")

        qual_row = ctk.CTkFrame(self._audio_opts_frame, fg_color="transparent")
        qual_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(qual_row, text="Quality (0=best, 9=worst):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._audio_quality_slider = ctk.CTkSlider(
            qual_row, from_=0, to=9, number_of_steps=9, command=self._on_audio_quality_change
        )
        self._audio_quality_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._audio_quality_label = ctk.CTkLabel(qual_row, text="5", font=ctk.CTkFont(size=12), width=20)
        self._audio_quality_label.pack(side="left")

        # Post-processing switches
        self._thumbnail_switch = ctk.CTkSwitch(cf, text="Embed thumbnail", command=self._on_change)
        self._thumbnail_switch.pack(anchor="w", pady=(8, 4))

        self._metadata_switch = ctk.CTkSwitch(cf, text="Write metadata (info.json)", command=self._on_change)
        self._metadata_switch.pack(anchor="w", pady=(0, 4))

        # Subtitles
        sub_row = ctk.CTkFrame(cf, fg_color="transparent")
        sub_row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(sub_row, text="Subtitles:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self._subtitle_entry = ctk.CTkEntry(sub_row, placeholder_text="en,ja (comma-separated)")
        self._subtitle_entry.pack(side="left", fill="x", expand=True)

    # --- Widget value helpers ---

    def get_values(self) -> dict:
        """Read all widget values into a config dict."""
        values = {}

        # Tools
        values["ffmpeg_path"] = self._ffmpeg_entry.get()
        values["aria2c_path"] = self._aria2c_entry.get()
        values["aria2c_enabled"] = bool(self._aria2c_switch.get())
        values["aria2c_connections"] = int(self._aria2c_conn_slider.get())

        # Cookies
        mode_map = {"None": "none", "Browser": "browser", "File": "file", "JSON": "json"}
        values["cookie_mode"] = mode_map.get(self._cookie_mode_var.get(), "none")
        values["cookie_browser"] = self._cookie_browser_menu.get()
        values["cookie_file"] = self._cookie_file_entry.get()
        values["cookie_json"] = self._cookie_json_textbox.get("1.0", "end-1c")

        # Anti-bot
        values["impersonate_enabled"] = bool(self._impersonate_switch.get())
        values["impersonate_browser"] = self._impersonate_menu.get()
        values["proxy"] = self._proxy_entry.get()
        values["user_agent"] = self._ua_entry.get()
        values["referer"] = self._referer_entry.get()
        values["custom_headers"] = self._headers_textbox.get("1.0", "end-1c")

        # Advanced
        values["quality_preset"] = self._quality_var.get()
        values["format_string"] = self._format_entry.get()
        try:
            values["rate_limit"] = min(max(0, int(self._rate_entry.get() or 0)), MAX_RATE_LIMIT_KB)
        except ValueError:
            values["rate_limit"] = 0
        try:
            values["retries"] = min(max(0, int(self._retries_entry.get() or 3)), MAX_RETRIES)
        except ValueError:
            values["retries"] = 3
        values["concurrent_limit"] = min(max(1, int(self._concurrent_slider.get())), MAX_CONCURRENT)

        # Anti-block
        values["anti_block_mode"] = bool(self._anti_block_switch.get())
        try:
            values["sleep_interval"] = max(0, int(self._sleep_min_entry.get() or 0))
        except ValueError:
            values["sleep_interval"] = 0
        try:
            values["sleep_interval_max"] = max(0, int(self._sleep_max_entry.get() or 0))
        except ValueError:
            values["sleep_interval_max"] = 0
        try:
            values["sleep_requests"] = max(0, int(self._sleep_req_entry.get() or 0))
        except ValueError:
            values["sleep_requests"] = 0
        try:
            values["fragment_retries"] = min(max(0, int(self._frag_retries_entry.get() or 10)), MAX_RETRIES)
        except ValueError:
            values["fragment_retries"] = 10
        try:
            values["sleep_subtitles"] = max(0, int(self._sleep_sub_entry.get() or 0))
        except ValueError:
            values["sleep_subtitles"] = 0

        # Validate proxy URL format (allow empty)
        proxy = values.get("proxy", "")
        if proxy and not _PROXY_RE.match(proxy):
            logger.warning("Invalid proxy URL cleared: %s", proxy)
            values["proxy"] = ""

        # Audio
        values["audio_extract"] = bool(self._audio_switch.get())
        values["audio_format"] = self._audio_format_menu.get()
        values["audio_quality"] = int(self._audio_quality_slider.get())
        values["embed_thumbnail"] = bool(self._thumbnail_switch.get())
        values["write_metadata"] = bool(self._metadata_switch.get())
        values["subtitle_langs"] = self._subtitle_entry.get()

        return values

    def set_values(self, config: dict):
        """Populate widgets from config dict."""
        self._suppress_callbacks = True

        # Tools
        self._set_entry(self._ffmpeg_entry, config.get("ffmpeg_path", ""))
        self._set_entry(self._aria2c_entry, config.get("aria2c_path", ""))
        if config.get("aria2c_enabled"):
            self._aria2c_switch.select()
        else:
            self._aria2c_switch.deselect()
        self._aria2c_conn_slider.set(config.get("aria2c_connections", 16))
        self._aria2c_conn_label.configure(text=str(config.get("aria2c_connections", 16)))
        self._on_aria2c_toggle()

        # Cookies
        mode_rmap = {"none": "None", "browser": "Browser", "file": "File", "json": "JSON"}
        self._cookie_mode_var.set(mode_rmap.get(config.get("cookie_mode", "none"), "None"))
        self._cookie_browser_menu.set(config.get("cookie_browser", "chrome"))
        self._set_entry(self._cookie_file_entry, config.get("cookie_file", ""))
        self._cookie_json_textbox.delete("1.0", "end")
        if config.get("cookie_json"):
            self._cookie_json_textbox.insert("1.0", config["cookie_json"])
        self._on_cookie_mode_change(self._cookie_mode_var.get())

        # Anti-bot
        if config.get("impersonate_enabled"):
            self._impersonate_switch.select()
        else:
            self._impersonate_switch.deselect()
        self._impersonate_menu.set(config.get("impersonate_browser", "chrome"))
        self._on_impersonate_toggle()
        self._set_entry(self._proxy_entry, config.get("proxy", ""))
        self._set_entry(self._ua_entry, config.get("user_agent", ""))
        self._set_entry(self._referer_entry, config.get("referer", ""))
        self._headers_textbox.delete("1.0", "end")
        if config.get("custom_headers"):
            self._headers_textbox.insert("1.0", config["custom_headers"])

        # Advanced
        preset = config.get("quality_preset", "Best MP4")
        # Use directly if valid key, otherwise fallback
        if preset in QUALITY_PRESETS:
            display_preset = preset
        else:
            display_preset = "Best MP4"
        self._quality_var.set(display_preset)
        self._set_entry(self._format_entry, config.get("format_string", QUALITY_PRESETS["Best MP4"]))
        self._set_entry(self._rate_entry, str(config.get("rate_limit", 0)) if config.get("rate_limit") else "")
        self._set_entry(self._retries_entry, str(config.get("retries", 3)))
        self._concurrent_slider.set(config.get("concurrent_limit", 3))
        self._concurrent_label.configure(text=str(config.get("concurrent_limit", 3)))

        # Anti-block
        if config.get("anti_block_mode"):
            self._anti_block_switch.select()
        else:
            self._anti_block_switch.deselect()
        si = config.get("sleep_interval", 0)
        self._set_entry(self._sleep_min_entry, str(si) if si else "")
        si_max = config.get("sleep_interval_max", 0)
        self._set_entry(self._sleep_max_entry, str(si_max) if si_max else "")
        sr = config.get("sleep_requests", 0)
        self._set_entry(self._sleep_req_entry, str(sr) if sr else "")
        fr = config.get("fragment_retries", 10)
        self._set_entry(self._frag_retries_entry, str(fr))
        ss = config.get("sleep_subtitles", 0)
        self._set_entry(self._sleep_sub_entry, str(ss) if ss else "")

        # Audio
        if config.get("audio_extract"):
            self._audio_switch.select()
        else:
            self._audio_switch.deselect()
        self._audio_format_menu.set(config.get("audio_format", "mp3"))
        self._audio_quality_slider.set(config.get("audio_quality", 5))
        self._audio_quality_label.configure(text=str(config.get("audio_quality", 5)))
        self._on_audio_toggle()
        if config.get("embed_thumbnail"):
            self._thumbnail_switch.select()
        else:
            self._thumbnail_switch.deselect()
        if config.get("write_metadata"):
            self._metadata_switch.select()
        else:
            self._metadata_switch.deselect()
        self._set_entry(self._subtitle_entry, config.get("subtitle_langs", ""))

        self._update_tool_status()
        self._suppress_callbacks = False

    # --- Callbacks ---

    def _on_change(self, *_args):
        if not self._suppress_callbacks:
            self._on_config_change()

    def _on_aria2c_toggle(self):
        if self._aria2c_switch.get():
            self._aria2c_conn_frame.pack(fill="x", pady=(4, 4))
        else:
            self._aria2c_conn_frame.pack_forget()
        self._on_change()

    def _on_conn_change(self, value):
        self._aria2c_conn_label.configure(text=str(int(value)))
        self._on_change()

    def _on_cookie_mode_change(self, mode):
        self._cookie_browser_frame.pack_forget()
        self._cookie_browser_warning.pack_forget()
        self._cookie_file_frame.pack_forget()
        self._cookie_file_help.pack_forget()
        self._cookie_json_frame.pack_forget()
        if mode == "Browser":
            self._cookie_browser_frame.pack(fill="x", pady=(0, 4))
            self._cookie_browser_warning.pack(fill="x", pady=(4, 4))
        elif mode == "File":
            self._cookie_file_frame.pack(fill="x", pady=(0, 4))
            self._cookie_file_help.pack(fill="x", pady=(4, 4))
        elif mode == "JSON":
            self._cookie_json_frame.pack(fill="x", pady=(0, 4))
        self._on_change()

    def _on_impersonate_toggle(self):
        if self._impersonate_switch.get():
            self._impersonate_frame.pack(fill="x", pady=(4, 4))
        else:
            self._impersonate_frame.pack_forget()
        self._on_change()

    def _on_quality_preset_change(self, preset_name):
        fmt = QUALITY_PRESETS.get(preset_name, "")
        if fmt:
            self._set_entry(self._format_entry, fmt)
        self._on_change()

    def _on_concurrent_change(self, value):
        self._concurrent_label.configure(text=str(int(value)))
        self._on_change()

    def _on_anti_block_toggle(self):
        """Apply or clear Anti-Block Mode preset."""
        if self._anti_block_switch.get():
            # Save current values before overwriting
            self._pre_anti_block = {
                "concurrent": int(self._concurrent_slider.get()),
                "sleep_min": self._sleep_min_entry.get(),
                "sleep_max": self._sleep_max_entry.get(),
                "sleep_req": self._sleep_req_entry.get(),
            }
            self._concurrent_slider.set(1)
            self._concurrent_label.configure(text="1")
            self._set_entry(self._sleep_min_entry, "3")
            self._set_entry(self._sleep_max_entry, "8")
            self._set_entry(self._sleep_req_entry, "1")
        else:
            # Restore previous values or defaults
            prev = getattr(self, "_pre_anti_block", None)
            concurrent = prev["concurrent"] if prev else 3
            self._concurrent_slider.set(concurrent)
            self._concurrent_label.configure(text=str(concurrent))
            self._set_entry(self._sleep_min_entry, prev["sleep_min"] if prev else "")
            self._set_entry(self._sleep_max_entry, prev["sleep_max"] if prev else "")
            self._set_entry(self._sleep_req_entry, prev["sleep_req"] if prev else "")
        self._on_change()

    def _on_audio_toggle(self):
        if self._audio_switch.get():
            self._audio_opts_frame.pack(fill="x", pady=(4, 4))
        else:
            self._audio_opts_frame.pack_forget()
        self._on_change()

    def _on_audio_quality_change(self, value):
        self._audio_quality_label.configure(text=str(int(value)))
        self._on_change()

    # --- Browse dialogs ---

    def _browse_ffmpeg(self):
        path = filedialog.askopenfilename(title="Select FFmpeg")
        if path:
            self._set_entry(self._ffmpeg_entry, path)
            self._update_tool_status()
            self._on_change()

    def _browse_aria2c(self):
        path = filedialog.askopenfilename(title="Select aria2c")
        if path:
            self._set_entry(self._aria2c_entry, path)
            self._update_tool_status()
            self._on_change()

    def _browse_cookie_file(self):
        path = filedialog.askopenfilename(
            title="Select Cookie File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self._set_entry(self._cookie_file_entry, path)
            self._on_change()

    # --- Utilities ---

    def _update_tool_status(self):
        ffmpeg = find_ffmpeg(self._ffmpeg_entry.get())
        if ffmpeg:
            self._ffmpeg_status.configure(text="Found", text_color=("#2e7d32", "#4caf50"))
        else:
            self._ffmpeg_status.configure(text="Not Found", text_color=("#c62828", "#ef5350"))

        aria2c = find_aria2c(self._aria2c_entry.get())
        if aria2c:
            self._aria2c_status.configure(text="Found", text_color=("#2e7d32", "#4caf50"))
        else:
            self._aria2c_status.configure(text="Not Found", text_color=("#c62828", "#ef5350"))

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str):
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)
