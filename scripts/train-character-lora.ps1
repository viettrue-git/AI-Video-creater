# Train a character LoRA with kohya sd-scripts as a detached background process.
# Stops ComfyUI first (16GB RAM cannot hold both). Log: lora/<name>/output/train.log
# Usage: powershell -ExecutionPolicy Bypass -File scripts\train-character-lora.ps1 tam-explorer-v1
param([Parameter(Mandatory = $true)][string]$LoraName)
$root = Split-Path -Parent $PSScriptRoot
$loraDir = Join-Path $root "lora\$LoraName"
$trainer = Join-Path $root "tools\lora-trainer"
if (-not (Test-Path (Join-Path $loraDir "train.toml"))) { Write-Output "Missing $loraDir\train.toml"; exit 1 }

& (Join-Path $PSScriptRoot "stop-comfyui-server.ps1")
$out = Join-Path $loraDir "output"
New-Item -ItemType Directory -Force $out | Out-Null
$env:HF_HOME = Join-Path $trainer "hf-cache"   # keep model downloads inside the trainer folder
$env:PYTHONIOENCODING = "utf-8"
$accelerate = Join-Path $trainer "venv\Scripts\accelerate.exe"
$p = Start-Process -FilePath $accelerate `
    -ArgumentList "launch", "--num_cpu_threads_per_process", "1", "--mixed_precision", "bf16", "--num_processes", "1", `
                  "--num_machines", "1", "--dynamo_backend", "no", "sdxl_train_network.py", "--config_file", (Join-Path $loraDir "train.toml") `
    -WorkingDirectory $trainer -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $out "train.log") -RedirectStandardError (Join-Path $out "train.err.log")
Write-Output "Training $LoraName started (pid $($p.Id)); log: $out\train.log"
