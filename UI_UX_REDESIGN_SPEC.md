# UI/UX Redesign Spec - yt-dlp Downloader

## 1. Goals
- Reduce cognitive load for power features.
- Speed up batch workflow: paste URLs -> configure -> run -> retry failed.
- Improve observability for long-running downloads.

## 2. Information Architecture
- Main screen uses 2-pane layout:
- Left pane (60%): Queue + controls + summary.
- Right pane (40%): Input + Settings.

## 3. Main Layout
- Top bar:
- App title, theme toggle, quick profile selector (`Fast`, `Balanced`, `Safe`, `Audio`).
- Left pane blocks:
- `Queue Summary` (counts + throughput).
- `Queue List` (rows with status/actions).
- `Global Actions` (`Download All`, `Pause All`, `Cancel All`, `Clear Completed`, `Load Failed`).
- Right pane blocks:
- `Bulk Input` (folders/filenames/urls).
- `Validation Panel` (error/warning count + jump to line).
- `Settings Tabs` (`Basic`, `Advanced`, `Network`).

## 4. Settings Model
- `Basic`
- Default folder, quality preset, audio extract/format, subtitles.
- `Advanced`
- Format string, retries, fragment retries, rate limit, concurrent limit.
- `Network`
- Cookies mode, proxy, user-agent, referer, custom headers, impersonate.
- Rule:
- Only show advanced fields if user enables `Expert mode`.

## 5. Queue Row Spec
- Row content:
- Primary text: resolved filename (fallback URL/domain).
- Secondary text: output folder + source site.
- Progress line:
- Progress bar + percent + speed + ETA + downloaded size.
- Status chips:
- `Pending`, `Downloading`, `Post-processing`, `Completed`, `Failed`, `Cancelled`.
- Row actions:
- While running: `Cancel`.
- Failed: `Retry`, `Copy Error`.
- Completed: `Open Folder`.

## 6. Validation UX
- Validate by line index (1-based).
- Inline line markers:
- Error: invalid URL.
- Warning: duplicate URL, duplicate filename, filename sanitized, folder/filename without URL.
- Summary box:
- `X errors`, `Y warnings`, with `Next issue` button.
- `Download All` disabled when errors exist; warnings allowed.

## 7. Preset Profiles
- `Fast`
- Concurrent=4, retries=2, anti-block off.
- `Balanced`
- Concurrent=2, retries=3, moderate sleep.
- `Safe`
- Concurrent=1, retries=5, anti-block on.
- `Audio`
- Audio extract on, default audio format `mp3`.
- Behavior:
- Preset applies defaults but user can override fields afterward.

## 8. Empty/First-Run Experience
- First-run modal:
- Step 1: choose default folder.
- Step 2: choose profile.
- Step 3: paste first URL.
- Empty queue state:
- Message + 2 CTAs: `Paste URLs`, `Load Failed`.

## 9. Visual System
- Spacing scale: 4/8/12/16/24.
- Radius: 8 for cards, 6 for row blocks.
- Color roles:
- `Success` green, `Error` red, `Warning` amber, `Info` neutral blue/gray.
- Typography:
- Title 18 bold, section 14 bold, body 12, meta 11.

## 10. Interaction Rules
- Save settings debounced (500ms) and show `Saved` hint.
- For destructive actions (`Cancel All`, `Clear All`), show confirm dialog.
- After `Load Failed`, only failed rows are removed from queue list.
- Keyboard shortcuts:
- `Cmd/Ctrl+Enter`: Download All.
- `Cmd/Ctrl+L`: focus URL box.
- `Cmd/Ctrl+K`: clear completed.

## 11. Implementation Plan
1. Sprint 1 (foundation)
- 2-pane layout.
- Queue summary + improved row actions.
- Settings tabs (`Basic/Advanced/Network`).
2. Sprint 2 (usability)
- Inline validation and issue navigator.
- Preset profile system.
- First-run onboarding + empty state polish.
3. Sprint 3 (quality)
- Keyboard shortcuts.
- Confirm dialogs and micro-copy cleanup.
- Performance pass for large queues (100+ rows).

## 12. Acceptance Criteria
- User can complete first download in <= 3 actions on first run.
- Error recovery flow (`Failed -> Retry`) takes <= 2 clicks.
- No full-page scrolling needed for normal batch workflow.
- Queue state remains visible while editing settings.
