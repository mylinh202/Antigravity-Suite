# ==============================================================================
# Script cài đặt riêng phần Quy tắc (Rules & Context Monitor) - Antigravity Suite
# ==============================================================================

Write-Host ">>> Bắt đầu cài đặt Gói Quy tắc (Rules Only)..." -ForegroundColor Cyan

# 0. Kiểm tra môi trường
Write-Host "`n--- 1. Kiểm tra môi trường thực thi ---" -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node -v
    Write-Host " [x] Node.js: $nodeVer (Sẵn sàng)" -ForegroundColor Green
} else {
    Write-Host " [!] Chưa tìm thấy Node.js. Vui lòng cài đặt Node.js từ https://nodejs.org/" -ForegroundColor Red
}

$userHome = $env:USERPROFILE
$userHomeForward = $userHome.Replace('\', '/')
$scriptRoot = $PSScriptRoot

# 1. Cài đặt thư mục Global .gemini
Write-Host "`n--- 2. Cài đặt Global Rules và Enforce Script ---" -ForegroundColor Yellow
$geminiDir = Join-Path $userHome ".gemini"
$geminiConfigDir = Join-Path $geminiDir "config"
$geminiScriptsDir = Join-Path $geminiDir "scripts"

New-Item -ItemType Directory -Path $geminiConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $geminiScriptsDir -Force | Out-Null

# Sao chép GEMINI.md
$globalRulesSrc = Join-Path $scriptRoot "global\GEMINI.md"
$globalRulesDest = Join-Path $geminiDir "GEMINI.md"
if (Test-Path $globalRulesSrc) {
    Copy-Item $globalRulesSrc -Destination $globalRulesDest -Force
    Write-Host " [x] Đã cập nhật Global Rules: $globalRulesDest" -ForegroundColor Green
}

# Sao chép script enforce_rules.js
$enforceSrc = Join-Path $scriptRoot "global\scripts\enforce_rules.js"
if (Test-Path $enforceSrc) {
    Copy-Item $enforceSrc -Destination (Join-Path $geminiScriptsDir "enforce_rules.js") -Force
    Write-Host " [x] Đã cài đặt script kiểm soát: $geminiScriptsDir\enforce_rules.js" -ForegroundColor Green
}

# 2. Cài đặt Extension Context Monitor
Write-Host "`n--- 3. Cài đặt Tiện ích Giám sát Ngữ cảnh ---" -ForegroundColor Yellow
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
    $contextSrc = Join-Path $scriptRoot "extensions\antigravity-context-monitor"
    $contextDest = Join-Path $target "antigravity-context-monitor-1.0.0"
    if (Test-Path $contextSrc) {
        New-Item -ItemType Directory -Path $contextDest -Force | Out-Null
        Copy-Item "$contextSrc\*" -Destination $contextDest -Recurse -Force
        Write-Host " [x] Đã cài đặt extension Context Monitor vào: $target" -ForegroundColor Green
    }
}

Write-Host "`n>>> Chúc mừng! Cài đặt thành công Gói Quy tắc (Rules Only)." -ForegroundColor Yellow
Write-Host ">>> Khởi động lại IDE để áp dụng các quy chuẩn mới.`n" -ForegroundColor Yellow
