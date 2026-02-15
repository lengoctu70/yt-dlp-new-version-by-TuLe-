# Code Review Summary

**Project**: yt-dlp GUI Downloader
**Reviewer**: code-reviewer agent
**Date**: 2026-02-12
**Review ID**: code-reviewer-260212-1103-core-architecture-review

## Scope

- **Files Reviewed**: 7 core modules
  - `src/ytdlp_gui/app.py` (49 LOC)
  - `src/ytdlp_gui/core/__init__.py` (22 LOC)
  - `src/ytdlp_gui/core/downloader.py` (315 LOC)
  - `src/ytdlp_gui/core/queue_manager.py` (141 LOC)
  - `src/ytdlp_gui/core/config_manager.py` (77 LOC)
  - `src/ytdlp_gui/utils/tool_checker.py` (18 LOC)
  - `src/ytdlp_gui/utils/platform_utils.py` (22 LOC)
- **Total LOC**: ~644 core lines (2110 total in src/)
- **Focus**: Architecture, thread safety, security, error handling, code quality
- **Scout Findings**: Skipped (edge case analysis not requested in this review)

## Overall Assessment

**Architecture Quality**: Good
**Thread Safety**: Good with minor concerns
**Security Posture**: Medium-High risk
**Error Handling**: Adequate but incomplete
**Code Maintainability**: Good

The codebase demonstrates solid threading patterns with poison-pill shutdown, clean exception-based cancellation, and scoped cleanup. However, critical security vulnerabilities exist in config validation, input sanitization, and path handling. Performance and reliability issues stem from unbounded queues and missing validation.

---

## Critical Issues

### 1. Path Traversal Vulnerability (SECURITY)
**File**: `downloader.py:31-42`, `queue_manager.py:84`
**Severity**: CRITICAL

**Problem**: User-supplied `folder` and `filename` parameters are used directly in filesystem operations without sanitization. Malicious inputs like `../../../etc/passwd` or absolute paths can write files anywhere on the filesystem.

```python
# VULNERABLE: downloader.py line 37
outtmpl = str(Path(folder) / filename)
# user provides: folder="/tmp", filename="../../../etc/evil"
# Result: writes to /etc/evil
```

**Impact**: Arbitrary file write vulnerability, potential system compromise

**Fix**:
```python
def _sanitize_path_component(path_str: str) -> str:
    """Remove path traversal attempts and dangerous characters."""
    # Remove null bytes, path separators, and parent references
    safe = path_str.replace('\0', '').replace('..', '')
    safe = Path(safe).name  # Extract filename only
    if not safe or safe.startswith('.'):
        raise ValueError(f"Invalid filename: {path_str}")
    return safe

def build_opts(self, folder: str, filename: str) -> dict:
    # Validate folder is absolute and normalized
    folder_path = Path(folder).resolve()
    if not folder_path.is_absolute():
        raise ValueError("Folder must be absolute path")

    # Sanitize filename to prevent traversal
    if filename:
        safe_name = _sanitize_path_component(filename)
        outtmpl = str(folder_path / safe_name)
        # ... rest of logic
```

---

### 2. Command Injection via Custom Headers (SECURITY)
**File**: `downloader.py:97-102`
**Severity**: CRITICAL

**Problem**: Custom HTTP headers are parsed from user input without validation. Malicious newline injection (`\r\n\r\n`) can inject arbitrary HTTP headers or payloads.

```python
# VULNERABLE: Line 99-102
for line in custom_headers.strip().splitlines():
    if ":" in line:
        key, val = line.split(":", 1)
        http_headers[key.strip()] = val.strip()
```

**Attack Vector**:
```
Referer: safe.com\r\nX-Evil: malicious\r\n\r\nHTTP/1.1 200 OK
```

**Impact**: HTTP request smuggling, session hijacking, cache poisoning

**Fix**:
```python
# Validate and sanitize headers
for line in custom_headers.strip().splitlines():
    line = line.strip()
    if not line or ":" not in line:
        continue

    key, val = line.split(":", 1)
    key = key.strip()
    val = val.strip()

    # Reject headers with control characters or dangerous patterns
    if any(c in key + val for c in '\r\n\0'):
        logging.warning(f"Skipping dangerous header: {key}")
        continue

    # Validate key is valid HTTP header name (alphanumeric + dash)
    if not re.match(r'^[A-Za-z0-9-]+$', key):
        logging.warning(f"Invalid header name: {key}")
        continue

    http_headers[key] = val
```

---

### 3. Cookie File Path Traversal (SECURITY)
**File**: `downloader.py:75-78`
**Severity**: HIGH

**Problem**: Cookie file path from config is used directly without validation. Can read arbitrary files via traversal.

```python
# VULNERABLE: Line 77-78
cookie_file = cfg.get("cookie_file", "")
if cookie_file:
    opts["cookiefile"] = cookie_file
```

**Impact**: Arbitrary file read, potential credential exposure

**Fix**:
```python
if cookie_mode == "file":
    cookie_file = cfg.get("cookie_file", "")
    if cookie_file:
        # Validate file exists and is readable
        cookie_path = Path(cookie_file).resolve()
        if not cookie_path.exists():
            logging.warning(f"Cookie file not found: {cookie_file}")
        elif not cookie_path.is_file():
            logging.warning(f"Cookie path is not a file: {cookie_file}")
        else:
            # Optionally: restrict to config directory or user home
            opts["cookiefile"] = str(cookie_path)
```

---

### 4. Unbounded Queue Memory Exhaustion (RELIABILITY)
**File**: `queue_manager.py:15`, `app.py:20`
**Severity**: HIGH

**Problem**: `Queue()` and `queue.Queue()` are unbounded. A malicious or accidental bulk paste of 100K URLs will consume all memory before workers can process them.

```python
# VULNERABLE: queue_manager.py line 15
self._job_queue: queue.Queue[DownloadItem | object] = queue.Queue()
# User adds 1 million items -> OOM crash
```

**Impact**: Denial of service, application crash

**Fix**:
```python
# Bound queue to reasonable limit
MAX_QUEUE_SIZE = 10000

class QueueManager:
    def __init__(self, config: dict, ui_queue: queue.Queue):
        # ... existing init
        self._job_queue: queue.Queue[DownloadItem | object] = queue.Queue(maxsize=MAX_QUEUE_SIZE)

    def add_items(self, items: list[DownloadItem]) -> None:
        """Queue items with overflow protection."""
        queued = 0
        failed = 0
        for item in items:
            try:
                # Use put_nowait to avoid blocking UI thread
                self._job_queue.put_nowait(item)
                queued += 1
            except queue.Full:
                failed += 1
                self._ui_queue.put({
                    "type": "error",
                    "message": f"Queue full, dropped {failed} items"
                })
                break

        if failed > 0:
            logging.warning(f"Queue overflow: {failed}/{len(items)} items dropped")
```

---

## High Priority

### 5. Missing Input Validation on Numeric Config (RELIABILITY)
**File**: `downloader.py:48,64,106-109,118,139-150`
**Severity**: HIGH

**Problem**: Numeric config values (`retries`, `aria2c_connections`, `rate_limit`, `audio_quality`, `sleep_*`, `fragment_retries`) are used directly without type/range validation. Invalid values cause runtime errors or unexpected behavior.

```python
# VULNERABLE: Line 48, 64, 108
opts["retries"] = cfg.get("retries", 3)  # What if "abc" or -1?
connections = cfg.get("aria2c_connections", 16)  # What if 999999?
opts["ratelimit"] = rate_limit * 1024  # What if float overflow?
```

**Impact**: Application crash, DoS via excessive connections, yt-dlp errors

**Fix**:
```python
def _validate_int(value: Any, default: int, min_val: int = 0, max_val: int = 2**31-1) -> int:
    """Safely cast to int with bounds checking."""
    try:
        result = int(value)
        return max(min_val, min(max_val, result))
    except (ValueError, TypeError):
        return default

def build_opts(self, folder: str, filename: str) -> dict:
    cfg = self._config

    opts = {
        "retries": _validate_int(cfg.get("retries", 3), default=3, min_val=0, max_val=100),
        # ... rest
    }

    # Aria2c with bounds
    if cfg.get("aria2c_enabled"):
        connections = _validate_int(cfg.get("aria2c_connections", 16), default=16, min_val=1, max_val=32)
        # ...

    # Rate limit with overflow protection
    rate_limit = _validate_int(cfg.get("rate_limit", 0), default=0, min_val=0, max_val=100000)
    if rate_limit > 0:
        opts["ratelimit"] = rate_limit * 1024
```

---

### 6. Race Condition in Worker Scaling (CONCURRENCY)
**File**: `queue_manager.py:125-141`
**Severity**: HIGH

**Problem**: `update_config()` modifies `_concurrent_limit` and spawns/stops workers without proper synchronization. Race conditions can occur if called during active downloads.

```python
# PROBLEMATIC: Lines 132-140
with self._lock:
    old_limit = self._concurrent_limit
    self._concurrent_limit = new_limit  # Updated inside lock

if new_limit > old_limit:
    self._start_workers(new_limit - old_limit)  # Workers start OUTSIDE lock
elif new_limit < old_limit:
    for _ in range(old_limit - new_limit):
        self._job_queue.put(self._stop_token)  # Queue writes OUTSIDE lock
```

**Issue**: New workers read `_concurrent_limit` without lock protection. Stop tokens may be processed by new workers instead of old ones.

**Fix**:
```python
def update_config(self, config: dict) -> None:
    """Update config for future downloads."""
    new_limit = config.get("concurrent_limit", 3)

    with self._lock:
        self._config = config
        old_limit = self._concurrent_limit

        if new_limit == old_limit:
            return

        self._concurrent_limit = new_limit

        if new_limit > old_limit:
            # Spawn workers inside lock to ensure consistent state
            for _ in range(new_limit - old_limit):
                worker = threading.Thread(target=self._worker_loop, daemon=True)
                worker.start()
                self._workers.append(worker)
        elif new_limit < old_limit:
            # Send stop tokens (queue is thread-safe)
            for _ in range(old_limit - new_limit):
                self._job_queue.put(self._stop_token)
```

---

### 7. Missing Error Handling for Directory Creation (RELIABILITY)
**File**: `downloader.py:252`, `platform_utils.py:7,13`
**Severity**: HIGH

**Problem**: `os.makedirs()` and `Path.mkdir()` can fail (permissions, disk full, read-only filesystem) but exceptions are not caught. This causes silent failures or crashes.

```python
# VULNERABLE: downloader.py line 252
os.makedirs(folder, exist_ok=True)  # Can raise OSError, PermissionError
```

**Impact**: Download failure without user notification, data loss

**Fix**:
```python
def download(self, url: str, folder: str, filename: str) -> None:
    """Run download (blocking). Call from worker thread only."""
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as e:
        self._ui_queue.put({
            "type": "status",
            "id": self._download_id,
            "status": "failed",
            "error": f"Cannot create download folder: {e}",
        })
        return

    # ... rest of download logic
```

**Apply similar pattern to `platform_utils.py`**:
```python
def get_config_dir() -> Path:
    """Return ~/.ytdlp-gui, creating it if missing."""
    config_dir = Path.home() / ".ytdlp-gui"
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.error(f"Cannot create config directory: {e}")
        # Fallback to temp directory
        import tempfile
        config_dir = Path(tempfile.gettempdir()) / ".ytdlp-gui"
        config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
```

---

### 8. Lack of URL Validation (SECURITY)
**File**: `downloader.py:258`
**Severity**: MEDIUM-HIGH

**Problem**: URLs are passed directly to yt-dlp without validation. Malicious inputs like `file:///etc/passwd` or `javascript:alert(1)` may be exploited.

**Impact**: Local file access, protocol handler abuse (depends on yt-dlp internals)

**Fix**:
```python
import urllib.parse

def _validate_url(url: str) -> None:
    """Validate URL scheme and format."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Whitelist allowed schemes
    if parsed.scheme not in ('http', 'https', 'ftp', 'ftps'):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    # Reject local file access
    if parsed.scheme == 'file':
        raise ValueError("Local file URLs are not allowed")

def download(self, url: str, folder: str, filename: str) -> None:
    try:
        _validate_url(url)
        os.makedirs(folder, exist_ok=True)
        # ... rest
```

---

## Medium Priority

### 9. Config Dict Mutation Without Locks (CONCURRENCY)
**File**: `queue_manager.py:127`, `app.py:11,23`
**Severity**: MEDIUM

**Problem**: Config dict is shared by reference across threads (main, workers) and mutated without synchronization. Worker threads reading `self._config` during UI updates can see partial/inconsistent state.

```python
# RACE CONDITION:
# Thread 1 (worker): connections = cfg.get("aria2c_connections", 16)
# Thread 2 (main UI): config["aria2c_connections"] = 32  # dict.update()
# Result: worker may read 16 or 32 mid-update
```

**Impact**: Non-deterministic behavior, potential crash if dict is resized during iteration

**Fix (Option A - Immutable Config)**:
```python
# In queue_manager.py
def update_config(self, config: dict) -> None:
    """Update config for future downloads."""
    # Create immutable copy
    with self._lock:
        self._config = dict(config)  # Shallow copy sufficient for primitives
        # ... rest of logic
```

**Fix (Option B - Config Manager with Lock)**:
```python
# In config_manager.py
class ConfigManager:
    def __init__(self, config: dict):
        self._config = config
        self._lock = threading.RLock()

    def get(self, key: str, default=None):
        with self._lock:
            return self._config.get(key, default)

    def update(self, updates: dict) -> None:
        with self._lock:
            self._config.update(updates)

    def snapshot(self) -> dict:
        """Return thread-safe copy."""
        with self._lock:
            return dict(self._config)
```

---

### 10. Graceful Shutdown Incomplete (RELIABILITY)
**File**: `app.py:39-44`
**Severity**: MEDIUM

**Problem**: `on_closing()` calls `cancel_all()` but does not wait for worker threads to finish. Daemon threads are killed immediately on exit, potentially corrupting partial downloads or leaving temp files.

```python
# PROBLEMATIC: app.py lines 39-44
def on_closing():
    queue_manager.cancel_all()
    main_window.flush_config_from_ui()
    app.destroy()  # Exits immediately, daemon threads killed
```

**Impact**: Data corruption, orphaned .part files, incomplete cleanup

**Fix**:
```python
def on_closing():
    # Signal cancellation
    queue_manager.cancel_all()

    # Show shutdown dialog
    shutdown_dialog = ctk.CTkToplevel(app)
    shutdown_dialog.title("Shutting down...")
    label = ctk.CTkLabel(shutdown_dialog, text="Waiting for downloads to cancel...")
    label.pack(padx=20, pady=20)

    # Wait for workers with timeout
    def wait_and_close():
        deadline = time.time() + 5.0  # 5 second timeout
        while time.time() < deadline:
            if queue_manager.all_workers_idle():
                break
            time.sleep(0.1)

        # Force shutdown after timeout
        main_window.flush_config_from_ui()
        shutdown_dialog.destroy()
        app.destroy()

    threading.Thread(target=wait_and_close, daemon=True).start()
```

**Add to QueueManager**:
```python
def all_workers_idle(self) -> bool:
    """Check if all workers finished processing."""
    with self._lock:
        return len(self._active) == 0 and self._job_queue.empty()
```

---

### 11. Missing Timeout on UI Queue Polling (RELIABILITY)
**File**: `app.py:27-34`
**Severity**: MEDIUM

**Problem**: `ui_queue.get_nowait()` processes unbounded messages in a single tick. If workers flood the queue (e.g., 1000 progress updates/sec), the UI freezes.

```python
# VULNERABLE: Lines 29-31
while True:
    msg = ui_queue.get_nowait()
    main_window.handle_queue_message(msg)
```

**Impact**: UI unresponsiveness, poor UX

**Fix**:
```python
def poll_queue():
    MAX_MESSAGES_PER_TICK = 50  # Process at most 50 messages per 100ms
    processed = 0

    try:
        while processed < MAX_MESSAGES_PER_TICK:
            msg = ui_queue.get_nowait()
            main_window.handle_queue_message(msg)
            processed += 1
    except queue.Empty:
        pass

    # Log if queue is backing up
    if ui_queue.qsize() > 100:
        logging.warning(f"UI queue backlog: {ui_queue.qsize()} messages")

    app.after(100, poll_queue)
```

---

### 12. Cleanup Glob Pattern Too Broad (RELIABILITY)
**File**: `downloader.py:310-312`
**Severity**: MEDIUM

**Problem**: Fallback cleanup uses overly broad glob patterns (`f"{base_name}*.part*"`). If `filename="video"`, it will delete `video-other.part` from concurrent downloads.

```python
# DANGEROUS: Lines 310-312
for pattern in (f"{base_name}*.part*", f"{base_name}*.ytdl"):
    for junk_file in folder_path.glob(pattern):
        junk_file.unlink(missing_ok=True)
# Deletes "video-123.part" when canceling "video.mp4"
```

**Impact**: Data loss from concurrent downloads in same folder

**Fix**:
```python
def _cleanup_part_files(self, folder: str, filename: str) -> None:
    """Delete only this download's temp files left by cancellation."""
    try:
        folder_path = Path(folder)

        # Primary: use tracked files from yt-dlp hooks
        for path in self._seen_temp_files:
            candidate = path if path.is_absolute() else (folder_path / path)
            if candidate.parent != folder_path:
                continue
            if ".part" in candidate.name or candidate.suffix == ".ytdl":
                candidate.unlink(missing_ok=True)

        # Fallback: only exact matches for custom filename
        if filename:
            base_name = Path(filename).stem or filename
            # Use exact pattern match, not prefix wildcard
            for suffix in ('.part', '.ytdl', '.part.ytdl'):
                exact_file = folder_path / f"{base_name}{suffix}"
                exact_file.unlink(missing_ok=True)
    except OSError:
        pass
```

---

### 13. Logging Configuration Missing (OBSERVABILITY)
**File**: All modules
**Severity**: MEDIUM

**Problem**: No logging configuration in `app.py`. Warnings in `config_manager.py:76` and potential errors elsewhere are silently dropped.

**Impact**: Difficult debugging, no audit trail

**Fix**:
```python
# In app.py
import logging

def main():
    # Configure logging before anything else
    log_dir = Path.home() / ".ytdlp-gui" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "ytdlp-gui.log"),
            logging.StreamHandler()  # Also print to console
        ]
    )

    config = load_config()
    # ... rest
```

---

## Low Priority

### 14. Magic Numbers and Hardcoded Defaults (MAINTAINABILITY)
**File**: `app.py:17,34`, `downloader.py:67-68,106,109`
**Severity**: LOW

**Problem**: Hardcoded values like `900x700`, `100ms`, `-k1M`, `1024` scattered throughout code.

**Fix**: Extract to named constants at module level:
```python
# app.py
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 700
UI_POLL_INTERVAL_MS = 100

# downloader.py
ARIA2C_MIN_SPLIT_SIZE = "1M"
KB_TO_BYTES = 1024
DEFAULT_RETRIES = 3
```

---

### 15. Type Hints Incomplete (MAINTAINABILITY)
**File**: `downloader.py:154,235`, `queue_manager.py:35`
**Severity**: LOW

**Problem**: Some functions lack return type hints (e.g., `_progress_hook`, `_postprocessor_hook`, `_worker_loop`).

**Fix**: Add explicit `-> None` annotations:
```python
def _progress_hook(self, d: dict) -> None:
    """Called by yt-dlp with download progress."""
    # ...

def _worker_loop(self) -> None:
    # ...
```

---

### 16. Docstring Inconsistencies (MAINTAINABILITY)
**File**: All modules
**Severity**: LOW

**Problem**: Some functions have detailed docstrings, others have none. Mix of Google-style and sentence-style.

**Recommendation**: Adopt consistent docstring format (suggest Google-style):
```python
def build_opts(self, folder: str, filename: str) -> dict:
    """Build yt-dlp options dict from config.

    Args:
        folder: Absolute path to download directory
        filename: Output filename (optional, uses video title if empty)

    Returns:
        yt-dlp options dict ready for YoutubeDL()

    Raises:
        ValueError: If folder path is invalid
    """
```

---

## Positive Observations

1. **Clean Threading Model**: Poison-pill pattern for worker shutdown is textbook correct
2. **Scoped Cleanup**: `_seen_temp_files` tracking prevents cross-download interference
3. **Exception-Based Cancellation**: `DownloadCancelled` is elegant and works within yt-dlp's callback model
4. **Config Separation**: Utils, core, and UI are well-separated
5. **Atomic File Writes**: `save_config()` uses proper encoding and restrictive permissions (0o600)
6. **Defensive Coding**: `task_done()` always called in `finally` blocks
7. **UI Responsiveness**: Async progress updates via queue prevent blocking

---

## Recommended Actions (Priority Order)

1. **IMMEDIATE (Critical Security)**:
   - Add path traversal validation to `folder`/`filename` parameters
   - Sanitize custom HTTP headers to prevent injection
   - Validate cookie file paths before passing to yt-dlp
   - Add URL scheme whitelist

2. **SHORT-TERM (High Reliability)**:
   - Bound `_job_queue` to prevent OOM (max 10K items)
   - Add numeric config validation with range checks
   - Fix worker scaling race condition in `update_config()`
   - Add error handling for directory creation failures

3. **MEDIUM-TERM (Stability)**:
   - Implement thread-safe config access (immutable snapshots)
   - Add graceful shutdown with worker join timeout
   - Rate-limit UI queue processing (max 50 msgs/tick)
   - Narrow cleanup glob patterns to exact matches
   - Configure structured logging with rotation

4. **LONG-TERM (Quality)**:
   - Extract magic numbers to named constants
   - Complete type hints across all modules
   - Standardize docstring format
   - Add unit tests for threading logic and edge cases

---

## Metrics

- **Type Coverage**: ~80% (missing in some helper functions)
- **Test Coverage**: 0% (no tests found in repo)
- **Linting Issues**: Not run (recommend `ruff` or `pylint`)
- **Security Scan**: Not run (recommend `bandit`)

---

## Unresolved Questions

1. **UI Module Review**: Should `main_window.py`, `settings_panel.py`, and `queue_frame.py` be reviewed for similar issues?
2. **Test Strategy**: Are integration tests planned for thread safety and cancellation flows?
3. **Dependency Pinning**: Are `yt-dlp` and `customtkinter` versions locked in requirements.txt?
4. **Anti-Block Testing**: Have sleep intervals and rate limits been validated against real websites?
5. **Error Recovery**: Should failed downloads support retry/resume from UI?

---

## References

- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- HTTP Request Smuggling: https://portswigger.net/web-security/request-smuggling
- Python Threading Best Practices: https://docs.python.org/3/library/threading.html
- yt-dlp API Docs: https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp
