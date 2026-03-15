# Start backend - kills any existing process first for a clean start
$port = 8010
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Kill existing processes on the port
& "$projectDir\kill_backend.ps1"

Write-Host "Starting uvicorn on port $port..." -ForegroundColor Cyan
Start-Process -FilePath "$projectDir\.venv\Scripts\uvicorn.exe" `
    -ArgumentList "backend.main:app", "--port", "$port", "--reload" `
    -WorkingDirectory $projectDir `
    -WindowStyle Hidden

Start-Sleep -Seconds 2

# Verify
$conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "Backend running on http://localhost:$port (PID $($conn.OwningProcess | Select-Object -First 1))" -ForegroundColor Green
} else {
    Write-Host "ERROR: Backend failed to start!" -ForegroundColor Red
}
