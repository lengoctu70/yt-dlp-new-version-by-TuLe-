"""Tests for CLI argument building used by the custom yt-dlp binary engine."""

import unittest
from pathlib import Path

from ytdlp_gui.core.cli_args_builder import build_cli_args, build_output_template


def _base_config(**overrides) -> dict:
    config = {
        "format_string": "bestvideo+bestaudio/best",
        "retries": 3,
        "fragment_retries": 10,
        "cookie_mode": "none",
        "audio_extract": False,
    }
    config.update(overrides)
    return config


class TestBuildCliArgs(unittest.TestCase):
    def _arg_value(self, args: list, flag: str) -> str:
        self.assertIn(flag, args)
        return args[args.index(flag) + 1]

    def test_referer_passed_through(self):
        args, _ = build_cli_args(_base_config(referer="https://vimeo.com/"), "/tmp/dl", "")
        self.assertEqual(self._arg_value(args, "--referer"), "https://vimeo.com/")

    def test_custom_headers(self):
        config = _base_config(custom_headers="X-Test: abc\nOrigin: https://example.com")
        args, _ = build_cli_args(config, "/tmp/dl", "")
        self.assertIn("--add-header", args)
        self.assertIn("X-Test:abc", args)
        self.assertIn("Origin:https://example.com", args)

    def test_aria2c_args(self):
        config = _base_config(
            aria2c_enabled=True, aria2c_path="", aria2c_connections=8
        )
        args, _ = build_cli_args(config, "/tmp/dl", "")
        # Only present when aria2c binary is found on this machine
        if "--downloader" in args:
            dl_args = self._arg_value(args, "--downloader-args")
            self.assertIn("-x8", dl_args)
            self.assertIn("-s8", dl_args)
            self.assertIn("-k1M", dl_args)

    def test_audio_extract_flags(self):
        config = _base_config(audio_extract=True, audio_format="mp3", audio_quality=5)
        args, _ = build_cli_args(config, "/tmp/dl", "")
        self.assertIn("-x", args)
        self.assertEqual(self._arg_value(args, "--audio-format"), "mp3")
        self.assertNotIn("--merge-output-format", args)

    def test_video_merge_mp4(self):
        args, _ = build_cli_args(_base_config(), "/tmp/dl", "")
        self.assertEqual(self._arg_value(args, "--merge-output-format"), "mp4")

    def test_impersonate_flag(self):
        config = _base_config(impersonate_enabled=True, impersonate_browser="chrome")
        args, _ = build_cli_args(config, "/tmp/dl", "")
        self.assertEqual(self._arg_value(args, "--impersonate"), "chrome")

    def test_rate_limit(self):
        args, _ = build_cli_args(_base_config(rate_limit=500), "/tmp/dl", "")
        self.assertEqual(self._arg_value(args, "--limit-rate"), "500K")

    def test_no_temp_cookie_without_json(self):
        _, temp_cookie = build_cli_args(_base_config(), "/tmp/dl", "")
        self.assertIsNone(temp_cookie)


class TestBuildOutputTemplate(unittest.TestCase):
    def test_default_template(self):
        result = build_output_template("/tmp/dl", "")
        self.assertEqual(result, str(Path("/tmp/dl") / "%(title)s.%(ext)s"))

    def test_filename_without_extension_gets_ext_template(self):
        result = build_output_template("/tmp/dl", "my video")
        self.assertTrue(result.endswith(".%(ext)s"))

    def test_filename_with_media_extension_preserved(self):
        result = build_output_template("/tmp/dl", "clip.mp4")
        self.assertTrue(result.endswith("clip.mp4"))

    def test_dotted_title_not_treated_as_extension(self):
        result = build_output_template("/tmp/dl", "7.1 - Origins")
        self.assertTrue(result.endswith(".%(ext)s"))


if __name__ == "__main__":
    unittest.main()
