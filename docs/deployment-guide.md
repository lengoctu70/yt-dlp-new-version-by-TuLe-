# Deployment Guide

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Running from Source](#running-from-source)
3. [Platform-Specific Setup](#platform-specific-setup)
4. [Windows One-Click Setup](#windows-one-click-setup)
5. [Building Executables](#building-executables)
6. [Troubleshooting](#troubleshooting)

## Environment Setup

### Prerequisites

1. **Python**: Version 3.10 or higher
2. **Operating System**: Windows 10+, macOS 10.14+, or Linux
3. **External Tools** (optional but recommended):
   - FFmpeg (for video/audio processing)
   - aria2c (for accelerated downloads)

### Setup Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd yt-dlp-new-version-by-TuLe--main
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

   Or install manually:
   ```bash
   pip install yt-dlp customtkinter pycryptodomex
   ```

4. Optional - Install curl-cffi for browser impersonation:
   ```bash
   pip install 'yt-dlp[curl-cffi]'
   ```

## Running from Source

```bash
python -m ytdlp_gui
```

Or:

```bash
python src/ytdlp_gui/app.py
```

## Platform-Specific Setup

### Windows

#### Manual Setup

1. Install Python 3.10+ from [python.org](https://python.org)
2. Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
3. Extract FFmpeg and add to PATH, or configure path in app settings
4. (Optional) Download aria2c from [GitHub releases](https://github.com/aria2/aria2/releases)

#### Windows One-Click Setup

Run the provided setup script for automatic installation:

```batch
scripts\windows\one_click_setup.bat
```

This script will:
- Check and install Python 3.10+ if missing
- Download yt-dlp.exe, FFmpeg, and aria2c to `%USERPROFILE%\.ytdlp-gui\tools\bin\`
- Install Python dependencies
- Configure the application
- Add tools to user PATH

**Requirements**: Internet connection, PowerShell execution policy may need adjustment

### macOS

#### Using Homebrew

```bash
# Install Python and FFmpeg
brew install python ffmpeg

# Optional: Install aria2
brew install aria2
```

#### Manual Installation

1. Install Python from [python.org](https://python.org)
2. Install FFmpeg using Homebrew or download from [ffmpeg.org](https://ffmpeg.org)

### Linux

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv ffmpeg

# Optional
sudo apt-get install aria2
```

#### Fedora

```bash
sudo dnf install python3 python3-pip ffmpeg

# Optional
sudo dnf install aria2
```

## Building Executables

### Using PyInstaller

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build executable:
   ```bash
   pyinstaller --onefile --windowed \
     --name ytdlp-gui \
     --add-data "src/ytdlp_gui: ytdlp_gui" \
     src/ytdlp_gui/app.py
   ```

3. Output will be in `dist/` directory

### Using build (Python package)

```bash
pip install build
python -m build
```

This creates a wheel in `dist/` that can be installed with pip.

## Troubleshooting

### Common Issues

1. **Python Not Found**
   - Ensure Python 3.10+ is installed
   - Check PATH environment variable
   - On Windows: Use "Add to PATH" during Python installation

2. **Missing External Tools**
   - Install FFmpeg for video/audio processing
   - Configure tool paths in app Settings > Tools
   - Or use Windows one-click setup for automatic installation

3. **Import Errors**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -e .`

4. **Cookie Extraction Fails**
   - Browser cookies may fail with DPAPI errors on Windows
   - Use "File" mode with exported cookies.txt instead
   - Or use "JSON" mode with cookies from browser extensions

5. **Download Failures**
   - Check internet connection
   - Update yt-dlp: `pip install -U yt-dlp`
   - Try Anti-Block mode in settings
   - Configure proxy if behind firewall

### Debug Mode

Enable debug logging:

```bash
# Environment variable
export YTDL_DEBUG=1
python -m ytdlp_gui
```

Or modify logging level in `src/ytdlp_gui/app.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

### Log Locations

- Config directory: `~/.ytdlp-gui/` (Linux/macOS) or `%USERPROFILE%\.ytdlp-gui\` (Windows)
- Logs are printed to console by default

## Configuration

Configuration is stored in:
- Windows: `%USERPROFILE%\.ytdlp-gui\config.json`
- macOS/Linux: `~/.ytdlp-gui/config.json`

The file is created automatically on first run with sensible defaults.
