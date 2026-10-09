# PowerShell twin of download-model-files-with-size-check.sh (use when Git Bash is slow/unavailable).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\download-model-files-with-size-check.ps1 scripts\<list>.txt
# List lines: <url> <path relative to ComfyUI/models>   (# = comment). Resumes partial downloads, verifies sizes.
param([Parameter(Mandatory = $true)][string]$ListFile)
$root = Split-Path -Parent $PSScriptRoot
$models = Join-Path $root "ComfyUI\models"
$lock = Join-Path $models ".download.lock"
if (-not (New-Item -ItemType Directory $lock -ErrorAction SilentlyContinue)) { Write-Output "Another download is running ($lock)"; exit 1 }
$failed = 0
try {
    foreach ($line in Get-Content (Join-Path $root $ListFile)) {
        if (-not $line.Trim() -or $line.Trim().StartsWith("#")) { continue }
        $url, $rel = $line.Trim() -split "\s+", 2
        $dest = Join-Path $models $rel
        $head = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -MaximumRedirection 10
        $expected = [int64]($head.Headers["Content-Length"] | Select-Object -First 1)
        if ((Test-Path $dest) -and (Get-Item $dest).Length -eq $expected) { Write-Output "OK (already have) $rel"; continue }
        New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
        $part = "$dest.part"
        & curl.exe -sSL --retry 5 --retry-delay 5 -C - -o $part $url
        $actual = (Get-Item $part -ErrorAction SilentlyContinue).Length
        if ($actual -eq $expected) { Move-Item $part $dest -Force; Write-Output "DONE $rel ($actual bytes)" }
        else { Write-Output "FAIL size $rel ($actual != $expected)"; $failed++ }
    }
} finally { Remove-Item $lock -Force }
exit $failed
