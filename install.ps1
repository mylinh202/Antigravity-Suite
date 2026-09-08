# ==============================================================================
# Script cài đặt tự động Antigravity Suite (Global Rules + Extensions)
# ==============================================================================

Write-Host ">>> Bắt đầu cài đặt Antigravity Suite..." -ForegroundColor Cyan

# 0. Kiểm tra môi trường
Write-Host "`n--- 1. Kiểm tra môi trường thực thi ---" -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node -v
    Write-Host " [x] Node.js: $nodeVer (Sẵn sàng)" -ForegroundColor Green
} else {
    Write-Host " [!] Chưa tìm thấy Node.js. Vui lòng cài đặt Node.js từ https://nodejs.org/" -ForegroundColor Red
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVer = python --version
    Write-Host " [x] Python: $pyVer (Sẵn sàng)" -ForegroundColor Green
} else {
    Write-Host " [!] Chưa tìm thấy Python (cần cho phát giọng đọc AI)." -ForegroundColor Yellow
}

$userHome = $env:USERPROFILE
$userHomeForward = $userHome.Replace('\', '/')
$scriptRoot = $PSScriptRoot

# 1. Cài đặt thư mục Global .gemini
Write-Host "`n--- 2. Cài đặt Global Rules và Hooks ---" -ForegroundColor Yellow
$geminiDir = Join-Path $userHome ".gemini"
$geminiConfigDir = Join-Path $geminiDir "config"
$geminiScriptsDir = Join-Path $geminiDir "scripts"

New-Item -ItemType Directory -Path $geminiConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $geminiScriptsDir -Force | Out-Null

# Sao chép GEMINI.md
$globalRulesSrc = Join-Path $scriptRoot "global\GEMINI.md"
$globalRulesDest = Join-Path $geminiDir "GEMINI.md"
Copy-Item $globalRulesSrc -Destination $globalRulesDest -Force
Write-Host " [x] Đã cập nhật Global Rules: $globalRulesDest" -ForegroundColor Green

# Sao chép scripts
Copy-Item (Join-Path $scriptRoot "global\scripts\*") -Destination $geminiScriptsDir -Recurse -Force
Write-Host " [x] Đã cài đặt các script bổ trợ: $geminiScriptsDir" -ForegroundColor Green

# Cấu hình hooks.json với đường dẫn thực tế của người dùng
$hooksSrc = Join-Path $scriptRoot "global\config\hooks.json"
$hooksDest = Join-Path $geminiConfigDir "hooks.json"
$hooksContent = Get-Content $hooksSrc -Raw
$hooksContent = $hooksContent -replace 'C:/Users/[^/]+/\.gemini', "$userHomeForward/.gemini"
Set-Content -Path $hooksDest -Value $hooksContent -Encoding UTF8
Write-Host " [x] Đã cấu hình Hooks tự động hóa: $hooksDest" -ForegroundColor Green

# 2. Cài đặt Extensions
$extTargetDirs = @()

$antigravityExtDir = Join-Path $userHome ".antigravity-ide\extensions"
if (Test-Path (Join-Path $userHome ".antigravity-ide")) {
    $extTargetDirs += $antigravityExtDir
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

    # Antigravity Voice Selector
    $voiceSrc = Join-Path $scriptRoot "extensions\antigravity-voice-selector"
    $voiceDest = Join-Path $target "antigravity-voice-selector-1.0.0"
    New-Item -ItemType Directory -Path $voiceDest -Force | Out-Null
    Copy-Item "$voiceSrc\*" -Destination $voiceDest -Recurse -Force

    # Antigravity Context Monitor
    $contextSrc = Join-Path $scriptRoot "extensions\antigravity-context-monitor"
    $contextDest = Join-Path $target "antigravity-context-monitor-1.0.0"
    New-Item -ItemType Directory -Path $contextDest -Force | Out-Null
    Copy-Item "$contextSrc\*" -Destination $contextDest -Recurse -Force

    Write-Host " [x] Đã cài đặt 2 extension vào: $target" -ForegroundColor Green
}

Write-Host "`n>>> Chúc mừng! Cài đặt thành công toàn bộ Antigravity Suite." -ForegroundColor Yellow
Write-Host ">>> Khởi động lại IDE để kích hoạt toàn diện các tính năng mới.`n" -ForegroundColor Yellow
