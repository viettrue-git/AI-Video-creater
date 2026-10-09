"""Overall progress (%) + ETA for making one video, across all pipeline stages (Vietnamese output).

  python scripts/project_progress_monitor.py            # newest project being built
  python scripts/project_progress_monitor.py P002 --watch
Stage weights are time estimates measured on this PC (RTX 3060): image ~25 s, video clip ~(0.4*frames-4)*20 s
+ 150 s overhead (live step progress from the ComfyUI log is used for the running clip), upscale ~1 s/frame.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from render_progress_monitor import LOG as COMFY_LOG, estimate_job_seconds, fmt, last_progress_bar
from video_project_config import ROOT, VideoProject, read_json

IMAGE_S, UPSCALE_S_PER_FRAME, ASSEMBLE_S, TTS_S = 25, 1.0, 15, 15


def gpu_temperature():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def newest_project_id():
    logs = sorted((ROOT / "projects").glob("*/build/make_video.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1].parent.parent.name.split("_")[0] if logs else None


def report(p):
    plan = {r["id"]: r for r in read_json(p.build / "plan.json", [])}
    picks, lines = p.picks(), []
    frames = {s["id"]: plan.get(s["id"], {}).get("frames", 81) for s in p.shots}
    stages = []  # (name, total_s, done_s, detail)

    tts_done = (p.voice_dir / "timing.csv").exists()
    stages.append(("Giọng đọc", TTS_S, TTS_S if tts_done else 0, "xong" if tts_done else "chưa"))

    picks_now = p.picks()
    open_shots = [s for s in p.shots if s["id"] not in picks_now]  # picked shots need no candidates
    want = sum(len(p.seeds_for(s)) for s in open_shots)
    have = sum(p.image_path(s, seed).exists() for s in open_shots for seed in p.seeds_for(s))
    stages.append(("Ảnh", want * IMAGE_S, have * IMAGE_S, f"{have}/{want} ảnh"))

    picked = sum(s["id"] in picks for s in p.shots)
    stages.append(("Chọn ảnh (bạn)", 0, 0, f"{picked}/{len(p.shots)} shot"))

    clip_total = sum(estimate_job_seconds(f) for f in frames.values())
    clip_done = sum(estimate_job_seconds(frames[s["id"]]) for s in p.shots
                    if p.clip_path(s["id"]).exists() or p.upscaled_path(s["id"]).exists())
    running = ""
    bar = last_progress_bar()
    log_fresh = COMFY_LOG.exists() and time.time() - COMFY_LOG.stat().st_mtime < 120
    pending = [s for s in p.shots if not (p.clip_path(s["id"]).exists() or p.upscaled_path(s["id"]).exists())]
    if picked == len(p.shots) and pending and bar and log_fresh and bar[0] < bar[1]:
        step, total, _, remaining, per_step = bar
        est = estimate_job_seconds(frames[pending[0]["id"]])
        clip_done += max(est - remaining - 60, 0)
        running = f" — đang {pending[0]['id']}: bước {step}/{total}, còn ~{fmt(remaining + 60)}"
    n_clips = len(p.shots) - len(pending)
    stages.append(("Video", clip_total, min(clip_done, clip_total), f"{n_clips}/{len(p.shots)} clip{running}"))

    up_total = sum(frames.values()) * UPSCALE_S_PER_FRAME
    up_done = sum(frames[s["id"]] for s in p.shots if p.upscaled_path(s["id"]).exists()) * UPSCALE_S_PER_FRAME
    stages.append(("Upscale", up_total, up_done, f"{sum(p.upscaled_path(s['id']).exists() for s in p.shots)}/{len(p.shots)}"))

    last = read_json(p.build / "state.json", {}).get("last_assembly", {})
    final_ok = bool(last) and (ROOT / last.get("output", "-")).exists() and up_done >= up_total
    stages.append(("Ghép video", ASSEMBLE_S, ASSEMBLE_S if final_ok else 0, last.get("output", "chưa") if final_ok else "chưa"))

    total = sum(t for _, t, _, _ in stages)
    done = sum(d for _, _, d, _ in stages)
    pct = 100 * done / total if total else 0
    bar_txt = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    lines += [f"{p.id} — {p.config.get('title', '')}", f"[{bar_txt}] {pct:.0f}%", ""]
    for name, t, d, detail in stages:
        all_picked = picked == len(p.shots)
        mark = "x" if (t and d >= t) or ((name.startswith("Chọn") or name == "Ảnh") and all_picked) else (">" if d else " ")
        lines.append(f"  [{mark}] {name:<15} {detail}")
    temp = gpu_temperature()
    if temp is not None:
        lines.append(f"\n  GPU: {temp}°C" + ("  ⚠ nóng — để máy chỗ thoáng" if temp >= 87 else ""))
    if have == want and picked < len(p.shots):
        lines += ["", "⏸  ĐANG CHỜ BẠN CHỌN ẢNH: http://127.0.0.1:8190"]
    elif done < total:
        finish = datetime.now() + timedelta(seconds=total - done)
        lines += ["", f"Còn lại ước tính: ~{fmt(total - done)} → xong khoảng {finish:%H:%M}"]
    else:
        lines += ["", "✅ Video đã hoàn thành."]
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    project_id = args[0] if args else newest_project_id()
    if not project_id:
        sys.exit("Chưa có project nào đang làm (thiếu build/make_video.log)")
    while True:
        p = VideoProject(project_id)
        if "--watch" in sys.argv:
            os.system("cls" if os.name == "nt" else "clear")
            print(f"TIẾN ĐỘ LÀM VIDEO — cập nhật {datetime.now():%H:%M:%S} (Ctrl+C để thoát)\n")
        print(report(p))
        if "--watch" not in sys.argv:
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
