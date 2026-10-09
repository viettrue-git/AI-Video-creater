"""Show video render progress + estimated time left for the current batch (Vietnamese output).

Reads experiments/render-queue.json (jobs + expected output files) and the ComfyUI log progress bar.
  python scripts/render_progress_monitor.py          # print once
  python scripts/render_progress_monitor.py --watch  # refresh every 10 s (Ctrl+C to quit)
Time per job is estimated from RTX 3060 measurements (2026-10-05): ~0.4*frames-4 s/step x 20 steps
+ ~2.5 min overhead (restart, model load, VAE decode). The running job uses the live s/step instead.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "experiments" / "render-queue.json"
LOG = ROOT / "experiments" / "comfyui-server-stderr.log"
STEPS, OVERHEAD_S = 20, 150
BAR = re.compile(r"(\d+)%\|[^|]*\|\s*(\d+)/(\d+) \[(\d+:\d+(?::\d+)?)<(\d+:\d+(?::\d+)?),\s*([\d.]+)(s/it|it/s)\]")


def to_seconds(text):
    seconds = 0
    for part in text.split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def fmt(seconds):
    m, s = divmod(int(max(seconds, 0)), 60)
    return f"{m // 60}h{m % 60:02d}m" if m >= 60 else f"{m}m{s:02d}s"


def estimate_job_seconds(frames):
    return max(0.4 * frames - 4, 8) * STEPS + OVERHEAD_S


def last_progress_bar():
    """(step, total, elapsed_s, remaining_s, s_per_step) from the newest progress bar in the log, or None."""
    if not LOG.exists():
        return None
    with LOG.open("rb") as f:
        f.seek(max(0, LOG.stat().st_size - 20000))
        tail = f.read().decode("utf-8", "replace").replace("\r", "\n")
    matches = BAR.findall(tail)
    if not matches:
        return None
    _, step, total, elapsed, remaining, rate, unit = matches[-1]
    per_step = float(rate) if unit == "s/it" else 1 / max(float(rate), 1e-6)
    return int(step), int(total), to_seconds(elapsed), to_seconds(remaining), per_step


def report():
    if not QUEUE.exists():
        return "Không có lô render nào (thiếu experiments/render-queue.json)."
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    started = datetime.fromisoformat(queue["started"]).timestamp()
    done = [j for j in queue["jobs"] if (ROOT / j["output"]).exists() and (ROOT / j["output"]).stat().st_mtime >= started]
    pending = [j for j in queue["jobs"] if j not in done]
    lines = [f"Lô: {queue['batch']}", f"Xong {len(done)}/{len(queue['jobs'])} clip", ""]
    lines += [f"  [x] {j['id']}" for j in done]
    left = 0.0
    if pending:
        current, rest = pending[0], pending[1:]
        bar = last_progress_bar()
        log_age = time.time() - LOG.stat().st_mtime if LOG.exists() else 1e9
        if bar and bar[0] < bar[1] and log_age < 120:
            step, total, _, remaining, per_step = bar
            current_left = remaining + 60  # + VAE decode / save
            lines.append(f"  [>] {current['id']}  — bước {step}/{total}, {per_step:.0f} giây/bước, còn ~{fmt(current_left)}")
        else:
            current_left = estimate_job_seconds(current["frames"])
            lines.append(f"  [>] {current['id']}  — đang khởi động / nạp model / giải mã (ước ~{fmt(current_left)})")
        left = current_left + sum(estimate_job_seconds(j["frames"]) for j in rest)
        lines += [f"  [ ] {j['id']}  (ước ~{fmt(estimate_job_seconds(j['frames']))})" for j in rest]
        finish = datetime.now() + timedelta(seconds=left)
        lines += ["", f"Còn lại ước tính: ~{fmt(left)}  → xong khoảng {finish:%H:%M}"]
    else:
        lines += ["", "Tất cả clip đã xong."]
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--watch" not in sys.argv:
        print(report())
        return
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"TIẾN ĐỘ RENDER — cập nhật {datetime.now():%H:%M:%S} (Ctrl+C để thoát)\n")
        print(report())
        time.sleep(10)


if __name__ == "__main__":
    main()
