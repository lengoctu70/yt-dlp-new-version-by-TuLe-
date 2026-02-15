# ============================================================
# yt-dlp Downloader - Windows One-Click Setup Script
# ============================================================
# This script:
#   1. Checks for Python 3.10+ — installs if missing
#   2. Downloads latest yt-dlp.exe, ffmpeg, aria2c into tools/bin
#   3. Installs all Python dependencies (yt-dlp, pycryptodomex, customtkinter, etc.)
#   4. Configures the app (config.json) with correct tool paths
#   5. Adds tools/bin to user PATH
# ============================================================

$ErrorActionPreference = 'Stop'

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ---------- Helper functions ----------

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [INFO] $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  [OK]   $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Invoke-DownloadWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$OutFile,
        [int]$MaxRetries = 5,
        [int]$DelaySeconds = 3
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            Write-Info "Downloading: $Url (attempt $attempt/$MaxRetries)"
            Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
            if ((Test-Path $OutFile) -and ((Get-Item $OutFile).Length -gt 0)) {
                return
            }
            throw "Downloaded file is empty: $OutFile"
        }
        catch {
            if ($attempt -eq $MaxRetries) {
                throw "Download failed after $MaxRetries attempts: $Url`n$($_.Exception.Message)"
            }
            Write-Warn "Attempt $attempt failed. Retrying in $DelaySeconds sec..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Expand-ZipClean {
    param(
        [Parameter(Mandatory = $true)][string]$ZipPath,
        [Parameter(Mandatory = $true)][string]$ExtractDir
    )

    if (Test-Path $ExtractDir) {
        Remove-Item -LiteralPath $ExtractDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir -Force
}

function Ensure-UserPathContains {
    param([Parameter(Mandatory = $true)][string]$PathToAdd)

    $current = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ([string]::IsNullOrWhiteSpace($current)) {
        [Environment]::SetEnvironmentVariable('Path', $PathToAdd, 'User')
        Write-Ok "Added to user PATH: $PathToAdd"
        return
    }

    $parts = $current.Split(';') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
    if ($parts -contains $PathToAdd) {
        Write-Info "Already in PATH: $PathToAdd"
        return
    }

    $newPath = "$current;$PathToAdd"
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Ok "Added to user PATH: $PathToAdd"
}

function Save-AppConfig {
    param(
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [Parameter(Mandatory = $true)][string]$FfmpegPath,
        [Parameter(Mandatory = $true)][string]$Aria2cPath
    )

    $config = @{}
    if (Test-Path $ConfigPath) {
        try {
            $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                $obj = $raw | ConvertFrom-Json
                if ($obj -ne $null) {
                    $obj.PSObject.Properties | ForEach-Object {
                        $config[$_.Name] = $_.Value
                    }
                }
            }
        }
        catch {
            $backupPath = "$ConfigPath.bak"
            Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -Force
            Write-Warn "Invalid config.json backed up to: $backupPath"
        }
    }

    $config['ffmpeg_path'] = $FfmpegPath
    $config['aria2c_path'] = $Aria2cPath
    $config['aria2c_enabled'] = $true

    $json = $config | ConvertTo-Json -Depth 12
    Set-Content -LiteralPath $ConfigPath -Value $json -Encoding UTF8
}

# ---------- Find Python ----------

function Find-PythonCommand {
    # Try common Python commands and return the first one >= 3.10
    $candidates = @('python', 'python3', 'py')

    foreach ($cmd in $candidates) {
        try {
            $null = Get-Command $cmd -ErrorAction Stop
            # Check version
            $versionOutput = & $cmd --version 2>&1
            if ($versionOutput -match 'Python (\d+)\.(\d+)') {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 10) {
                    return $cmd
                }
            }
        }
        catch {
            continue
        }
    }
    return $null
}

# ---------- Install Python ----------

function Install-Python {
    Write-Step "Python 3.10+ not found — Installing Python automatically"

    $pythonVersion = "3.12.8"
    $pythonInstaller = "python-${pythonVersion}-amd64.exe"
    $pythonUrl = "https://www.python.org/ftp/python/${pythonVersion}/${pythonInstaller}"
    $installerPath = Join-Path $env:TEMP $pythonInstaller

    Write-Info "Downloading Python $pythonVersion installer..."
    Invoke-DownloadWithRetry -Url $pythonUrl -OutFile $installerPath

    Write-Info "Installing Python $pythonVersion (this may take a minute)..."
    Write-Info "Options: InstallAllUsers=0, PrependPath=1, Include_pip=1"

    # Silent install for current user, add to PATH, include pip
    $installArgs = @(
        '/quiet',
        'InstallAllUsers=0',
        'PrependPath=1',
        'Include_pip=1',
        'Include_test=0',
        'Include_launcher=1',
        'InstallLauncherAllUsers=0'
    )

    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Python installer exited with code $($process.ExitCode). Please install Python 3.10+ manually from https://www.python.org/downloads/"
    }

    # Refresh PATH for current session
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"

    # Clean up installer
    Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue

    # Verify installation
    $pythonCmd = Find-PythonCommand
    if (-not $pythonCmd) {
        throw "Python was installed but cannot be found in PATH. Please restart your terminal and run this script again."
    }

    Write-Ok "Python installed successfully: $(& $pythonCmd --version 2>&1)"
    return $pythonCmd
}

# ---------- Install Python Packages ----------

function Install-PythonPackages {
    param([Parameter(Mandatory = $true)][string]$PythonCmd)

    Write-Step "Installing Python packages"

    $packages = @(
        'yt-dlp',
        'pycryptodomex',
        'customtkinter',
        'setuptools'
    )

    # First upgrade pip itself
    Write-Info "Upgrading pip..."
    try {
        & $PythonCmd -m pip install --upgrade pip 2>&1 | Out-Null
    }
    catch {
        Write-Warn "Could not upgrade pip: $($_.Exception.Message)"
    }

    foreach ($pkg in $packages) {
        Write-Info "Installing/upgrading: $pkg"
        try {
            & $PythonCmd -m pip install --upgrade $pkg
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "$pkg installed successfully"
            }
            else {
                Write-Warn "Failed to install $pkg (exit code: $LASTEXITCODE)"
            }
        }
        catch {
            Write-Warn "Failed to install $pkg — $($_.Exception.Message)"
        }
    }

    # Try optional curl-cffi (may fail on some systems, that's OK)
    Write-Info "Installing optional: curl-cffi (for browser impersonation)"
    try {
        & $PythonCmd -m pip install --upgrade 'yt-dlp[curl-cffi]' 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "curl-cffi installed successfully"
        }
        else {
            Write-Warn "curl-cffi failed (optional, app will still work)"
        }
    }
    catch {
        Write-Warn "curl-cffi not available (optional, app will still work)"
    }

    # Install the project itself if pyproject.toml exists nearby
    $scriptDir = Split-Path -Parent $PSCommandPath
    $projectRoot = (Get-Item $scriptDir).Parent.Parent.FullName
    $pyprojectPath = Join-Path $projectRoot 'pyproject.toml'
    if (Test-Path $pyprojectPath) {
        Write-Info "Installing yt-dlp Downloader app from source..."
        try {
            & $PythonCmd -m pip install -e $projectRoot
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "yt-dlp Downloader app installed (ytdlp-gui command available)"
            }
        }
        catch {
            Write-Warn "Could not install app from source: $($_.Exception.Message)"
        }
    }
}

# ============================================================
# MAIN SCRIPT
# ============================================================

try {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Magenta
    Write-Host "   yt-dlp Downloader — Windows One-Click Setup" -ForegroundColor Magenta
    Write-Host "========================================================" -ForegroundColor Magenta
    Write-Host ""

    # --- Step 1: Prepare folders ---
    Write-Step "Preparing folders"
    $configDir = Join-Path $HOME '.ytdlp-gui'
    $toolsDir = Join-Path $configDir 'tools'
    $binDir = Join-Path $toolsDir 'bin'
    $tempDir = Join-Path $env:TEMP 'ytdlp-gui-oneclick'

    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    Write-Ok "Folders ready: $binDir"

    # --- Step 2: Check/Install Python ---
    Write-Step "Checking for Python 3.10+"
    $pythonCmd = Find-PythonCommand

    if ($pythonCmd) {
        $pyVer = & $pythonCmd --version 2>&1
        Write-Ok "Found: $pyVer (command: $pythonCmd)"
    }
    else {
        $pythonCmd = Install-Python
    }

    # --- Step 3: Download yt-dlp.exe ---
    Write-Step "Downloading latest yt-dlp.exe"
    $ytDlpExePath = Join-Path $binDir 'yt-dlp.exe'
    Invoke-DownloadWithRetry -Url 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile $ytDlpExePath
    Write-Ok "yt-dlp.exe → $ytDlpExePath"

    # --- Step 4: Download FFmpeg ---
    Write-Step "Downloading latest FFmpeg (essentials build)"
    $ffmpegZip = Join-Path $tempDir 'ffmpeg-release-essentials.zip'
    Invoke-DownloadWithRetry -Url 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $ffmpegZip

    $ffmpegExtractDir = Join-Path $tempDir 'ffmpeg_extract'
    Expand-ZipClean -ZipPath $ffmpegZip -ExtractDir $ffmpegExtractDir

    $ffmpegExe = Get-ChildItem -Path $ffmpegExtractDir -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1
    $ffprobeExe = Get-ChildItem -Path $ffmpegExtractDir -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1

    if (-not $ffmpegExe) {
        throw 'Cannot find ffmpeg.exe after extraction.'
    }

    Copy-Item -LiteralPath $ffmpegExe.FullName -Destination (Join-Path $binDir 'ffmpeg.exe') -Force
    if ($ffprobeExe) {
        Copy-Item -LiteralPath $ffprobeExe.FullName -Destination (Join-Path $binDir 'ffprobe.exe') -Force
    }
    Write-Ok "ffmpeg.exe + ffprobe.exe → $binDir"

    # --- Step 5: Download aria2c ---
    Write-Step "Downloading latest aria2c"
    $ghHeaders = @{ 'User-Agent' = 'ytdlp-gui-oneclick' }
    $ariaRelease = Invoke-RestMethod -Uri 'https://api.github.com/repos/aria2/aria2/releases/latest' -Headers $ghHeaders -UseBasicParsing
    $ariaAsset = $ariaRelease.assets |
        Where-Object { $_.name -match 'win-64bit-build1\.zip$' } |
        Select-Object -First 1

    if (-not $ariaAsset) {
        $ariaAsset = $ariaRelease.assets |
            Where-Object { $_.name -match 'win-32bit-build1\.zip$' } |
            Select-Object -First 1
    }

    if (-not $ariaAsset) {
        throw 'Cannot find aria2 Windows asset in latest release.'
    }

    $ariaZip = Join-Path $tempDir $ariaAsset.name
    Invoke-DownloadWithRetry -Url $ariaAsset.browser_download_url -OutFile $ariaZip

    $ariaExtractDir = Join-Path $tempDir 'aria_extract'
    Expand-ZipClean -ZipPath $ariaZip -ExtractDir $ariaExtractDir

    $ariaExe = Get-ChildItem -Path $ariaExtractDir -Recurse -Filter 'aria2c.exe' | Select-Object -First 1
    if (-not $ariaExe) {
        throw 'Cannot find aria2c.exe after extraction.'
    }
    Copy-Item -LiteralPath $ariaExe.FullName -Destination (Join-Path $binDir 'aria2c.exe') -Force
    Write-Ok "aria2c.exe → $binDir"

    # --- Step 6: Add to PATH ---
    Write-Step "Updating user PATH"
    Ensure-UserPathContains -PathToAdd $binDir
    # Also refresh current session PATH
    $env:Path = "$binDir;$env:Path"

    # --- Step 7: Write app config ---
    Write-Step "Writing app config (config.json)"
    $configPath = Join-Path $configDir 'config.json'
    Save-AppConfig -ConfigPath $configPath -FfmpegPath (Join-Path $binDir 'ffmpeg.exe') -Aria2cPath (Join-Path $binDir 'aria2c.exe')
    Write-Ok "Config saved: $configPath"

    # --- Step 8: Install Python packages ---
    Install-PythonPackages -PythonCmd $pythonCmd

    # --- Step 9: Cleanup temp files ---
    Write-Step "Cleaning up temporary files"
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Ok "Temp files removed"

    # --- Step 10: Verify everything ---
    Write-Step "Verifying installations"

    Write-Info "yt-dlp version:"
    & (Join-Path $binDir 'yt-dlp.exe') --version

    Write-Info "ffmpeg version:"
    & (Join-Path $binDir 'ffmpeg.exe') -version 2>&1 | Select-Object -First 1

    Write-Info "aria2c version:"
    & (Join-Path $binDir 'aria2c.exe') --version 2>&1 | Select-Object -First 1

    Write-Info "Python version:"
    & $pythonCmd --version

    Write-Info "Checking pycryptodomex:"
    $cryptoCheck = & $pythonCmd -c "import Cryptodome; print(f'pycryptodomex v{Cryptodome.__version__}')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "$cryptoCheck"
    }
    else {
        Write-Warn "pycryptodomex not working (AES-128 streams may have issues)"
    }

    # --- Done! ---
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "   SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Tools installed in:  $binDir" -ForegroundColor Green
    Write-Host "  Config saved to:     $configPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "  All tools in one folder:" -ForegroundColor White
    Write-Host "    - yt-dlp.exe" -ForegroundColor White
    Write-Host "    - ffmpeg.exe" -ForegroundColor White
    Write-Host "    - ffprobe.exe" -ForegroundColor White
    Write-Host "    - aria2c.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "  To run the app, type:  ytdlp-gui" -ForegroundColor Yellow
    Write-Host "  (Reopen terminal first if PATH was just updated)" -ForegroundColor Yellow
    Write-Host ""
    exit 0
}
catch {
    Write-Host ''
    Write-Host '========================================================' -ForegroundColor Red
    Write-Host '   SETUP FAILED' -ForegroundColor Red
    Write-Host '========================================================' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ''
    Write-Host 'Troubleshooting:' -ForegroundColor Yellow
    Write-Host '  1. Check your internet connection' -ForegroundColor Yellow
    Write-Host '  2. Try running this script again' -ForegroundColor Yellow
    Write-Host '  3. If Python install fails, download manually:' -ForegroundColor Yellow
    Write-Host '     https://www.python.org/downloads/' -ForegroundColor Yellow
    Write-Host ''
    exit 1
}
