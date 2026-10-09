"""Video Spike: run one Wan image-to-video clip through ComfyUI and record the numbers the plan asks for
(render minutes, peak VRAM, peak system RAM). Appends one row to experiments/video-spike-log.csv.

Example:
  ComfyUI/venv/Scripts/python.exe scripts/video_spike_runner.py --spike-id V01 ^
      --start-image experiments/C01-hood-color-fix/S1_w0.50_s111111.png --length 121
"""
import argparse
import csv
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

from comfyui_api_client import DEFAULT_SERVER, ComfyUIClient, ComfyUIError
from workflow_template_utils import load_workflow_template, with_inputs

ROOT = Path(__file__).resolve().parent.parent
# gait/finger terms added 2026-10-05 after user review (stiff back-view walk, odd ring-finger gesture)
DEFAULT_NEGATIVE = ("static, frozen, blurry, low quality, distorted face, deformed hands, extra limbs, "
                    "morphing, flickering, jitter, text, watermark, subtitles, "
                    "sliding feet, stiff legs, unnatural gait, moonwalking, "
                    "finger twitching, moving fingers, extra fingers, weird hand gestures")
LOG_COLUMNS = ["date", "spike_id", "model", "width", "height", "length", "fps", "steps", "cfg", "seed",
               "render_minutes", "peak_vram_gb", "peak_ram_used_gb", "oom_or_crash", "motion_1_5",
               "identity_1_5", "video_file", "prompt", "notes"]


class ResourcePeakSampler:
    """Polls nvidia-smi (VRAM) and Windows memory counters (RAM) in a background thread."""

    def __init__(self, interval=2.0):
        self.interval, self.peak_vram_mb, self.peak_ram_mb = interval, 0, 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _sample(self):
        try:
            vram = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
            self.peak_vram_mb = max(self.peak_vram_mb, int(vram))
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            pass
        try:
            import ctypes

            class MemStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MemStatus(dwLength=ctypes.sizeof(MemStatus))
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            self.peak_ram_mb = max(self.peak_ram_mb, (ms.ullTotalPhys - ms.ullAvailPhys) // 2**20)
        except (OSError, AttributeError):
            pass

    def _run(self):
        while not self._stop.is_set():
            self._sample()
            self._stop.wait(self.interval)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spike-id", required=True)
    p.add_argument("--start-image", required=True)
    p.add_argument("--prompt", default="the young man walks slowly forward along the forest path, gentle camera "
                                        "dolly forward, sunlight rays flicker through the trees, leaves sway, "
                                        "stylized 3D animated movie, smooth natural motion")
    p.add_argument("--negative", default=DEFAULT_NEGATIVE)
    p.add_argument("--width", type=int, default=704)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--length", type=int, default=121, help="frames, must be 4n+1")
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--cfg", type=float, default=5.0)
    p.add_argument("--seed", type=int, default=111111)
    p.add_argument("--workflow", default="workflows/api/wan22-ti2v-5b-image-to-video-v1.json")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--out", default=None, help="output mp4 (default experiments/video-spike/<spike-id>.mp4)")
    return p.parse_args()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    if (args.length - 1) % 4:
        sys.exit("--length must be 4n+1 (e.g. 49, 81, 121)")
    client = ComfyUIClient(args.server, timeout=120)
    if not client.is_alive():
        sys.exit(f"ComfyUI is not running at {args.server}")
    template = load_workflow_template(ROOT / args.workflow)
    model = template["1"]["inputs"]["unet_name"]
    out_path = ROOT / (args.out or f"experiments/video-spike/{args.spike_id}.mp4")
    workflow = with_inputs(template, {
        "IN_PositivePrompt": {"text": args.prompt},
        "IN_NegativePrompt": {"text": args.negative},
        "IN_StartImage": {"image": client.upload_image(ROOT / args.start_image)},
        "IN_VideoSize": {"width": args.width, "height": args.height, "length": args.length},
        "IN_Sampler": {"seed": args.seed, "steps": args.steps, "cfg": args.cfg},
        "IN_Fps": {"fps": args.fps},
        "OUT_Video": {"filename_prefix": f"spike/{args.spike_id}"},
    })

    error, started = "", time.time()
    with ResourcePeakSampler() as sampler:
        try:
            entry = client.wait_for_result(client.queue_prompt(workflow), poll_seconds=5, max_wait_seconds=4 * 3600)
            if not client.download_images(entry, [out_path]):
                raise ComfyUIError("finished but returned no video")
        except ComfyUIError as e:
            error = str(e)[:300]
    minutes = round((time.time() - started) / 60, 1)
    row = {"date": date.today().isoformat(), "spike_id": args.spike_id, "model": model, "width": args.width,
           "height": args.height, "length": args.length, "fps": args.fps, "steps": args.steps, "cfg": args.cfg,
           "seed": args.seed, "render_minutes": minutes, "peak_vram_gb": round(sampler.peak_vram_mb / 1024, 1),
           "peak_ram_used_gb": round(sampler.peak_ram_mb / 1024, 1), "oom_or_crash": error or "no",
           "video_file": str(out_path.relative_to(ROOT)) if not error else "", "prompt": args.prompt}
    log_path = ROOT / "experiments" / "video-spike-log.csv"
    is_new = not log_path.exists() or log_path.stat().st_size == 0
    with log_path.open("a", newline="", encoding="utf-8-sig" if is_new else "utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    print(("FAILED: " + error) if error else f"OK {out_path} in {minutes} min",
          f"| peak VRAM {row['peak_vram_gb']}GB | peak RAM used {row['peak_ram_used_gb']}GB")
    if error:
        sys.exit(1)


if __name__ == "__main__":
    main()
