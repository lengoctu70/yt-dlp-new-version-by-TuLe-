"""Centralized filename and folder name sanitization utilities.

Handles special characters that could break file paths, yt-dlp template
strings, or cause cross-platform compatibility issues.
"""

import re
import unicodedata

# Characters illegal in file/folder names on Windows/macOS/Linux
_ILLEGAL_CHARS_RE = re.compile(r'[<>:"/\\|?*]')

# Unicode control and invisible characters to strip
_INVISIBLE_RE = re.compile(
    r'[\x00-\x1f\x7f'           # C0 controls + DEL
    r'\u200b\u200c\u200d\u200e'  # zero-width chars, LRM
    r'\u200f\u202a-\u202e'       # bidi overrides
    r'\u2060\u2061-\u2064'       # word joiner, invisible operators
    r'\ufeff\ufff9-\ufffb]'      # BOM, interlinear annotation
)

# Windows reserved device names (case-insensitive)
_WINDOWS_RESERVED = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})

# Maximum filename length (leave room for extension + path prefix)
_MAX_NAME_LENGTH = 200


def sanitize_filename(name: str) -> str:
    """Sanitize a user-provided filename for safe use with yt-dlp and filesystems.

    Processing steps:
    1. Strip Unicode invisible/control characters
    2. Replace illegal path characters (<>:"/\\|?*) with underscore
    3. Replace '%' with fullwidth '％' to avoid yt-dlp template conflicts
    4. Replace '#' with underscore (problematic on some filesystems/URLs)
    5. Remove '..' path traversal sequences
    6. Collapse consecutive whitespace
    7. Trim leading/trailing dots and spaces
    8. Truncate to MAX_NAME_LENGTH characters
    9. Handle Windows reserved device names
    10. Return 'download' if name is empty after sanitization
    """
    return _sanitize(name, escape_percent=True)


def sanitize_foldername(name: str) -> str:
    """Sanitize a user-provided folder name for safe use in file paths.

    Same as sanitize_filename but does NOT escape '%' since folder names
    are not passed through yt-dlp's template engine.
    """
    return _sanitize(name, escape_percent=False)


def _sanitize(name: str, *, escape_percent: bool) -> str:
    """Core sanitization logic shared by filename and foldername sanitizers."""
    if not name:
        return ""

    # 1. Normalize unicode to NFC form (combine diacritics)
    name = unicodedata.normalize("NFC", name)

    # 2. Strip invisible / control characters
    name = _INVISIBLE_RE.sub("", name)

    # 3. Replace illegal filesystem characters with underscore
    name = _ILLEGAL_CHARS_RE.sub("_", name)

    # 4. Escape '%' to fullwidth '％' (avoids yt-dlp %(template)s conflicts)
    if escape_percent:
        name = name.replace("%", "\uff05")

    # 5. Replace '#' with underscore
    name = name.replace("#", "_")

    # 6. Strip directory separators (should not be in a single name component)
    name = name.replace("/", "_").replace("\\", "_")

    # 7. Remove path traversal sequences
    while ".." in name:
        name = name.replace("..", "")

    # 8. Collapse consecutive whitespace into a single space
    name = re.sub(r"\s+", " ", name)

    # 9. Trim leading/trailing dots and spaces (Windows restriction)
    name = name.strip(". ")

    # 10. Truncate to safe length
    if len(name) > _MAX_NAME_LENGTH:
        name = name[:_MAX_NAME_LENGTH].rstrip(". ")

    # 11. Handle Windows reserved device names
    stem = name.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        name = f"_{name}"

    # 12. Fallback if nothing remains
    if not name:
        return "download"

    return name
