"""Review step for dubbed Muse episodes: contact sheets of every clip + detect clips where Muse spoke anyway.

  tools/asr-venv/Scripts/python.exe scripts/muse_clip_review_sheet_and_speech_check.py P011 [--apply]
- build/review/sheet-SH01-SH05.jpg ...: 1 frame per second (10 per clip), 5 clips per sheet -> pick 'at' / trims.
- Speech check: Whisper with VAD on each clip's own sound; a segment with no_speech_prob < 0.5 is real speech
  (murmurs Muse adds despite "no voices"). Whisper's "Hãy subscribe..." on rain is filtered out by VAD/no_speech_prob.
- --apply: set "clip_audio": 0.0 in shots.json for dubbed shots with speech (post-production key, no re-approval).
Report: build/review/review.json {shot: {"speech": [[start, end, text]], "muted": bool}}.
"""
import argparse
import json
import subprocess
import sys

import numpy as np

from assemble_vertical_video_with_narration import find_ffmpeg
from video_project_config import ROOT, VideoProject, read_json, write_json

MODEL, MODEL_DIR = "small", ROOT / "tools" / "asr-models"
PER_SHEET = 5


def clip_audio_16k(path):
    raw = subprocess.run([find_ffmpeg(), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def contact_sheets(p, ids, out):
    """1 fps x 10 frames per clip in a row, PER_SHEET clips stacked per image."""
    ffmpeg = find_ffmpeg()
    for start in range(0, len(ids), PER_SHEET):
        group = ids[start:start + PER_SHEET]
        inputs = sum((["-i", str(p.clip_path(s))] for s in group), [])
        rows = "".join(f"[{i}:v]fps=1,scale=130:232,setsar=1,tile=10x1[r{i}];" for i in range(len(group)))
        stack = "".join(f"[r{i}]" for i in range(len(group))) + (f"vstack={len(group)}" if len(group) > 1 else "null")
        sheet = out / f"sheet-{group[0]}-{group[-1]}.jpg"
        subprocess.run([ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", rows + stack, "-frames:v", "1", str(sheet)],
                       check=True)
        print(f"  {p.rel(sheet)}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--apply", action="store_true", help="mute dubbed shots whose clip contains speech")
    args = ap.parse_args()
    from faster_whisper import WhisperModel  # heavy import after arg parsing
    p = VideoProject(args.project)
    clips = read_json(p.build / "muse-clips.json", {})
    ids = [s["id"] for s in p.shots if s["id"] in clips]
    out = p.build / "review"
    out.mkdir(parents=True, exist_ok=True)
    contact_sheets(p, ids, out)
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=str(MODEL_DIR))
    report, muted = {}, []
    for shot in p.shots:
        if shot["id"] not in clips:
            continue
        segments, _ = model.transcribe(clip_audio_16k(p.clip_path(shot["id"])), language="vi", vad_filter=True)
        speech = [[round(s.start, 1), round(s.end, 1), s.text.strip()] for s in segments if s.no_speech_prob < 0.5]
        dubbed = any(isinstance(d, dict) for d in shot.get("dialogue", []))
        mute = bool(speech) and dubbed and shot.get("clip_audio", 1.0) != 0.0
        if mute and args.apply:
            shot["clip_audio"] = 0.0
            muted.append(shot["id"])
        report[shot["id"]] = {"speech": speech, "muted": shot.get("clip_audio", 1.0) == 0.0}
        print(f"  {shot['id']}: {'CÓ TIẾNG NÓI ' + str(speech) if speech else 'chỉ tiếng nền'}")
    write_json(out / "review.json", report)
    if muted:  # rewrite shots.json keeping its layout keys order; clip_audio is not part of the approval fingerprint
        data = read_json(p.dir / "shots.json")
        data["shots"] = p.shots
        (p.dir / "shots.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"  tắt tiếng clip: {muted}")


if __name__ == "__main__":
    main()
