# Codebase Review: yt-dlp GUI Downloader v0.1.0

**Date**: 2025-02-12 | **Reviewer**: Claude Code | **Total LOC**: ~2,100 across 12 source files

## Project Overview

Cross-platform GUI video downloader (CustomTkinter + yt-dlp). Architecture: `app.py` → `MainWindow` → `{URLInputFrame, QueueFrame, SettingsPanel}` backed by `{Downloader, QueueManager, ConfigManager}`.

**Tech**: Python 3.10+, customtkinter, yt-dlp, threading, queue

---

## Architecture Assessment

**Strengths**:
- Clean 3-layer separation: core / ui / utils
- Queue-based thread-to-UI messaging (safe)
- Poison-pill worker shutdown pattern
- Exception-based download cancellation (elegant yt-dlp integration)
- Scoped temp file cleanup via `_seen_temp_files`
- Atomic config writes with 0o600 permissions
- Debounced config saves (500ms)
- Reusable `CollapsibleSection` widget (44 lines, well-designed)

**Weaknesses**:
- Config is mutable dict passed by reference across threads (no locking)
- No tests (0% coverage)
- No logging infrastructure
- `settings_panel.py` at 669 lines (3.3x over 200-line guideline)

---

## Critical Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| C1 | Security | `downloader.py` | No path sanitization on `folder`/`filename` in `build_opts()`. Path traversal possible via `../../` |
| C2 | Security | `downloader.py:97-102` | Custom HTTP headers parsed without control char validation. CRLF injection possible |
| C3 | Security | `downloader.py:77-78` | Cookie file path not validated before passing to yt-dlp |
| C4 | Crash | `settings_panel.py:605` | Anti-block OFF toggle accesses `_pre_anti_block` before it's ever set → `TypeError` |
| C5 | Reliability | `queue_manager.py` | Unbounded `Queue()` — bulk URL paste could cause OOM |

## High Priority Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| H1 | Thread Safety | `queue_manager.py:126-141` | `update_config()` reads `_concurrent_limit` outside lock, race with worker spawn |
| H2 | Thread Safety | Config dict | Shared mutable dict read/written from multiple threads without synchronization |
| H3 | Memory | `main_window.py` | `_save_timer_id` not cancelled on destroy → callback fires on dead widget |
| H4 | Memory | `queue_frame.py` | `DownloadRow._item` reference never cleared after destroy |
| H5 | Validation | `settings_panel.py` | Numeric config values silently default on parse failure (user confusion) |
| H6 | Encapsulation | `queue_frame.py` | `getattr(row, "_current_status")` × 4 — fragile private attr access |
| H7 | File Size | `settings_panel.py` | 669 lines; should split into `ui/settings/` submodules |

## Medium Priority Issues

| # | Category | Location | Description |
|---|----------|----------|-------------|
| M1 | Shutdown | `app.py:39-43` | `on_closing()` doesn't wait for worker threads to finish |
| M2 | Dead Code | `url_input_frame.py:250-252` | `_get_nonempty_lines()` is unused |
| M3 | UX | `url_input_frame.py` | No URL scheme validation before queuing (only `http/https` should pass) |
| M4 | Logging | All | No `logging` calls anywhere; debugging production issues impossible |
| M5 | DRY | `url_input_frame.py` | `validate()` and `validate_detailed()` duplicate column-padding logic from `get_items()` |
| M6 | UI | `queue_frame.py:163` | Filename truncation uses string split instead of `Path` |

## Low/Info

- `.gitignore` lists `dist/` and `build/` but both dirs exist in repo
- `README.md` describes "AntiGravity IDE" (unrelated to this project)
- `GEMINI.md`, `HDSD_Vi.md`, `UI_UX_REDESIGN_SPEC.md` exist at root (project docs scattered)
- `build/` contains stale copy of source (should be gitignored)
- No `__main__.py` for `python -m ytdlp_gui` invocation
- `ensure_dirs_exist()` in `platform_utils.py` never called

---

## Recommended Fix Priority

### Immediate (before any release)
1. **C4**: Initialize `_pre_anti_block = None` in `__init__`, guard with `if prev:`
2. **C1-C3**: Add path/header sanitization in `Downloader.build_opts()`
3. **C5**: Set `maxsize` on job queue

### Short-term
4. **H1-H2**: Add threading.Lock around config access
5. **H3-H4**: Cancel timers on destroy, clear item refs
6. **H6**: Add `DownloadRow.status` property
7. **M2**: Remove dead code

### Medium-term
8. **H7**: Split `settings_panel.py` into section submodules
9. **M4**: Add structured logging
10. **M1**: Implement graceful shutdown with thread join timeout
11. Add unit tests for core modules

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Source Files | 12 |
| Total LOC | ~2,100 |
| Critical Issues | 5 |
| High Issues | 7 |
| Medium Issues | 6 |
| Test Coverage | 0% |
| Max File Size | 669 lines (settings_panel.py) |
| Architecture | Clean 3-layer (core/ui/utils) |
