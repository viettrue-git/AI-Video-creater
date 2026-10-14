"""Dub Muse clips with fixed VieNeu voices per character (Muse makes picture + sound effects, never the voices).

  tools/vieneu-tts-venv/Scripts/python.exe scripts/muse_dialogue_dubbing_with_character_voices.py P010
Why: Muse speaks every line of a clip in ONE voice, crammed at the start, and picks a new voice per clip.
shots.json "dialogue" items as objects switch a shot to dubbing:
  {"who": "SAU RIENG", "text": "Dọn đồ rồi đi đi!", "at": 6.2}   # at = seconds into the (untrimmed) clip
Voices come from the character file's "cast": {"SAU RIENG": {"voice": "Hải Đăng"}, ...}. Faster pacing: "trim_start"/"trim_end" keep
only the part of the 10 s clip with the lines (the assembler cuts both). Optional per shot "clip_audio": 0.0 mutes the clip's own sound (e.g. a clip where Muse spoke anyway; default 1.0).
Output per shot: build/audio/muse-clip/shot_NN.wav (clip sound + voices, clip length) — the track the assembler
uses — and build/dub-timing.json {shot: [[start, end, text], ...]} (clip time) for exact subtitles.
Each line is cached in build/audio/dub/ by voice + text, so re-runs only synthesize edited lines.
"""
import hashlib
import subprocess
import sys

import numpy as np
import soundfile as sf

from assemble_vertical_video_with_narration import find_ffmpeg
from video_project_config import VideoProject, read_json, write_json

RATE = 48000  # same as muse_clip_ingest's extracted clip audio
GAP = 0.15  # min seconds between two lines; a line that would overlap is pushed later


def dubbed_shots(p):
    return [s for s in p.shots if any(isinstance(d, dict) for d in s.get("dialogue", []))]


def clip_sound(p, sid, seconds):
    """Clip's own audio as float32 stereo at RATE (silence if it has none), exactly `seconds` long."""
    raw = subprocess.run([find_ffmpeg(), "-v", "error", "-i", str(p.clip_path(sid)), "-vn", "-ac", "2", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
    return fit(audio, int(seconds * RATE))


def fit(audio, frames):
    return audio[:frames] if len(audio) >= frames else np.vstack([audio, np.zeros((frames - len(audio), 2), np.float32)])


def resample(mono, src_rate):
    target = np.arange(0, len(mono) / src_rate, 1 / RATE)
    return np.interp(target, np.arange(len(mono)) / src_rate, mono).astype(np.float32)


def line_audio(p, voice, text, tts_holder):
    """Mono float32 at RATE for one line, from cache or freshly synthesized."""
    key = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:12]
    cache = p.build / "audio" / "dub" / f"{key}.wav"
    if not cache.exists():
        if not tts_holder:
            from vieneu import Vieneu  # slow import: only when a line is not cached yet
            tts_holder.append(Vieneu())
        from vietnamese_narration_tts_generator import synthesize_clean
        audio, qc = synthesize_clean(tts_holder[0], text, voice)
        if qc != "ok":
            print(f"    {voice}: {qc}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        sf.write(cache, resample(audio, tts_holder[0].sample_rate), RATE)
    return sf.read(cache, dtype="float32")[0]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    cast = p.character.get("cast", {})
    clips = read_json(p.build / "muse-clips.json", {})
    timing, tts_holder = {}, []
    for shot in dubbed_shots(p):
        sid = shot["id"]
        if sid not in clips:  # make_video only dubs once every clip is in; a manual run can preview the first ones
            print(f"  {sid}: chưa có clip, bỏ qua")
            continue
        seconds = clips[sid]["seconds"]
        mix = clip_sound(p, sid, seconds) * float(shot.get("clip_audio", 1.0))
        cursor, rows = 0.0, []
        for line in shot["dialogue"]:
            voice = cast.get(line.get("who"), {}).get("voice")
            if not voice:
                raise SystemExit(f"{sid}: '{line.get('who')}' chưa có voice trong cast của characters/{p.config['character']}.json")
            audio = line_audio(p, voice, line["text"], tts_holder)
            start = max(float(line.get("at", cursor)), cursor)
            end = start + len(audio) / RATE
            keep_from, keep_to = float(shot.get("trim_start", 0)), seconds - float(shot.get("trim_end", 0))
            if start < keep_from or end > keep_to:  # outside the part of the clip the assembler keeps
                print(f"  CẢNH BÁO {sid}: câu '{line['text'][:30]}' {start:.1f}-{end:.1f}s nằm ngoài đoạn giữ "
                      f"{keep_from:.1f}-{keep_to:.1f}s (bị cắt)")
            begin = int(start * RATE)
            piece = audio[: max(0, len(mix) - begin)]
            mix[begin:begin + len(piece)] += piece[:, None]
            rows.append([round(start, 2), round(min(end, seconds), 2), line["text"]])
            cursor = end + GAP
        peak = np.abs(mix).max()
        if peak > 0.98:  # voices on top of loud effects: scale down instead of clipping
            mix *= 0.98 / peak
        out = p.voice_dir / f"shot_{int(sid[2:]):02d}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(out, mix, RATE, subtype="PCM_16")
        timing[sid] = rows
        print(f"  {sid}: {len(rows)} câu " + ", ".join(f"{a:.1f}-{b:.1f}s" for a, b, _ in rows))
    write_json(p.build / "dub-timing.json", timing)


if __name__ == "__main__":
    main()
