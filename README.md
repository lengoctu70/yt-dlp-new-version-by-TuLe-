# yt-dlp Downloader GUI

A modern graphical user interface for the yt-dlp command-line tool, providing an easy way to download videos and audio from YouTube and other supported platforms.

## Features

- **Modern UI**: Built with CustomTkinter for a clean, responsive interface
- **Bulk Downloads**: 3-column input for folders, filenames, and URLs
- **Queue Management**: Download multiple videos concurrently (1-5 at a time)
- **Progress Tracking**: Real-time progress bars with speed and ETA
- **Advanced Options**: Cookies, proxy, custom headers, rate limiting
- **Audio Extraction**: Convert downloads to MP3, M4A, Opus, or FLAC
- **Anti-Block Mode**: Built-in delays and request throttling
- **External Downloader**: Optional aria2c support for faster downloads
- **Custom yt-dlp Binary**: Point the app at your own downloaded yt-dlp (Settings → Tools) to use a newer version than the bundled one
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Requirements

- Python 3.10+ (tested on 3.10, 3.11, 3.12+)
- yt-dlp (latest)
- CustomTkinter 5.2+
- pycryptodomex
- FFmpeg 4.2+ (optional, for post-processing)
- curl-cffi (optional, for browser impersonation)

## Installation

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yt-dlp-new-version-by-TuLe--main
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Run the application:
   ```bash
   python -m ytdlp_gui
   ```

### Windows One-Click Setup

For automatic setup on Windows, run:

```batch
scripts\windows\one_click_setup.bat
```

This will install Python (if needed), download required tools, and configure the application.

## Usage

1. **Enter URLs**: Paste video URLs in the right column (supports YouTube and 1000+ sites)
2. **Set Folders** (optional): Enter subfolder names in the left column
3. **Set Filenames** (optional): Enter custom filenames in the middle column
4. **Configure Settings**: Expand settings sections for advanced options
5. **Click Download All**: Start downloading

### Settings

- **Tools**: Configure yt-dlp binary, FFmpeg and aria2c paths. Setting a custom yt-dlp path switches downloads to that binary (fixes outdated-extractor errors like Vimeo `Failed to parse XML`); leave empty to use the built-in engine
- **Cookie Settings**: Use browser cookies, cookie files, or JSON
- **Anti-Bot/Bypass**: Enable impersonation, set proxy, custom headers
- **Advanced Options**: Quality presets, format strings, rate limits, sleep intervals
- **Audio & Post-Processing**: Extract audio, embed thumbnails, write metadata

## Project Structure

```
src/ytdlp_gui/
├── app.py                         # Entry point (61 LOC)
├── core/                          # Business logic (~700 LOC)
│   ├── config_manager.py         # Config persistence
│   ├── downloader.py             # Embedded yt-dlp API engine
│   ├── cli_args_builder.py       # Config → yt-dlp CLI args
│   ├── cli_downloader.py         # Custom yt-dlp binary engine (subprocess)
│   └── queue_manager.py          # Worker pool + engine dispatch
├── ui/                            # UI components (~1,700 LOC)
│   ├── main_window.py
│   ├── settings_panel.py
│   ├── queue_frame.py
│   ├── url_input_frame.py
│   └── collapsible_section.py
└── utils/                         # Helpers (~240 LOC)
    ├── sanitize.py              # Filename sanitization
    ├── cookie_converter.py
    ├── platform_utils.py
    └── tool_checker.py

tests/
└── test_sanitize.py               # 22 test methods
```

## Documentation

- [Project Overview & PDR](./docs/project-overview-pdr.md) - Features, requirements, tech stack
- [Code Standards](./docs/code-standards.md) - Style guide, patterns, testing standards
- [System Architecture](./docs/system-architecture.md) - Layers, data flow, threading model
- [Codebase Summary](./docs/codebase-summary.md) - Code metrics, file organization
- [Deployment Guide](./docs/deployment-guide.md) - Setup, troubleshooting, uninstall/update
- [Project Roadmap](./docs/project-roadmap.md) - Phases, priorities, metrics

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful download engine
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI framework
