# Stop every ComfyUI server process (frees GPU/RAM, e.g. before AI upscaling).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\stop-comfyui-server.ps1
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.py*--port 8188*" }
foreach ($p in $procs) {
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; Write-Output "Stopped $($p.ProcessId)" }
    catch { Write-Output "Already gone: $($p.ProcessId)" }
}
if (-not $procs) { Write-Output "ComfyUI was not running" }
