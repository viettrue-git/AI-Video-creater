"""AI-upscale several clips in one go: stops ComfyUI first (GPU must be free), skips clips already done.

  ComfyUI/venv/Scripts/python.exe scripts/upscale_video_clips_batch.py --src experiments/video-spike ^
      --out experiments/upscaled MVP3-SH01 MVP3-SH02 ...
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", default="experiments/video-spike")
    p.add_argument("--out", default="experiments/upscaled")
    p.add_argument("names", nargs="+", help="clip names without .mp4")
    args = p.parse_args()

    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "stop-comfyui-server.ps1")])
    failed = 0
    for name in args.names:
        src, dst = ROOT / args.src / f"{name}.mp4", ROOT / args.out / f"{name}.mp4"
        if dst.exists() and dst.stat().st_size > 0:
            print(f"have  {name}")
            continue
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "upscale_video_clip_realesrgan.py"), str(src), str(dst)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        print((result.stdout.strip().splitlines() or [result.stderr.strip()[-300:]])[-1])
        failed += result.returncode != 0
    print(f"Upscale done, {failed} failed" if failed else "Upscale done, all OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
