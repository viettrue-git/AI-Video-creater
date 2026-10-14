"""Generate Vietnamese narrator audio per shot with VieNeu-TTS and measure each shot's duration.

TTS runs BEFORE rendering: the measured narration length sets each shot's video duration.
Run with the TTS venv (not the ComfyUI one):
  tools/vieneu-tts-venv/Scripts/python.exe scripts/vietnamese_narration_tts_generator.py ^
      --script projects/P001_rung_co/script-narrator-draft-v1.txt --voices "Thiện Minh,Thanh Bình"

Script format: "[SHOT n — description]" header lines, narration text below, "---" ends the script.
Output per voice: <out>/<voice>/shot_NN.wav, full.wav (shots joined with a pause), timing.csv.
"""
import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

# shared helpers (also used by the pipeline): ASCII folder naming + [SHOT n] script parser
from video_project_config import parse_shots, slug

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
ROOT = Path(__file__).resolve().parent.parent


def voiced_segments(audio, rate, win_s=0.05, rel_threshold=0.08):
    """[(start_s, end_s)] of voiced regions from a simple RMS envelope."""
    win = int(win_s * rate)
    rms = np.array([np.sqrt((audio[i:i + win] ** 2).mean()) for i in range(0, len(audio) - win, win)])
    if not len(rms):
        return []
    threshold, segments, start = rms.max() * rel_threshold, [], None
    for i, value in enumerate(rms):
        if value > threshold and start is None:
            start = i
        elif value <= threshold and start is not None:
            segments.append((start * win_s, i * win_s))
            start = None
    if start is not None:
        segments.append((start * win_s, len(rms) * win_s))
    return segments


def trailing_babble_start(audio, rate, min_gap=0.55, max_burst=0.8):
    """Seconds where a short stray sound after a long final silence begins (TTS 'babble'), else None.
    Found on 2026-10-05 (0.15s extra syllable, P001 shot 1) and 2026-10-09 (0.5s burst after a 0.7s gap,
    P003 shot 3 — missed by the old 0.4s/0.4s limits). 0.55/0.8 flags only that file among 39 good ones."""
    segments = voiced_segments(audio, rate)
    if len(segments) < 2:
        return None
    (_, prev_end), (last_start, last_end) = segments[-2], segments[-1]
    if last_start - prev_end >= min_gap and last_end - last_start < max_burst:
        return prev_end
    return None


def load_voice(voice):
    """Preset name -> (name, {}); a custom voice file (.npz from vieneu_blended_voice_demo.py: speaker_emb + codes +
    temperature) -> ({"speaker_emb", "codes"}, {"temperature": t})."""
    if not str(voice).lower().endswith(".npz"):
        return voice, {}
    data = np.load(ROOT / voice)
    return {"speaker_emb": data["speaker_emb"], "codes": data["codes"]}, {"temperature": float(data["temperature"])}


def synthesize_clean(tts, text, voice, retries=4):
    """Infer, regenerating when trailing babble is detected; last resort: cut the stray tail."""
    rate = tts.sample_rate
    voice, options = load_voice(voice)
    for attempt in range(1, retries + 1):
        audio = np.asarray(tts.infer(text, voice=voice, **options), dtype=np.float32)
        cut = trailing_babble_start(audio, rate)
        if cut is None:
            return audio, "ok" if attempt == 1 else f"ok after {attempt} tries"
    return audio[: int((cut + 0.15) * rate)], f"trimmed trailing babble at {cut:.2f}s"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--script", required=True)
    p.add_argument("--voices", default="Thiện Minh", help="comma list of preset voice names")
    p.add_argument("--out", default=None, help="default: <script folder>/audio-tts-tests")
    p.add_argument("--pause", type=float, default=0.6, help="seconds of silence between shots in full.wav")
    p.add_argument("--only-shot", type=int, default=0,
                   help="regenerate just this shot number; other shots reuse their existing wav (keeps their timing)")
    args = p.parse_args()

    from vieneu import Vieneu  # slow import: keep after arg parsing so --help is instant

    shots = parse_shots(ROOT / args.script)
    if not shots:
        sys.exit("No [SHOT n] blocks with text found in the script")
    out_root = Path(args.out) if args.out else (ROOT / args.script).parent / "audio-tts-tests"
    tts = Vieneu()
    rate = tts.sample_rate

    any_failed = False
    for voice in [v.strip() for v in args.voices.split(",") if v.strip()]:
        voice_dir = out_root / slug(Path(voice).stem if voice.lower().endswith(".npz") else voice)
        voice_dir.mkdir(parents=True, exist_ok=True)
        pieces, rows, started = [], [], time.time()
        for no, desc, text in shots:
            existing = voice_dir / f"shot_{no:02d}.wav"
            if args.only_shot and no != args.only_shot and existing.exists():
                audio = sf.read(existing, dtype="float32")[0]
                rows.append({"shot": no, "seconds": round(len(audio) / rate, 2), "description": desc, "text": text})
                pieces += [audio, np.zeros(int(args.pause * rate), dtype=np.float32)]
                continue
            try:
                audio, qc = synthesize_clean(tts, text, voice)
            except Exception as e:  # keep other shots/voices going; report which one failed
                print(f"  ! {voice} shot {no} failed: {e}")
                continue
            if qc != "ok":
                print(f"  {voice} shot {no}: {qc}")
            sf.write(voice_dir / f"shot_{no:02d}.wav", audio, rate)
            seconds = round(len(audio) / rate, 2)
            rows.append({"shot": no, "seconds": seconds, "description": desc, "text": text})
            pieces += [audio, np.zeros(int(args.pause * rate), dtype=np.float32)]
        if len(rows) < len(shots):
            # no timing.csv for an incomplete voice: the pipeline must regenerate it, not plan with gaps
            any_failed = True
            (voice_dir / "timing.csv").unlink(missing_ok=True)
            print(f"  ! {voice}: {len(shots) - len(rows)} shot(s) failed — timing.csv not written")
            continue
        sf.write(voice_dir / "full.wav", np.concatenate(pieces[:-1]), rate)
        with (voice_dir / "timing.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["shot", "seconds", "description", "text"])
            writer.writeheader()
            writer.writerows(rows)
        total = sum(r["seconds"] for r in rows) + args.pause * (len(rows) - 1)
        print(f"{voice}: {len(rows)} shots, {total:.1f}s audio, generated in {time.time() - started:.0f}s -> {voice_dir}")
    if any_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
