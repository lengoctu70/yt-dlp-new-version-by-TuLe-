# Project Overview & Product Development Requirements

## Project Overview

The yt-dlp Downloader GUI is a Python-based desktop application that provides a user-friendly graphical interface for the yt-dlp command-line tool. It simplifies video and audio downloading from YouTube and other supported platforms.

## Product Development Requirements

### Functional Requirements

#### User Interface
- Modern GUI using CustomTkinter with light/dark theme support
- 3-column bulk input (folders, filenames, URLs)
- Real-time download progress with speed and ETA
- Collapsible settings sections
- Responsive layout (min 900x700)

#### Core Functionality
- URL validation for multiple formats (http/https, search queries, video IDs)
- Download queue with concurrent execution (1-5 parallel downloads)
- Per-download cancellation with cleanup
- Duplicate URL and filename detection
- Failed download retry support

#### Download Options
- Quality presets (Best MP4, 1080p, 720p, 480p, Audio Only)
- Custom format string support
- Audio extraction (MP3, M4A, Opus, FLAC)
- Subtitle download by language code
- Metadata and thumbnail embedding

#### Advanced Features
- Cookie support (browser, file, JSON paste)
- Browser impersonation (requires curl-cffi)
- Proxy configuration (HTTP/SOCKS)
- Custom headers and User-Agent
- Rate limiting
- Anti-block mode with sleep intervals
- aria2c external downloader support

#### Configuration Management
- Persistent JSON-based settings
- Auto-detected tool paths (FFmpeg, aria2c)
- Default download folder selection
- 40+ configurable options

### Non-Functional Requirements

#### Performance
- Non-blocking UI during downloads (threading)
- Configurable concurrent downloads (1-5)
- Queue-based message passing between threads
- Efficient temp file cleanup on cancel

#### Compatibility
- Python 3.10 or higher
- Windows 10+, macOS 10.14+, Linux
- Cross-platform path handling
- macOS paste bug workaround

#### Reliability
- Graceful download cancellation
- Partial file cleanup on interrupt
- Retry logic with configurable attempts
- Error messages propagated to UI

#### Security
- Cookie file stored with user-only permissions (0o600)
- Proxy URL validation
- Path sanitization for filenames
- No sensitive data in logs

## Target Audience

- Users preferring GUI over command-line tools
- Content creators downloading reference material
- Users needing bulk download capabilities
- Those requiring advanced options (cookies, proxy, etc.)

## Key Success Metrics

1. Download success rate >95% for supported content
2. UI remains responsive during concurrent downloads
3. Zero data loss on graceful cancellation
4. Successful extraction with FFmpeg when configured

## Technology Stack

- **Language**: Python 3.10+
- **UI Framework**: CustomTkinter 5.2+
- **Download Engine**: yt-dlp (latest)
- **Media Processing**: FFmpeg
- **Configuration**: JSON file storage
- **Optional Acceleration**: aria2c

## Dependencies

### Required
- `yt-dlp`: Core downloading functionality
- `customtkinter>=5.2.2`: UI framework
- `pycryptodomex`: AES-128 stream decryption

### Optional
- `yt-dlp[curl-cffi]`: Browser impersonation
- FFmpeg: Post-processing and format conversion
- aria2c: External downloader for segmented files

## Version

Current version: **0.1.0** (defined in `src/ytdlp_gui/__init__.py` and `pyproject.toml`)
