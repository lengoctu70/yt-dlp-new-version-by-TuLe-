"""Convert JSON cookies (from browser extensions) to Netscape format for yt-dlp."""

import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Netscape cookie file header
NETSCAPE_HEADER = "# Netscape HTTP Cookie File\n# https://curl.se/docs/http-cookies.html\n\n"


def json_cookies_to_netscape(json_str: str) -> str:
    """Convert JSON cookies string to Netscape cookie format.

    Accepts JSON in two formats:
    1. Array of cookies: [{"domain": "...", "name": "...", "value": "...", ...}, ...]
    2. Object with cookies key: {"url": "...", "cookies": [...]}

    Returns Netscape format string.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Handle both formats
    if isinstance(data, list):
        cookies = data
    elif isinstance(data, dict) and "cookies" in data:
        cookies = data["cookies"]
    else:
        raise ValueError("JSON must be an array of cookies or an object with a 'cookies' key")

    lines = [NETSCAPE_HEADER]

    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue

        domain = cookie.get("domain", "")
        # Netscape format: include_subdomains is TRUE if domain starts with '.'
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = cookie.get("path", "/")
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        # expirationDate: 0 or missing means session cookie
        expiry = str(int(cookie.get("expirationDate", 0)))
        name = cookie.get("name", "")
        value = cookie.get("value", "")

        if not name:
            continue

        line = f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expiry}\t{name}\t{value}"
        lines.append(line)

    return "\n".join(lines) + "\n"


def save_json_cookies_to_temp(json_str: str) -> str | None:
    """Convert JSON cookies and save to a temporary Netscape cookie file.

    Returns the path to the temp file, or None on failure.
    """
    try:
        netscape_content = json_cookies_to_netscape(json_str)
    except ValueError as e:
        logger.warning("Failed to parse JSON cookies: %s", e)
        return None

    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix="_cookies.txt",
            prefix="ytdlp_",
            delete=False,
            encoding="utf-8",
        )
        tmp.write(netscape_content)
        tmp.close()
        return tmp.name
    except OSError as e:
        logger.warning("Failed to write temp cookie file: %s", e)
        return None
