# Start make_video.py for a project as an independent background process (survives closing this console/session).
# Output -> projects/<id>_*/build/make_video.log (+ make_video.err.log). The picker page opens in the browser when needed.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\start-make-video-detached.ps1 P002
param([Parameter(Mandatory = $true)][string]$ProjectId)
$root = Split-Path -Parent $PSScriptRoot
$projectDir = Get-ChildItem (Join-Path $root "projects") -Directory | Where-Object { $_.Name -like "$ProjectId`_*" } | Select-Object -First 1
if (-not $projectDir) { Write-Output "Project $ProjectId not found"; exit 1 }
$build = Join-Path $projectDir.FullName "build"
New-Item -ItemType Directory -Force $build | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$p = Start-Process -FilePath (Join-Path $root "ComfyUI\venv\Scripts\python.exe") `
    -ArgumentList "-u", "scripts\make_video.py", $ProjectId `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $build "make_video.log") -RedirectStandardError (Join-Path $build "make_video.err.log")
Write-Output "Started make_video $ProjectId (pid $($p.Id)); log: $build\make_video.log"
