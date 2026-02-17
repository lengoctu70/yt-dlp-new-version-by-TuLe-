# Code Standards

## Project Structure

```
src/ytdlp_gui/
├── app.py                    # Application entry point
├── core/                     # Business logic
│   ├── __init__.py          # DownloadItem, DownloadStatus
│   ├── config_manager.py    # Configuration persistence
│   ├── downloader.py        # yt-dlp download engine
│   └── queue_manager.py     # Concurrent download workers
├── ui/                       # User interface
│   ├── __init__.py
│   ├── collapsible_section.py
│   ├── main_window.py
│   ├── queue_frame.py
│   ├── settings_panel.py
│   └── url_input_frame.py
└── utils/                    # Helper utilities
    ├── __init__.py
    ├── cookie_converter.py
    ├── platform_utils.py
    └── tool_checker.py
```

## Code Style Guidelines

### Python Standards
- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use f-strings for string formatting

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `MainWindow`, `QueueManager` |
| Functions/Methods | snake_case | `get_video_info()`, `update_progress()` |
| Variables | snake_case | `download_path`, `queue_item` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_FORMAT`, `SOCKET_TIMEOUT` |
| Private members | Leading underscore | `_validate_url()`, `_config_data` |

### Documentation Standards
- All public classes and functions have docstrings
- Google-style docstring format
- Type hints on function signatures
- Complex logic has inline comments

```python
def download_video(url: str, output_path: str, quality: str) -> bool:
    """Download video with specified quality.

    Args:
        url: Video URL to download
        output_path: Directory to save file
        quality: Quality selector string

    Returns:
        True if download successful, False otherwise
    """
```

## Module Organization

### Core Modules
| Module | Responsibility |
|--------|----------------|
| `config_manager.py` | Configuration persistence, defaults, loading |
| `downloader.py` | yt-dlp integration, progress hooks, cancellation |
| `queue_manager.py` | Worker pool, concurrent download management |

### UI Modules
| Module | Responsibility |
|--------|----------------|
| `main_window.py` | Window composition, event handling |
| `settings_panel.py` | 5 collapsible settings sections |
| `queue_frame.py` | Download rows with progress display |
| `url_input_frame.py` | 3-column bulk input interface |
| `collapsible_section.py` | Reusable collapsible container |

### Utility Modules
| Module | Responsibility |
|--------|----------------|
| `sanitize.py` | 12-step filename sanitization pipeline |
| `platform_utils.py` | Config/download directories, XDG support |
| `tool_checker.py` | FFmpeg and aria2c detection |
| `cookie_converter.py` | JSON to Netscape format conversion |

## Error Handling Standards

### Exception Handling
- Use specific exception types
- Log errors with context
- Provide user-friendly UI messages

```python
try:
    info = downloader.get_video_info(url)
except yt_dlp.utils.DownloadError as e:
    logger.error(f"Download error: {e}")
    # UI notification via queue
```

### Logging
- Use Python's `logging` module
- Include module name in logger
- Log levels: DEBUG for verbose, INFO for operations, ERROR for failures

```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Starting download: {url}")
logger.error(f"Download failed: {e}")
```

## Threading Standards

### Thread Safety
- Use `threading.Event` for cancellation signals
- Use `threading.Lock` for shared state access
- Queue-based communication between threads
- Never update UI directly from worker threads

```python
# Worker thread sends message via queue
self._ui_queue.put({
    "type": "progress",
    "id": download_id,
    "percent": percent,
})

# Main thread polls and updates UI
def poll_queue():
    try:
        while True:
            msg = ui_queue.get_nowait()
            main_window.handle_queue_message(msg)
    except queue.Empty:
        pass
    app.after(100, poll_queue)
```

## Configuration Standards

### Config Keys
- Use snake_case for all config keys
- Provide sensible defaults in `DEFAULT_CONFIG`
- Validate user input before saving
- Set file permissions to user-only (0o600)

## Testing Standards

### Unit Testing
- Use pytest framework
- Mock external dependencies
- Test both success and failure cases
- Current test coverage: `test_sanitize.py` (22 test methods covering filename sanitization)

```python
# Example from test_sanitize.py
import pytest
from ytdlp_gui.utils.sanitize import sanitize_filename

def test_sanitize_removes_invalid_chars():
    """Test that invalid characters are properly removed."""
    assert sanitize_filename("file<>name") == "filename"
    assert sanitize_filename("path/to/file") == "pathtofile"
```

### Test Execution
```bash
pytest tests/
pytest tests/test_sanitize.py -v  # Verbose output
```

## Version Management

- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update version in `src/ytdlp_gui/__init__.py`
- Update version in `pyproject.toml`
- Tag releases in git

## Security Considerations

### Input Validation
- Validate URLs before processing
- Sanitize file paths
- Validate proxy URL format

### Data Protection
- Config file: user-only permissions (0o600)
- Cookies: temporary files cleaned after use
- No passwords stored in plain text
