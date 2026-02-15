"""Tests for the centralized sanitization module."""

import pytest
from ytdlp_gui.utils.sanitize import sanitize_filename, sanitize_foldername


class TestSanitizeFilename:
    """Tests for sanitize_filename()."""

    def test_normal_name_unchanged(self):
        assert sanitize_filename("my_video") == "my_video"

    def test_percent_escaped_to_fullwidth(self):
        """% must be escaped to avoid yt-dlp template conflicts."""
        result = sanitize_filename("100%_done")
        assert "%" not in result
        assert "\uff05" in result  # fullwidth percent

    def test_hash_replaced(self):
        assert "#" not in sanitize_filename("video#1")

    def test_illegal_chars_replaced(self):
        result = sanitize_filename('file<>:"|?*name')
        for ch in '<>:"|?*':
            assert ch not in result

    def test_path_traversal_removed(self):
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_directory_separators_replaced(self):
        result = sanitize_filename("path/to\\file")
        assert "/" not in result
        assert "\\" not in result

    def test_unicode_invisible_stripped(self):
        # Zero-width space U+200B
        result = sanitize_filename("hello\u200bworld")
        assert "\u200b" not in result
        assert "helloworld" == result

    def test_bom_stripped(self):
        result = sanitize_filename("\ufeffvideo")
        assert "\ufeff" not in result
        assert result == "video"

    def test_whitespace_collapsed(self):
        assert sanitize_filename("hello   world") == "hello world"

    def test_leading_trailing_dots_stripped(self):
        assert sanitize_filename("...video...") == "video"

    def test_max_length_enforced(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_windows_reserved_names(self):
        for name in ("CON", "NUL", "AUX", "PRN", "COM1", "LPT1"):
            result = sanitize_filename(name)
            assert result.upper() != name, f"{name} should be prefixed"
            assert result.startswith("_")

    def test_windows_reserved_with_extension(self):
        result = sanitize_filename("CON.txt")
        assert result.startswith("_")

    def test_empty_string_returns_download(self):
        assert sanitize_filename("") == ""

    def test_only_illegal_chars_returns_download(self):
        # Only dots and path-only chars → fully stripped → fallback
        result = sanitize_filename("......")
        assert result == "download"

    def test_real_world_youtube_title(self):
        title = "Video 100% Working! (2024) #trending"
        result = sanitize_filename(title)
        assert "%" not in result
        assert "#" not in result
        assert len(result) > 0

    def test_unicode_filename_preserved(self):
        """Non-control unicode characters should be preserved."""
        result = sanitize_filename("Bài hát tiếng Việt")
        assert result == "Bài hát tiếng Việt"


class TestSanitizeFoldername:
    """Tests for sanitize_foldername()."""

    def test_percent_not_escaped(self):
        """Folder names don't go through yt-dlp templates, so % is kept."""
        result = sanitize_foldername("100%_done")
        assert "%" in result

    def test_illegal_chars_still_replaced(self):
        result = sanitize_foldername('folder<>name')
        assert "<" not in result
        assert ">" not in result

    def test_hash_replaced(self):
        assert "#" not in sanitize_foldername("folder#1")

    def test_path_traversal_removed(self):
        result = sanitize_foldername("../../secret")
        assert ".." not in result

    def test_empty_returns_empty(self):
        assert sanitize_foldername("") == ""
