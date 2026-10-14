"""Automatic QC of a project's newest final MP4: per-shot frame strip, brightness flicker, cut alignment.

  python scripts/final_video_qc_report.py P003
Writes experiments/<id>-qc-<final name>.jpg (3 frames per shot) and prints one line per shot.
Flicker = frame-to-frame brightness jumps > 1.5 (excluding the cut frames and the final fade-out).
"""
import sys
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

from video_project_config import ROOT, VideoProject

FPS = 24


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    final = sorted((p.dir / "final").glob(f"{p.id}-v*.mp4"), key=lambda f: f.stat().st_mtime)[-1]
    plan = p.plan()  # computed (Muse projects have no plan.json: no TTS/plan stage)
    fade = float(p.config.get("fade_out", 1.5))
    frames = [f.to_image() for f in av.open(str(final)).decode(video=0)]
    small = [np.asarray(f.convert("L").resize((54, 96)), np.float32) for f in frames]
    lum = np.array([s.mean() for s in small])
    diffs = np.array([np.abs(a - b).mean() for a, b in zip(small, small[1:])])
    cuts = [i + 1 for i, d in enumerate(diffs) if d > 12]
    fade_start = int((len(frames) / FPS - fade) * FPS)

    w = 150
    h = round(w * frames[0].height / frames[0].width)
    sheet = Image.new("RGB", (w * 3, (h + 18) * len(plan)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    print(f"{final.name}: {len(frames) / FPS:.2f}s, {len(frames)} frames, detected cuts at "
          f"{[round(c / FPS, 2) for c in cuts]}")
    for row, shot in enumerate(plan):
        a = int(shot["start"] * FPS) + 2  # skip the cut frame itself (rounding puts it at +1)
        b = min(int((shot["start"] + shot["duration"]) * FPS) - 1, fade_start if row == len(plan) - 1 else 10 ** 9)
        jumps = int((np.abs(np.diff(lum[a:b])) > 1.5).sum()) if b > a + 1 else 0
        cut_ok = row == 0 or any(abs(c / FPS - shot["start"]) < 0.1 for c in cuts)
        print(f"  {shot['id']}: {shot['duration']:.2f}s | brightness {lum[a:b].min():.0f}-{lum[a:b].max():.0f} | "
              f"flicker jumps {jumps} | cut {'ok' if cut_ok else 'not detected (soft transition?)'}")
        y = row * (h + 18)
        draw.text((4, y + 2), f"{shot['id']}  flicker={jumps}", fill=(230, 230, 230))
        for col, k in enumerate((a, (a + b) // 2, b)):
            sheet.paste(frames[min(k, len(frames) - 1)].resize((w, h)), (col * w, y + 18))
    out = ROOT / "experiments" / f"{p.id}-qc-{final.stem}.jpg"
    sheet.save(out, quality=85)
    print(f"QC sheet: {out}")


if __name__ == "__main__":
    main()
