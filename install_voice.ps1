# ==============================================================================
# Script cài đặt riêng phần Giọng đọc (Voice Daemon & Selector) - Antigravity Suite
# ==============================================================================

Write-Host ">>> Bắt đầu cài đặt Gói Giọng đọc (Voice Only)..." -ForegroundColor Cyan

# 0. Kiểm tra môi trường
Write-Host "`n--- 1. Kiểm tra môi trường thực thi ---" -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVer = python --version
    Write-Host " [x] Python: $pyVer (Sẵn sàng)" -ForegroundColor Green
} else {
    Write-Host " [!] Chưa tìm thấy Python. Vui lòng cài đặt Python (cần cho phát giọng đọc AI)." -ForegroundColor Red
}

$userHome = $env:USERPROFILE
$userHomeForward = $userHome.Replace('\', '/')
$scriptRoot = $PSScriptRoot

# 1. Cài đặt thư mục Global .gemini/scripts
Write-Host "`n--- 2. Cài đặt Voice Daemon và Notification Scripts ---" -ForegroundColor Yellow
$geminiDir = Join-Path $userHome ".gemini"
$geminiConfigDir = Join-Path $geminiDir "config"
$geminiScriptsDir = Join-Path $geminiDir "scripts"

New-Item -ItemType Directory -Path $geminiConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $geminiScriptsDir -Force | Out-Null

# Sao chép voice_daemon.py và voice_notify.py
$voiceDaemonSrc = Join-Path $scriptRoot "global\scripts\voice_daemon.py"
$voiceNotifySrc = Join-Path $scriptRoot "global\scripts\voice_notify.py"

if (Test-Path $voiceDaemonSrc) {
    Copy-Item $voiceDaemonSrc -Destination (Join-Path $geminiScriptsDir "voice_daemon.py") -Force
    Write-Host " [x] Đã cài đặt dịch vụ: $geminiScriptsDir\voice_daemon.py" -ForegroundColor Green
}
if (Test-Path $voiceNotifySrc) {
    Copy-Item $voiceNotifySrc -Destination (Join-Path $geminiScriptsDir "voice_notify.py") -Force
    Write-Host " [x] Đã cài đặt kích hoạt âm thanh: $geminiScriptsDir\voice_notify.py" -ForegroundColor Green
}

# Cấu hình hooks.json
$hooksSrc = Join-Path $scriptRoot "global\config\hooks.json"
$hooksDest = Join-Path $geminiConfigDir "hooks.json"
if (Test-Path $hooksSrc) {
    $hooksContent = Get-Content $hooksSrc -Raw
    $hooksContent = $hooksContent -replace 'C:/Users/[^/]+/\.gemini', "$userHomeForward/.gemini"
    Set-Content -Path $hooksDest -Value $hooksContent -Encoding UTF8
    Write-Host " [x] Đã cấu hình Hooks tự động hóa: $hooksDest" -ForegroundColor Green
}

# 2. Cài đặt Extension Voice Selector
Write-Host "`n--- 3. Cài đặt Tiện ích Chọn Giọng đọc ---" -ForegroundColor Yellow
$extTargetDirs = @()
$antigravityExtDir = Join-Path $userHome ".antigravity-ide\extensions"
if (Test-Path (Join-Path $userHome ".antigravity-ide")) {
    $extTargetDirs += $antigravityExtDir
}
$antigravityAltExtDir = Join-Path $userHome ".antigravity\extensions"
if (Test-Path (Join-Path $userHome ".antigravity")) {
    $extTargetDirs += $antigravityAltExtDir
}
$vscodeExtDir = Join-Path $userHome ".vscode\extensions"
if (Test-Path (Join-Path $userHome ".vscode")) {
    $extTargetDirs += $vscodeExtDir
}
if ($extTargetDirs.Count -eq 0) {
    $extTargetDirs += $antigravityExtDir
}

foreach ($target in $extTargetDirs) {
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    $voiceSrc = Join-Path $scriptRoot "extensions\antigravity-voice-selector"
    $voiceDest = Join-Path $target "antigravity-voice-selector-1.0.0"
    if (Test-Path $voiceSrc) {
        New-Item -ItemType Directory -Path $voiceDest -Force | Out-Null
        Copy-Item "$voiceSrc\*" -Destination $voiceDest -Recurse -Force
        Write-Host " [x] Đã cài đặt extension Voice Selector vào: $target" -ForegroundColor Green
    }
}

# 3. Khởi động Voice Daemon toàn cục
Write-Host "`n--- 4. Khởi động Dịch vụ Voice Daemon ---" -ForegroundColor Yellow
$daemonGlobalPath = Join-Path $geminiScriptsDir "voice_daemon.py"
if (Test-Path $daemonGlobalPath) {
    Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    Start-Process pythonw -ArgumentList "`"$daemonGlobalPath`""
    Start-Sleep -Milliseconds 400
    try {
        $res = Invoke-RestMethod -Uri "http://127.0.0.1:54321/ping" -Method GET -TimeoutSec 2 -ErrorAction Stop
        if ($res.status -eq "ok") {
            Write-Host " [x] Voice Daemon đã kích hoạt thành công trên 127.0.0.1:54321" -ForegroundColor Green
        }
    } catch {
        Write-Host " [!] Đang kích hoạt Voice Daemon chạy ngầm." -ForegroundColor Yellow
    }
}

Write-Host "`n>>> Chúc mừng! Cài đặt thành công Gói Giọng đọc (Voice Only)." -ForegroundColor Yellow
Write-Host ">>> Khởi động lại IDE để kích hoạt toàn diện các tính năng mới.`n" -ForegroundColor Yellow
