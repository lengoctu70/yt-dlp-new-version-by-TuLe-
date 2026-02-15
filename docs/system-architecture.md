# System Architecture

## Overview

The yt-dlp Downloader GUI uses a layered architecture separating UI, business logic, and utilities. The design enables concurrent downloads while maintaining UI responsiveness through threading and queue-based communication.

## Architecture Layers

### 1. Presentation Layer (UI)
**Location**: `src/ytdlp_gui/ui/`

Handles all user interactions and visual elements using CustomTkinter.

#### Components
| Component | File | Responsibility |
|-----------|------|----------------|
| Main Window | `main_window.py` | Composes all UI sections, handles actions |
| Settings Panel | `settings_panel.py` | 5 collapsible sections for configuration |
| Queue Frame | `queue_frame.py` | Download queue with progress rows |
| URL Input | `url_input_frame.py` | 3-column bulk input interface |
| Collapsible Section | `collapsible_section.py` | Reusable toggleable container |

#### UI Patterns
- Event-driven architecture with callbacks
- Queue polling for thread-safe UI updates
- Debounced config saves (500ms)

### 2. Business Logic Layer (Core)
**Location**: `src/ytdlp_gui/core/`

Contains application logic and download management.

#### Components
| Component | File | Responsibility |
|-----------|------|----------------|
| Queue Manager | `queue_manager.py` | Worker pool, job scheduling |
| Downloader | `downloader.py` | yt-dlp integration, progress hooks |
| Config Manager | `config_manager.py` | Settings persistence |
| Data Models | `__init__.py` | DownloadItem, DownloadStatus |

#### Key Features
- Thread pool for concurrent downloads (1-5 workers)
- Cancellation via `threading.Event`
- Progress hooks sending messages to UI queue
- Config snapshot for thread safety

### 3. Application Entry Point
**Location**: `src/ytdlp_gui/app.py`

Initializes the application:
1. Configures logging
2. Loads configuration
3. Sets up CustomTkinter theme
4. Creates main window
5. Starts queue polling loop
6. Handles graceful shutdown

### 4. Utility Layer
**Location**: `src/ytdlp_gui/utils/`

Cross-cutting helper functions.

#### Components
| Component | File | Responsibility |
|-----------|------|----------------|
| Platform Utils | `platform_utils.py` | Config/download directories |
| Tool Checker | `tool_checker.py` | FFmpeg/aria2c detection |
| Cookie Converter | `cookie_converter.py` | JSON to Netscape format |

## Data Flow

### Download Process
```
User Input (URL Input Frame)
    |
    v
Validation (URL format, duplicates)
    |
    v
Add to Queue (Queue Manager)
    |
    v
Worker Thread Pool
    |
    v
Downloader (yt-dlp with progress hooks)
    |
    v
UI Queue <- Progress messages
    |
    v
Queue Frame (update progress bars)
```

### Configuration Flow
```
Load Config (config_manager.load_config)
    |
    v
Apply to UI (settings_panel.set_values)
    |
    v
User Changes Setting
    |
    v
Debounced Save (500ms) -> config_manager.save_config
```

## Threading Model

### Main Thread
- UI event loop (CustomTkinter)
- Queue polling (every 100ms)
- Configuration saves

### Worker Threads
- Download execution (yt-dlp)
- Configurable pool size (1-5 threads)
- Check cancellation event periodically

### Communication
- `queue.Queue` for UI updates from workers
- `threading.Event` for cancellation signals
- `threading.Lock` for shared state (active downloads)

## Key Design Patterns

### Observer Pattern
- UI polls message queue for updates
- Progress hooks send messages on state changes

### Factory Pattern
- DownloadItem creation with auto-generated UUID
- Config snapshot copies for thread safety

### Template Method
- Downloader class with configurable options building
- Sub-methods for each config category

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| UI Framework | CustomTkinter 5.2+ |
| Download Engine | yt-dlp |
| Media Processing | FFmpeg |
| External Downloader | aria2c (optional) |
| Configuration | JSON |
| Threading | Standard library (threading, queue) |

## Integration Points

### External Dependencies
- **yt-dlp**: Python API for video downloading
- **FFmpeg**: Post-processing via yt-dlp options
- **aria2c**: External downloader for segmented files

### Internal Communication
- Message types: `progress`, `progress_no_total`, `status`, `indeterminate`, `log`
- Shared config dict (copied per download for thread safety)
- QueueManager maintains active download tracking

## Security Considerations

- URL validation before processing
- Path sanitization for filenames
- Cookie temp files cleaned after use
- Config file permissions: user-only (0o600)
- Proxy URL format validation

## Performance Considerations

- Threading prevents UI blocking during downloads
- Lazy loading of tool paths (FFmpeg, aria2c)
- Efficient temp file cleanup (scoped to download)
- Debounced config saves reduce disk I/O
