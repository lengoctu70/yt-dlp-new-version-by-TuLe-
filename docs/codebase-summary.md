# Codebase Summary

## Project Overview

The yt-dlp Downloader GUI is a Python desktop application providing a user-friendly interface for downloading videos using the yt-dlp library. Built with CustomTkinter for a modern UI experience.

## Code Metrics

- **Total Python Files**: 16
- **Total Lines of Code**: ~2,655
- **Main Source Directory**: `src/ytdlp_gui/`
- **Language**: Python 3.10+
- **Primary UI Framework**: CustomTkinter
- **Core Dependency**: yt-dlp

## Code Distribution by Layer

### UI Layer (~1,716 LOC - 65% of codebase)
Graphical interface components built with CustomTkinter:

| File | Purpose | LOC |
|------|---------|-----|
| `settings_panel.py` | Download settings, tools, cookies, anti-bot options | 736 |
| `url_input_frame.py` | 3-column bulk URL input (folders/filenames/URLs) | 411 |
| `queue_frame.py` | Download queue display with progress rows | 269 |
| `main_window.py` | Main application window composition | 257 |
| `collapsible_section.py` | Reusable collapsible UI component | 43 |

### Core Logic Layer (~684 LOC - 26% of codebase)
Business operations and download management:

| File | Purpose | LOC |
|------|---------|-----|
| `downloader.py` | yt-dlp integration, progress hooks, download execution | 422 |
| `queue_manager.py` | Concurrent download worker pool management | 158 |
| `config_manager.py` | Configuration persistence and defaults | 79 |
| `__init__.py` | DownloadItem dataclass, DownloadStatus enum | 25 |

### Utilities Layer (~131 LOC - 5% of codebase)
Helper functions and platform-specific code:

| File | Purpose | LOC |
|------|---------|-----|
| `cookie_converter.py` | JSON to Netscape cookie format conversion | 85 |
| `platform_utils.py` | Config and download directory management | 29 |
| `tool_checker.py` | FFmpeg and aria2c detection | 17 |

### Entry Point (~61 LOC - 2% of codebase)
| File | Purpose | LOC |
|------|---------|-----|
| `app.py` | Application initialization and main event loop | 61 |

## Key Architectural Patterns

### Separation of Concerns
- UI components handle presentation only
- Core modules manage business logic
- Utilities provide cross-cutting functionality

### Threading Model
- Main thread: UI event loop
- Worker threads: Download execution (configurable pool)
- Queue-based communication between threads

### Configuration System
- JSON-based persistent storage
- Centralized defaults in `config_manager.py`
- 40+ configuration options supported

## Dependencies

### Core Dependencies (from pyproject.toml)
- `yt-dlp`: Video downloading engine
- `customtkinter>=5.2.2`: Modern UI framework
- `pycryptodomex`: AES-128 decryption support

### Optional Dependencies
- `yt-dlp[curl-cffi]`: Browser impersonation support

### External Tools
- FFmpeg: Media processing and format conversion
- aria2c: Optional external downloader for acceleration

## Code Quality Indicators

### Strengths
1. **Modular Structure**: Clear separation between UI, core, and utilities
2. **Type Hints**: Used throughout for better code clarity
3. **Error Handling**: Try-catch blocks with user-friendly messages
4. **Thread Safety**: Proper locking for shared state
5. **Configuration Management**: Comprehensive options with validation

### Areas for Improvement
1. **Testing**: No test suite currently implemented
2. **Documentation**: Could benefit from more inline documentation
3. **Logging**: Basic logging implemented, could be enhanced

## File Structure

```
src/ytdlp_gui/
├── app.py                    # Application entry point
├── core/
│   ├── __init__.py          # DownloadItem, DownloadStatus
│   ├── config_manager.py    # Configuration persistence
│   ├── downloader.py        # Download engine with yt-dlp
│   └── queue_manager.py     # Worker pool management
├── ui/
│   ├── __init__.py
│   ├── collapsible_section.py
│   ├── main_window.py
│   ├── queue_frame.py
│   ├── settings_panel.py
│   └── url_input_frame.py
└── utils/
    ├── __init__.py
    ├── cookie_converter.py
    ├── platform_utils.py
    └── tool_checker.py
```

## Scalability Considerations

The architecture supports future enhancements:
1. **Plugin Architecture**: UI sections use collapsible panels
2. **Download Backend**: Downloader class can be extended
3. **Configuration**: Easily extensible for new options
4. **Queue Management**: Configurable concurrent download limits
