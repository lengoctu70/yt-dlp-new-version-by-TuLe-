import os
import platform
import re
from pathlib import Path
from tkinter import filedialog
from urllib.parse import urlparse

import customtkinter as ctk

from ytdlp_gui.core import DownloadItem
from ytdlp_gui.core.config_manager import save_config
from ytdlp_gui.utils.sanitize import sanitize_filename, sanitize_foldername

# yt-dlp supported URL schemes (beyond standard http/https)
_EXTENDED_SCHEMES = frozenset({"http", "https", "rtmp", "rtmps", "mms", "rtsp"})
# Patterns that yt-dlp treats as search queries
_SEARCH_PREFIXES = ("ytsearch:", "ytsearchdate:", "scsearch:", "auto:")

_IS_MACOS = platform.system() == "Darwin"


def _custom_paste(textbox: ctk.CTkTextbox, event=None):
    """Custom paste handler to prevent macOS double-paste bug.

    On macOS, tkinter fires the <<Paste>> event twice (once from the
    default Tk binding and once from the macOS input method), causing
    pasted text to be duplicated. This handler manually inserts clipboard
    content and returns 'break' to suppress the default handler.
    """
    try:
        clipboard = textbox.clipboard_get()
    except Exception:
        return "break"

    # Delete selected text if any
    try:
        sel_first = textbox._textbox.index("sel.first")
        sel_last = textbox._textbox.index("sel.last")
        textbox._textbox.delete(sel_first, sel_last)
    except Exception:
        pass  # No selection — that's fine

    textbox._textbox.insert("insert", clipboard)
    return "break"


class URLInputFrame(ctk.CTkFrame):
    """3-column bulk input: folders, filenames, URLs."""

    def __init__(self, master, config: dict, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._config = config

        # Column headers + textboxes
        columns_frame = ctk.CTkFrame(self, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True)
        columns_frame.columnconfigure((0, 1, 2), weight=1, uniform="col")

        col_defs = [
            ("Folders", "subfolder name (e.g. 123)"),
            ("Filenames", "video_name (optional)"),
            ("URLs", "https://youtube.com/watch?v=..."),
        ]

        self._textboxes: list[ctk.CTkTextbox] = []
        for i, (label_text, placeholder) in enumerate(col_defs):
            col_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
            col_frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0))

            ctk.CTkLabel(
                col_frame, text=label_text, font=ctk.CTkFont(size=13, weight="bold")
            ).pack(anchor="w", pady=(0, 4))

            textbox = ctk.CTkTextbox(col_frame, height=150, wrap="none")
            textbox.pack(fill="both", expand=True)
            self._textboxes.append(textbox)

            # Fix macOS double-paste bug in tkinter/customtkinter
            if _IS_MACOS:
                textbox._textbox.bind(
                    "<<Paste>>",
                    lambda e, tb=textbox: _custom_paste(tb, e),
                )
                # Also bind Cmd+V directly as a fallback
                textbox._textbox.bind(
                    "<Command-v>",
                    lambda e, tb=textbox: _custom_paste(tb, e),
                )

        # Bottom row: default folder button + validation error
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", pady=(8, 0))

        ctk.CTkButton(
            bottom,
            text="Set Default Folder",
            command=self._set_default_folder,
            width=150,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(size=13),
        ).pack(side="left")

        default_folder = config.get("default_folder", "")
        self._folder_label = ctk.CTkLabel(
            bottom,
            text=f"Default: {default_folder}" if default_folder else "",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        self._folder_label.pack(side="left", padx=(8, 0))

        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color=("#c62828", "#ef5350"),
            font=ctk.CTkFont(size=12),
        )

    def get_items(self) -> list[DownloadItem]:
        """Parse columns into DownloadItems. Skip lines where URL is empty."""
        folders = self._get_lines(0)
        filenames = self._get_lines(1)
        urls = self._get_lines(2)

        max_lines = max(len(folders), len(filenames), len(urls))
        # Pad shorter columns
        folders.extend([""] * (max_lines - len(folders)))
        filenames.extend([""] * (max_lines - len(filenames)))
        urls.extend([""] * (max_lines - len(urls)))

        default_folder = self._config.get("default_folder", str(Path.home() / "Downloads"))

        items = []
        for i in range(max_lines):
            url = urls[i].strip()
            if not url:
                continue

            # --- Folder logic: always create subfolder inside default_folder ---
            raw_folder = folders[i].strip()
            if raw_folder:
                if os.path.isabs(raw_folder):
                    # Absolute path → use as-is
                    folder = raw_folder
                else:
                    # Relative name → sanitize & join with default_folder
                    safe_folder = sanitize_foldername(raw_folder)
                    if safe_folder:
                        folder = str(Path(default_folder) / safe_folder)
                    else:
                        folder = default_folder
            else:
                folder = default_folder

            # --- Filename sanitization ---
            raw_filename = filenames[i].strip()
            filename = sanitize_filename(raw_filename) if raw_filename else ""

            items.append(DownloadItem(url=url, folder=folder, filename=filename))

        return items

    def validate(self) -> list[str]:
        """Backward-compatible validation API returning combined messages."""
        result = self.validate_detailed()
        return result["errors"] + result["warnings"]

    def validate_detailed(self) -> dict[str, list[str]]:
        """Validate inputs and split hard errors from warnings."""
        folders = self._get_lines(0)
        filenames = self._get_lines(1)
        urls = self._get_lines(2)

        if not any(line.strip() for line in urls):
            return {"errors": ["No URLs entered"], "warnings": []}

        max_lines = max(len(folders), len(filenames), len(urls))
        folders.extend([""] * (max_lines - len(folders)))
        filenames.extend([""] * (max_lines - len(filenames)))
        urls.extend([""] * (max_lines - len(urls)))

        errors = []
        warnings = []
        for i in range(max_lines):
            raw_url = urls[i].strip()
            if not raw_url and (folders[i].strip() or filenames[i].strip()):
                warnings.append(f"⚠ Line {i + 1}: folder/filename provided but URL is empty (line ignored)")
            if raw_url and not self._is_valid_url(raw_url):
                if self._is_extended_url(raw_url):
                    warnings.append(f"⚠ Line {i + 1}: non-standard URL (may still work with yt-dlp)")
                else:
                    errors.append(f"❌ Line {i + 1}: invalid URL format")

        # --- Duplicate URL detection ---
        url_seen: dict[str, list[int]] = {}
        for i, raw_url in enumerate(urls[:max_lines]):
            u = raw_url.strip()
            if u:
                url_seen.setdefault(u, []).append(i + 1)  # 1-indexed lines
        for u, lines in url_seen.items():
            if len(lines) > 1:
                line_nums = ", ".join(str(n) for n in lines)
                warnings.append(f"⚠ Duplicate URL at lines {line_nums}")

        # --- Duplicate filename detection (ignore empty) ---
        fname_seen: dict[str, list[int]] = {}
        for i, raw_fn in enumerate(filenames[:max_lines]):
            if not urls[i].strip():
                continue
            fn = raw_fn.strip()
            if fn:
                fname_seen.setdefault(fn, []).append(i + 1)
        for fn, lines in fname_seen.items():
            if len(lines) > 1:
                line_nums = ", ".join(str(n) for n in lines)
                warnings.append(f"⚠ Duplicate filename \"{fn}\" at lines {line_nums}")

        return {"errors": errors, "warnings": warnings}

    @staticmethod
    def _is_valid_url(raw_url: str) -> bool:
        """Check if URL has a standard http(s) scheme and a host."""
        try:
            parsed = urlparse(raw_url)
        except ValueError:
            return False
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    @staticmethod
    def _is_extended_url(raw_url: str) -> bool:
        """Check if URL is a yt-dlp-supported non-standard format.

        Returns True for search queries (ytsearch:...), extended schemes
        (rtmp://, rtsp://), or bare video IDs.
        """
        # Search prefixes
        if any(raw_url.lower().startswith(p) for p in _SEARCH_PREFIXES):
            return True
        # Extended schemes
        try:
            parsed = urlparse(raw_url)
            if parsed.scheme in _EXTENDED_SCHEMES and parsed.netloc:
                return True
        except ValueError:
            pass
        # Bare video ID (alphanumeric + hyphens/underscores, 6-20 chars)
        if re.match(r'^[a-zA-Z0-9_-]{6,20}$', raw_url):
            return True
        return False

    def show_validation_error(self, msg: str):
        if msg:
            self._error_label.configure(text=msg)
            self._error_label.pack(fill="x", pady=(4, 0))
        else:
            self._error_label.pack_forget()

    def clear(self):
        for tb in self._textboxes:
            tb.delete("1.0", "end")
        self._error_label.pack_forget()

    def load_items(self, items: list) -> None:
        """Load DownloadItems back into the 3 input columns for editing.

        Clears existing content and fills Folders, Filenames, URLs
        from the given items so the user can edit and re-download.
        """
        self.clear()

        default_folder = self._config.get("default_folder", str(Path.home() / "Downloads"))

        folders_lines = []
        filenames_lines = []
        urls_lines = []

        for item in items:
            # Reverse folder logic: if folder == default_folder, leave empty
            # If folder is subfolder of default_folder, show relative part
            folder_display = ""
            if item.folder and item.folder != default_folder:
                try:
                    rel = Path(item.folder).relative_to(default_folder)
                    folder_display = str(rel)
                except ValueError:
                    # Absolute path outside default_folder
                    folder_display = item.folder
            folders_lines.append(folder_display)
            filenames_lines.append(item.filename or "")
            urls_lines.append(item.url)

        # Use a single space for empty values so _get_lines() won't skip
        # blank lines and cause column misalignment
        self._textboxes[0].insert("1.0", "\n".join(f or " " for f in folders_lines))
        self._textboxes[1].insert("1.0", "\n".join(f or " " for f in filenames_lines))
        self._textboxes[2].insert("1.0", "\n".join(urls_lines))

    def _get_lines(self, col_index: int) -> list[str]:
        """Get all lines from a textbox, preserving blank lines for alignment."""
        text = self._textboxes[col_index].get("1.0", "end-1c")
        return text.splitlines()

    def _get_nonempty_lines(self, col_index: int) -> list[str]:
        """Get only non-empty lines (for validation counts)."""
        return [line for line in self._get_lines(col_index) if line.strip()]

    def remove_items(self, items: list) -> None:
        """Remove lines corresponding to the given DownloadItems.

        Scans the active lines in the textboxes. If a line matches the
        URL, folder, and filename of a completed item, that line is removed.
        Removal happens from bottom to top to preserve indices during loop.
        """
        if not items:
            return

        # Snapshots of current lines
        folders = self._get_lines(0)
        filenames = self._get_lines(1)
        urls = self._get_lines(2)
        max_lines = max(len(folders), len(filenames), len(urls))

        # Pad
        folders.extend([""] * (max_lines - len(folders)))
        filenames.extend([""] * (max_lines - len(filenames)))
        urls.extend([""] * (max_lines - len(urls)))

        # Identify lines to remove
        indices_to_remove = []
        default_folder = self._config.get("default_folder", str(Path.home() / "Downloads"))

        # Pre-process items for easier matching
        # (item.folder, item.filename, item.url)
        # Note: input folder might be relative or absolute.
        # We need to reconstruct what logical "folder" string meant.
        # But actually, simpler: compare normalized URL and filename?
        # A 100% robust match is hard because user might have typed partial folder.
        # Let's match primarily on URL and Filename.
        
        # Helper to normalize item folder for comparison
        def normalize_folder(f):
            return str(Path(f)).strip()

        targets = []
        for item in items:
            targets.append((item.url.strip(), item.filename.strip(), item.folder.strip()))

        for i in range(max_lines):
            line_url = urls[i].strip()
            line_fn = sanitize_filename(filenames[i].strip())
            
            # Reconstruct what the 'folder' means for this line
            raw_folder = folders[i].strip()
            if raw_folder:
                if os.path.isabs(raw_folder):
                    line_folder = raw_folder
                else:
                    safe_folder = sanitize_foldername(raw_folder)
                    if safe_folder:
                        line_folder = str(Path(default_folder) / safe_folder)
                    else:
                        line_folder = default_folder
            else:
                line_folder = default_folder
            
            line_folder = str(Path(line_folder)).strip()

            # Check if this line matches any completed item
            matched = False
            for (t_url, t_fn, t_folder) in targets:
                # Compare URL (exact), Filename (exact), Folder (exact resolved path)
                if t_url == line_url and t_fn == line_fn and t_folder == line_folder:
                    matched = True
                    break
            
            if matched:
                indices_to_remove.append(i)

        # Remove matching lines in reverse order
        for i in reversed(indices_to_remove):
            for tb in self._textboxes:
                # Tkinter text index: "line.0" -> "line+1.0"
                # But note: lines are 1-indexed in Tkinter ('1.0'), but 0-indexed in our list 'i'
                start_idx = f"{i + 1}.0"
                end_idx = f"{i + 2}.0"
                tb.delete(start_idx, end_idx)

    def _set_default_folder(self):
        folder = filedialog.askdirectory(title="Select Default Download Folder")
        if folder:
            self._config["default_folder"] = folder
            self._folder_label.configure(text=f"Default: {folder}")
            save_config(self._config)
