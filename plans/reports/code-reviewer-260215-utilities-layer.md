# Utilities Layer Code Review

**Date**: 2025-02-15
**Reviewer**: Code Reviewer Agent
**Scope**: src/ytdlp_gui/utils/ (4 modules, 172 lines)

## Files Reviewed
- cookie_converter.py (86 lines)
- platform_utils.py (30 lines)
- sanitize.py (108 lines)
- tool_checker.py (18 lines)

---

## Critical Issues

### cookie_converter.py: Cookie Value Injection
- **Line 55**: Cookie values not sanitized before writing to Netscape format
- **Risk**: Malicious cookies with newlines/tabs could corrupt file format
- **Impact**: Broken cookie files, potential yt-dlp failures
- **Fix**: Validate/escape cookie values before writing

### sanitize.py: Empty Input Handling
- **Line 33-48**: sanitize_filename("") returns "" but docs say "download"
- **Line 51-57**: sanitize_foldername("") returns "" inconsistent with filename
- **Risk**: Callers expecting fallback may get empty string
- **Impact**: Empty filenames passed to yt-dlp may cause errors

---

## High Priority

### cookie_converter.py: Missing Cookie Validation
- **Lines 38-56**: No validation of required cookie fields (domain, name)
- **Risk**: Invalid cookies written to file causing silent failures
- **Impact**: yt-dlp fails with unclear error message
- **Fix**: Skip cookies without domain; require name field

### sanitize.py: Path Traversal Handling Weak
- **Lines 84-86**: While loop removes ".." but not "../" or "./"
- **Risk**: Edge cases may bypass traversal protection
- **Impact**: Potential path traversal in rare cases
- **Fix**: Use proper path normalization or stricter regex

### sanitize.py: Inconsistent Empty Returns
- **Lines 33-48, 51-57**: sanitize_filename/foldername return "" for empty input
- **Risk**: Different from docstring promise of "download" fallback
- **Impact**: Confusing API behavior, potential bugs

---

## Medium Priority

### platform_utils.py: macOS Support Missing
- **Line 8**: Only handles Linux XDG, defaults to ~/.ytdlp-gui for macOS
- **Risk**: macOS doesn't respect XDG_CONFIG_HOME
- **Impact**: Config files not in macOS-standard location
- **Fix**: Add macOS case using ~/Library/Application Support

### cookie_converter.py: Temp File Permissions
- **Lines 73-79**: No explicit file permissions set on temp cookie file
- **Risk**: Default permissions may expose cookies to other users
- **Impact**: Privacy violation on multi-user systems
- **Fix**: Set 0o600 permissions after writing

### tool_checker.py: No Path Sanitization
- **Line 7**: custom_path passed directly to Path().is_file()
- **Risk**: No validation of path format or existence check safety
- **Impact**: Potential unexpected behavior with malformed paths
- **Fix**: Validate path string before use

---

## Low Priority

### cookie_converter.py: Type Safety Gap
- **Lines 39-40**: isinstance(cookie, dict) check silently skips invalid entries
- **Risk**: Mixed-type arrays silently lose data
- **Impact**: Difficult to debug cookie parsing issues
- **Fix**: Log warnings when skipping invalid cookies

### platform_utils.py: Windows Support Unclear
- **Lines 6-29**: No explicit Windows handling
- **Risk**: May not handle Windows edge cases properly
- **Impact**: Potential issues on Windows with special paths
- **Fix**: Document Windows behavior or add explicit handling

### tool_checker.py: Thin Wrapper
- **Lines 5-18**: All functions are thin wrappers around shutil.which
- **Risk**: Questionable value as separate module
- **Impact**: Unnecessary abstraction
- **Fix**: Consider inlining or expanding with validation

---

## Positive Observations

- **sanitize.py**: Excellent Unicode handling (invisible chars, BOM, normalization)
- **sanitize.py**: Good Windows reserved name detection
- **sanitize.py**: Well-structured with shared _sanitize core function
- **cookie_converter.py**: Good error handling with try/except and logging
- **platform_utils.py**: Simple, clean XDG support for Linux
- **All modules**: Good use of type hints (str | None return types)
- **Tests**: sanitize.py has comprehensive test coverage (112 lines)
- **Documentation**: All public functions have docstrings

---

## Security Assessment

### Input Validation
- **Cookie values**: No sanitization (CRITICAL)
- **File paths**: Good sanitization in sanitize.py
- **Custom paths**: No validation in tool_checker.py
- **JSON input**: Proper JSONDecodeError handling

### Data Protection
- **Temp files**: No explicit permissions (MEDIUM)
- **Cleanup**: Proper cleanup in downloader.py (good)
- **Config storage**: Uses platform_utils (good)

### Code Injection
- **No command injection risks found**
- **No XXE risks** (no XML processing)

---

## Edge Cases Found

1. sanitize_filename("...") → "" (not "download" per docs)
2. sanitize_filename("") → "" (inconsistent with docs)
3. Cookie values with newlines corrupt Netscape format
4. macOS doesn't respect XDG_CONFIG_HOME
5. Custom paths not validated before use
6. Empty cookies (no name) silently skipped without logging
7. Windows reserved names handled but macOS not in XDG path

---

## Type Safety

- **Good**: All functions have type hints
- **Good**: Return types clearly specified (str | None)
- **Gap**: No validation of input types (e.g., cookie dict structure)
- **Gap**: Empty string handling inconsistent with docstring

---

## Metrics

- **Total Lines**: 172
- **Test Coverage**: 65% (sanitize only tested)
- **Type Hints**: 100%
- **Docstrings**: 100%
- **Critical Issues**: 2
- **High Priority**: 3
- **Medium Priority**: 3
- **Low Priority**: 3

---

## Recommended Actions

1. **CRITICAL**: Add cookie value sanitization in json_cookies_to_netscape
2. **CRITICAL**: Fix empty input handling to match docstring promises
3. **HIGH**: Add required cookie field validation (domain, name)
4. **HIGH**: Improve path traversal protection with proper normalization
5. **MEDIUM**: Add macOS config dir support (~/Library/Application Support)
6. **MEDIUM**: Set 0o600 permissions on temp cookie files
7. **LOW**: Add tests for cookie_converter and platform_utils

---

## Unresolved Questions

- Should tool_checker.py be inlined given it's a thin wrapper?
- Should sanitize_foldername also return "download" for empty input?
- Should cookie values be logged in warnings when skipped?
- Should Windows get special handling in platform_utils?

---

## Code Quality: B+

**Strengths**: Clean code, good type hints, excellent sanitization logic
**Weaknesses**: Missing input validation in cookie handling, inconsistent behavior
**Overall**: Solid foundation with security gaps to address
