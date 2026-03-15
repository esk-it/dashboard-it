# Cleanly kill ALL backend processes (uvicorn + workers + orphans)
# Solves the Windows zombie process issue with uvicorn --reload

param([int]$Port = 8010)

Write-Host "Stopping backend on port $Port..." -ForegroundColor Yellow

# 1. Find the root uvicorn process on our port
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    foreach ($conn in $listeners) {
        $procId = $conn.OwningProcess
        # Use taskkill /T to kill the entire process tree
        Write-Host "  Killing process tree for PID $procId" -ForegroundColor Red
        taskkill /F /T /PID $procId 2>$null | Out-Null
    }
}

# 2. Kill any uvicorn/backend processes by command line match
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*backend.main*'
} | ForEach-Object {
    Write-Host "  Killing backend process PID $($_.ProcessId)" -ForegroundColor Red
    taskkill /F /T /PID $_.ProcessId 2>$null | Out-Null
}

# 3. Kill orphaned spawn_main workers (parent dead)
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*spawn_main*'
} | ForEach-Object {
    $parent = Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue
    if (-not $parent) {
        Write-Host "  Killing orphan worker PID $($_.ProcessId)" -ForegroundColor DarkRed
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 4. Also clean old ports (8008, 8009) if still occupied
foreach ($oldPort in @(8008, 8009)) {
    Get-NetTCPConnection -LocalPort $oldPort -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  Cleaning old port $oldPort (PID $($_.OwningProcess))" -ForegroundColor DarkRed
        taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null
    }
}

Start-Sleep -Seconds 1

# Verify
$remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "WARNING: Port $Port still occupied!" -ForegroundColor Red
} else {
    Write-Host "Port $Port is free." -ForegroundColor Green
}
