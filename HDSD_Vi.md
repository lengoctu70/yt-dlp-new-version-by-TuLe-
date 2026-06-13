# Hướng dẫn cài đặt & chạy trên Windows

[English README](README.md)

## 1. Cài Python 3.10+

1. Tải Python tại: https://www.python.org/downloads/
2. Chạy file cài đặt, **QUAN TRỌNG: tick ô "Add Python to PATH"** trước khi bấm Install
3. Kiểm tra:

```cmd
python --version
```

Kết quả mong muốn: `Python 3.10.x` trở lên.

**Nếu lỗi "python không được nhận dạng":**

```cmd
:: Thử lệnh này thay thế
python3 --version

:: Nếu vẫn lỗi → cài lại Python, nhớ tick "Add Python to PATH"
```

## 2. Tải source code

```cmd
:: Cách 1: Dùng git
git clone <URL-repo> yt-dlp_downloader
cd yt-dlp_downloader

:: Cách 2: Tải ZIP từ GitHub → giải nén → mở CMD trong thư mục đó
:: Click phải vào thư mục → "Open in Terminal" hoặc gõ:
cd C:\Users\TenBan\Downloads\yt-dlp_downloader
```

## 3. Cài đặt app

```cmd
pip install .
```

**Nếu lỗi "pip không được nhận dạng":**

```cmd
:: Thử:
python -m pip install .

:: Nếu vẫn lỗi → cài pip:
python -m ensurepip --upgrade
python -m pip install .
```

**Cài bản dev (để chỉnh sửa code):**

```cmd
pip install -e .
```

## 4. Chạy app

```cmd
ytdlp-gui
```

**Nếu lỗi "ytdlp-gui không được nhận dạng":**

```cmd
:: Chạy trực tiếp bằng Python:
set PYTHONPATH=src
python -m ytdlp_gui.app

:: Hoặc (PowerShell):
$env:PYTHONPATH="src"; python -m ytdlp_gui.app
```

## 5. Cài FFmpeg (tuỳ chọn — cần cho merge video+audio, chuyển format)

1. Tải tại: https://www.gyan.dev/ffmpeg/builds/ → chọn `ffmpeg-release-essentials.zip`
2. Giải nén, ví dụ ra `C:\ffmpeg`
3. Thêm vào PATH:

```cmd
:: Thêm tạm (chỉ trong phiên CMD hiện tại):
set PATH=%PATH%;C:\ffmpeg\bin

:: Thêm vĩnh viễn (chạy CMD với quyền Admin):
setx PATH "%PATH%;C:\ffmpeg\bin"
```

4. Kiểm tra: `ffmpeg -version`

**Hoặc:** Mở app → Settings → FFmpeg → chỉ đường dẫn thủ công đến file `ffmpeg.exe`

## 6. Cài aria2c (tuỳ chọn — tăng tốc tải)

1. Tải tại: https://github.com/aria2/aria2/releases → file `aria2-...-win-64bit-build1.zip`
2. Giải nén, ví dụ ra `C:\aria2`
3. Thêm vào PATH tương tự FFmpeg:

```cmd
set PATH=%PATH%;C:\aria2
```

4. Kiểm tra: `aria2c --version`

**Hoặc:** Bật trong app → Settings → aria2c

## 6b. Dùng yt-dlp bản tự tải (khuyên dùng khi gặp lỗi extractor)

Khi gặp lỗi kiểu `Failed to parse XML` (Vimeo) hoặc cảnh báo impersonation, nguyên nhân thường là yt-dlp tích hợp sẵn đã cũ. Cách fix:

1. Tải bản yt-dlp mới nhất: https://github.com/yt-dlp/yt-dlp/releases
   - Windows: `yt-dlp.exe`
   - macOS/Linux: `yt-dlp_macos` / `yt-dlp` (nhớ `chmod +x`)
2. Mở app → Settings → Tools → **yt-dlp Path** → Browse → chọn file vừa tải
3. Status hiện số phiên bản (vd `2026.06.10`) là OK. Để trống = dùng bản tích hợp sẵn.

Bản tự chọn vẫn dùng đầy đủ: Referer/headers, cookies, proxy, impersonate, aria2c, extract audio, progress, cancel.

## 7. Lỗi thường gặp & cách fix

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|----------|
| `'python' is not recognized` | Python chưa trong PATH | Cài lại Python, tick "Add to PATH" |
| `'pip' is not recognized` | pip chưa trong PATH | Dùng `python -m pip install .` |
| `ModuleNotFoundError: customtkinter` | Chưa cài dependencies | Chạy lại `pip install .` |
| `ModuleNotFoundError: ytdlp_gui` | Thiếu PYTHONPATH | Dùng `set PYTHONPATH=src` trước khi chạy |
| `ffmpeg not found` | Chưa cài hoặc chưa thêm PATH | Xem bước 5 |
| `PermissionError` khi cài | Cần quyền admin | Chạy CMD với "Run as Administrator" |
| `ERROR: No video formats found` | Video cần cookie đăng nhập | Xem mục 8 bên dưới |
| `Failed to parse XML` (Vimeo) | yt-dlp tích hợp đã cũ | Dùng yt-dlp bản tự tải (xem mục 6b) |
| Cảnh báo `impersonation... no impersonate target` | Thiếu curl-cffi | Dùng yt-dlp.exe bản standalone (mục 6b) hoặc `pip install curl-cffi` |
| `Failed to decrypt with DPAPI` | Chrome cookie bị mã hóa | Dùng cookie file thay vì browser (xem mục 8) |
| App bị treo khi tải | Quá nhiều download đồng thời | Settings → giảm concurrent downloads xuống 1-2 |

## 8. Thiết lập Cookie (cho video cần đăng nhập)

Một số video yêu cầu đăng nhập (YouTube premium, video riêng tư...). Bạn cần export cookie từ trình duyệt.

> ⚠️ **Lưu ý:** Chế độ "Browser" (lấy cookie tự động) có thể bị lỗi DPAPI trên macOS và Windows mới. **Khuyến nghị dùng "File" mode.**

### Cách làm:

1. **Cài tiện ích Chrome**: [Get cookies.txt locally](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. **Đăng nhập** vào trang video (YouTube, v.v.)
3. **Click tiện ích** → chọn "Export" → lưu file `cookies.txt`
4. **Trong app**: Settings → Cookie Settings → chọn **File** → Browse → chọn file `cookies.txt` vừa lưu

> 💡 Nên export lại cookie khi cookie hết hạn (thường sau vài ngày-vài tuần).

## Tóm tắt lệnh (copy nhanh)

```cmd
:: Cài đặt
pip install .

:: Chạy
ytdlp-gui

:: Nếu lỗi, chạy cách này:
set PYTHONPATH=src
python -m ytdlp_gui.app
```
