"""Render every job in experiments/render-queue.json: clean ComfyUI restart, then one Wan clip per job.

The same queue file feeds scripts/render_progress_monitor.py (progress + ETA). Finished outputs are skipped,
so an interrupted batch can be re-run. Run with the ComfyUI venv python:
  ComfyUI/venv/Scripts/python.exe scripts/render_video_queue.py
Job fields: id, output (experiments/video-spike/<spike_id>.mp4), frames (4n+1), start_image,
            motion (key in shot_prompts.video_motion) or prompt, seed (optional, default 111111).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "experiments" / "render-queue.json"
PYTHON = ROOT / "ComfyUI" / "venv" / "Scripts" / "python.exe"


def restart_comfyui():
    # output goes to a file: piping it would hang (detached server inherits the pipe)
    with (ROOT / "experiments" / "restart.log").open("w") as log:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts" / "restart-comfyui-server-clean.ps1")], stdout=log, stderr=log)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    motions = {}
    if queue.get("shot_prompts"):
        motions = json.loads((ROOT / queue["shot_prompts"]).read_text(encoding="utf-8-sig"))["video_motion"]
    failures = 0
    for job in queue["jobs"]:
        output = ROOT / job["output"]
        if output.exists() and output.stat().st_size > 0:
            print(f"have  {job['id']}")
            continue
        prompt = job.get("prompt") or motions[job["motion"]]
        restart_comfyui()
        cmd = [str(PYTHON), "-u", str(ROOT / "scripts" / "video_spike_runner.py"), "--spike-id", output.stem,
               "--start-image", job["start_image"], "--length", str(job["frames"]), "--prompt", prompt,
               "--seed", str(job.get("seed", 111111)), "--out", job["output"]]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = (result.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(f"{job['id']}: {last}")
        failures += not output.exists()
    print(f"Batch done, {failures} failed" if failures else "Batch done, all clips rendered")
    sys.exit(1 if failures else 0)  # lets make_video.py stop instead of upscaling missing clips


if __name__ == "__main__":
    main()
