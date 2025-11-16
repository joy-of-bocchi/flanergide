# PowerShell script to test summary system
# Usage: .\test.ps1 "YOUR_JWT_TOKEN_HERE"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "SUMMARIZATION SYSTEM TEST" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Test server
Write-Host "1. Testing server connection..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
    if ($health.status -eq "ok") {
        Write-Host "   [OK] Server is running!" -ForegroundColor Green
    }
} catch {
    Write-Host "   [ERROR] Server not responding: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Upload test logs
Write-Host ""
Write-Host "2. Uploading test logs..." -ForegroundColor Yellow
try {
    $headers = @{
        "Authorization" = "Bearer $Token"
        "Content-Type" = "application/json"
    }

    $body = Get-Content "test_logs.json" -Raw
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/logs/upload" `
                                  -Method Post `
                                  -Headers $headers `
                                  -Body $body `
                                  -ContentType "application/json"

    Write-Host "   [OK] Uploaded: $($response.uploaded) logs" -ForegroundColor Green
    Write-Host "   [OK] Failed: $($response.failed) logs" -ForegroundColor Green
    Write-Host "   [OK] Status: $($response.status)" -ForegroundColor Green
    Write-Host "   [OK] Message: $($response.message)" -ForegroundColor Green

} catch {
    Write-Host "   [ERROR] Upload failed: $_" -ForegroundColor Red
    Write-Host "   Response: $($_.Exception.Response)" -ForegroundColor Red
    exit 1
}

# Step 3: Generate summary
Write-Host ""
Write-Host "3. Generating today's summary (this may take 30-60 seconds)..." -ForegroundColor Yellow
try {
    $summary = Invoke-RestMethod -Uri "http://localhost:8000/api/summary/today" `
                                    -Method Get `
                                    -Headers $headers `
                                    -TimeoutSec 120

    Write-Host "   [OK] Summary generated!" -ForegroundColor Green
    Write-Host "   [OK] Date: $($summary.metadata.date_range)" -ForegroundColor Green
    Write-Host "   [OK] Log count: $($summary.metadata.log_count)" -ForegroundColor Green
    Write-Host "   [OK] Blog count: $($summary.metadata.blog_count)" -ForegroundColor Green
    Write-Host "   [OK] Analysis type: $($summary.metadata.analysis_type)" -ForegroundColor Green

    Write-Host ""
    Write-Host "   Files created:" -ForegroundColor Cyan
    Write-Host "   - $($summary.log_file_path)" -ForegroundColor White
    Write-Host "   - $($summary.summary_file_path)" -ForegroundColor White

    # Show preview
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "SUMMARY PREVIEW (first 800 characters):" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    $preview = $summary.summary.Substring(0, [Math]::Min(800, $summary.summary.Length))
    Write-Host $preview -ForegroundColor White
    Write-Host "..." -ForegroundColor Gray
    Write-Host "================================================================================" -ForegroundColor Cyan

} catch {
    Write-Host "   [ERROR] Summary generation failed: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Show files to check
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check these files:" -ForegroundColor Yellow
Write-Host "  1. $($summary.log_file_path)" -ForegroundColor White
Write-Host "  2. $($summary.summary_file_path)" -ForegroundColor White
Write-Host ""
Write-Host "View them with:" -ForegroundColor Yellow
Write-Host "  Get-Content `"$($summary.log_file_path)`"" -ForegroundColor Cyan
Write-Host "  Get-Content `"$($summary.summary_file_path)`"" -ForegroundColor Cyan
Write-Host ""
