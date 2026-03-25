# stop_and_clean.ps1 - Kill all processes on port 5000 and clean SQLite temp files

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SQLFileProcess Stop & Clean Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: Kill all processes listening on port 5000 ----
Write-Host "[1/3] Finding processes on port 5000..." -ForegroundColor Yellow

$pids = @()
$lines = & netstat -ano | Select-String ":5000"
foreach ($line in $lines) {
    if ($line -match '\s+(\d+)\s*$') {
        $p = [int]$Matches[1]
        if ($p -gt 0 -and $p -notin $pids) {
            $pids += $p
        }
    }
}

if ($pids.Count -eq 0) {
    Write-Host "  No process found on port 5000." -ForegroundColor Green
} else {
    foreach ($p in $pids) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  Killing: $($proc.Name) (PID $p)" -ForegroundColor Red
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  Done." -ForegroundColor Green
}

# ---- Step 2: Kill any leftover python app.py processes ----
Write-Host ""
Write-Host "[2/3] Finding leftover python app.py processes..." -ForegroundColor Yellow

$pythonProcs = Get-WmiObject Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -match 'app\.py'
}

if ($null -ne $pythonProcs -and @($pythonProcs).Count -gt 0) {
    foreach ($proc in @($pythonProcs)) {
        Write-Host "  Killing: $($proc.Name) (PID $($proc.ProcessId))" -ForegroundColor Red
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  Done." -ForegroundColor Green
} else {
    Write-Host "  No leftover python process found." -ForegroundColor Green
}

# ---- Step 3: Clean SQLite WAL/SHM temp files ----
Write-Host ""
Write-Host "[3/3] Cleaning SQLite temp files..." -ForegroundColor Yellow

Start-Sleep -Seconds 2

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tempFiles = @(
    (Join-Path $scriptDir "sql_fix_log.db-wal"),
    (Join-Path $scriptDir "sql_fix_log.db-shm")
)

foreach ($f in $tempFiles) {
    if (Test-Path $f) {
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        Write-Host "  Deleted: $f" -ForegroundColor Green
    } else {
        Write-Host "  Not found (skip): $f" -ForegroundColor DarkGray
    }
}

# ---- Done ----
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  All done!" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Verify port 5000
$check = & netstat -ano | Select-String ":5000"
if ($check) {
    Write-Host "[WARN] Port 5000 still has connections (TIME_WAIT is normal, will expire):" -ForegroundColor DarkYellow
    $check | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkYellow }
} else {
    Write-Host "[OK] Port 5000 fully released." -ForegroundColor Green
}
