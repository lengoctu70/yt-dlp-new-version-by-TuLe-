# Windows 1-Click Setup

## Cách chạy
- Double-click: `scripts/windows/one_click_setup.bat`
- Hoặc mở PowerShell:
  ```powershell
  Set-ExecutionPolicy Bypass -Scope Process
  .\scripts\windows\setup_windows_one_click.ps1
  ```

## Script tự động làm những gì?

### 1. Kiểm tra & Cài đặt Python
- Kiểm tra Python 3.10+ có sẵn trong hệ thống
- Nếu chưa có → **tự động tải và cài Python 3.12** từ python.org
- Thêm Python vào PATH tự động

### 2. Tải các công cụ mới nhất
Tất cả công cụ được tải về và đặt chung vào `%USERPROFILE%\.ytdlp-gui\tools\bin\`:
- **yt-dlp.exe** — Engine tải video
- **ffmpeg.exe** + **ffprobe.exe** — Xử lý/chuyển đổi video/audio
- **aria2c.exe** — Tăng tốc tải file (hỗ trợ đa kết nối)

### 3. Cài đặt Python packages
- `yt-dlp` — Thư viện Python cho yt-dlp
- `pycryptodomex` — Giải mã AES-128 (cần cho HLS streams mã hóa)
- `customtkinter` — Thư viện giao diện
- `setuptools` — Build tools
- `curl-cffi` *(tùy chọn)* — Giả lập trình duyệt để chống block

### 4. Cấu hình ứng dụng
- Ghi đường dẫn tools vào `~/.ytdlp-gui/config.json`:
  - `ffmpeg_path`
  - `aria2c_path`
  - `aria2c_enabled = true`

### 5. Cập nhật PATH
- Thêm thư mục tools vào User PATH:
  - `%USERPROFILE%\.ytdlp-gui\tools\bin`

## Lưu ý
- Chạy script bằng user thường (không cần quyền Admin)
- Cần kết nối Internet
- Nếu PATH được cập nhật, hãy **mở lại terminal/ứng dụng** để áp dụng
- Chạy lại script bất cứ lúc nào để **cập nhật tất cả tools lên phiên bản mới nhất**

## Khắc phục sự cố
| Lỗi | Giải pháp |
|---|---|
| Script không chạy | Click phải → "Run as administrator" hoặc check PowerShell Execution Policy |
| Python không tìm thấy sau cài | Đóng và mở lại terminal, rồi chạy lại script |
| Download thất bại | Kiểm tra kết nối mạng, chạy lại script (có retry tự động 5 lần) |
| Lỗi AES-128 khi tải video | Chạy lại script để cài `pycryptodomex` |
