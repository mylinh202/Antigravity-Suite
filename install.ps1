# ==============================================================================
# Script cài đặt tổng hợp Antigravity Suite (Hỗ trợ phân tách module)
# ==============================================================================

param (
    [Parameter(Mandatory = $false)]
    [ValidateSet("All", "Rules", "Voice")]
    [string]$Type = ""
)

$scriptRoot = $PSScriptRoot

function Run-InstallAll {
    Write-Host "`n>>> Đang thực hiện cài đặt TOÀN BỘ Antigravity Suite..." -ForegroundColor Cyan
    & (Join-Path $scriptRoot "install_rules.ps1")
    Start-Sleep -Milliseconds 300
    & (Join-Path $scriptRoot "install_voice.ps1")
}

function Run-InstallRules {
    & (Join-Path $scriptRoot "install_rules.ps1")
}

function Run-InstallVoice {
    & (Join-Path $scriptRoot "install_voice.ps1")
}

# 1. Nếu có truyền tham số dòng lệnh -Type
if ($Type -eq "All") {
    Run-InstallAll
    exit 0
} elseif ($Type -eq "Rules") {
    Run-InstallRules
    exit 0
} elseif ($Type -eq "Voice") {
    Run-InstallVoice
    exit 0
}

# 2. Nếu không truyền tham số: Hiển thị Menu tương tác trực quan
Clear-Host
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         ANTIGRAVITY SUITE - BỘ CÀI ĐẶT MÔ-ĐUN HÓA          " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Vui lòng chọn gói cài đặt bạn mong muốn:" -ForegroundColor White
Write-Host ""
Write-Host "  [1] Cài đặt TOÀN BỘ (Quy tắc + Giọng đọc AI + Tiện ích)" -ForegroundColor Green
Write-Host "  [2] Chỉ cài đặt QUY TẮC (Global Rules + Context Monitor)" -ForegroundColor Cyan
Write-Host "  [3] Chỉ cài đặt GIỌNG ĐỌC (Voice Daemon + Selector)" -ForegroundColor Magenta
Write-Host "  [0] Thoát cài đặt" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan

$choice = Read-Host "Nhập lựa chọn của bạn [1/2/3/0] (Mặc định: 1)"

if ([string]::IsNullOrWhiteSpace($choice) -or $choice -eq "1") {
    Run-InstallAll
} elseif ($choice -eq "2") {
    Run-InstallRules
} elseif ($choice -eq "3") {
    Run-InstallVoice
} elseif ($choice -eq "0") {
    Write-Host "Đã hủy cài đặt." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Lựa chọn không hợp lệ. Đang tiến hành cài đặt toàn bộ theo mặc định..." -ForegroundColor Yellow
    Run-InstallAll
}
