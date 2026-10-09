"""Watch a kohya LoRA training log: print step progress every few minutes, errors at once, and the end.
  python scripts/watch_lora_training_log.py tam-explorer-v1
"""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEP = re.compile(r"steps:\s+(\d+)%\|[^|]*\|\s*(\d+)/(\d+) \[([^\]]*)\]")
ERROR = re.compile(r"Traceback|Error:|out of memory|CUDA error")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
name = sys.argv[1]
out = ROOT / "lora" / name / "output"
log = out / "train.err.log"
report_every, last_report, last_epoch_files = 300, 0.0, set()
while True:
    text = log.read_text(encoding="utf-8", errors="replace").replace("\r", "\n") if log.exists() else ""
    if (m := ERROR.search(text)):
        tail = [ln for ln in text.splitlines() if ln.strip()][-6:]
        print("ERROR in training:\n" + "\n".join(ln[:200] for ln in tail), flush=True)
        sys.exit(1)
    epochs = {p.name for p in out.glob(f"{name}-*.safetensors")}
    for new in sorted(epochs - last_epoch_files):
        print(f"checkpoint saved: {new}", flush=True)
    last_epoch_files = epochs
    steps = STEP.findall(text)
    if steps and time.time() - last_report >= report_every:
        pct, done, total, timing = steps[-1]
        print(f"step {done}/{total} ({pct}%) [{timing}]", flush=True)
        last_report = time.time()
    if (out / f"{name}.safetensors").exists():
        print("TRAINING DONE", flush=True)
        break
    time.sleep(15)
