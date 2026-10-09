# Restart ComfyUI cleanly: stop EVERY ComfyUI process, then start exactly one detached server and wait until ready.
# Why: leftover servers each held GBs of RAM (5 found on 2026-10-05), and switching image <-> video models
# in one server process crashed Wan (access violation). Restart between image and video phases.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\restart-comfyui-server-clean.ps1
# Do NOT pipe its output (e.g. "| tail"): the detached server inherits the pipe, so the pipe never closes
# and the caller hangs. Redirect to a file instead if you need the output.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$comfy = Join-Path $root "ComfyUI"
$logOut = Join-Path $root "experiments\comfyui-server.log"
$logErr = Join-Path $root "experiments\comfyui-server-stderr.log"

$old = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.py*--port 8188*" }
foreach ($p in $old) {
    Write-Output "Stopping old ComfyUI process $($p.ProcessId)"
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch { Write-Output "  (already gone)" }
}
Start-Sleep -Seconds 3

# --disable-pinned-memory: required on 16GB RAM (see docs/ai-video-factory-project-overview-v3.md section 6)
Start-Process -FilePath (Join-Path $comfy "venv\Scripts\python.exe") `
    -ArgumentList "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-pinned-memory" `
    -WorkingDirectory $comfy -WindowStyle Hidden `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr | Out-Null

$deadline = (Get-Date).AddMinutes(4)
while ((Get-Date) -lt $deadline) {
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8188/system_stats" -TimeoutSec 3 | Out-Null
        Write-Output "ComfyUI ready at http://127.0.0.1:8188"
        exit 0
    } catch { Start-Sleep -Seconds 3 }
}
Write-Output "ComfyUI did not become ready in 4 minutes - check $logErr"
exit 1
