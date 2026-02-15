@echo off
setlocal

echo.
echo ========================================================
echo   yt-dlp Downloader - Windows One-Click Setup
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PS1_FILE=%SCRIPT_DIR%setup_windows_one_click.ps1"

if not exist "%PS1_FILE%" (
  echo [ERROR] Missing script: "%PS1_FILE%"
  echo.
  echo Make sure you run this .bat from the scripts\windows\ folder.
  pause
  exit /b 1
)

echo [INFO] Starting setup... This may take a few minutes.
echo [INFO] Python will be installed automatically if not found.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
  echo.
  echo [ERROR] Setup failed with code %ERR%.
  echo [INFO]  Try running this script again, or check the error above.
  pause
  exit /b %ERR%
)

echo.
echo [OK] Setup finished! You can now run: ytdlp-gui
echo [INFO] If this is the first time, please reopen terminal/app.
pause
exit /b 0
