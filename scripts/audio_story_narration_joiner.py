"""Join per-paragraph narration (build/audio/<voice>/shot_NN.wav) into one long story track with paced pauses.

  python scripts/audio_story_narration_joiner.py P006
Long-form audio stories (history & mythology channel): a short breath between paragraphs, longer silence around
chapter titles (script blocks whose description contains "tiêu đề") and before the ending ("Kết").
Writes build/audio/story-narration.wav + build/audio/story-timing.json ([{shot, start, end, description, text}])
which later steps (music bed, subtitles, name cards) use.
"""
import json
import sys
import wave

import numpy as np

from video_project_config import VideoProject, parse_shots, write_json

PAUSE = 0.7            # between paragraphs
CHAPTER_BEFORE = 2.2   # silence before a chapter title (room for a music bridge)
CHAPTER_AFTER = 1.4    # after the title, before the chapter starts
ENDING_BEFORE = 1.8    # before the first "Kết" paragraph


def read_wav(path):
    with wave.open(str(path)) as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype={2: np.int16, 4: np.int32}[width])
    return rate, data.reshape(-1, channels).mean(axis=1).astype(np.int16 if width == 2 else np.int32)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    shots = parse_shots(p.dir / "script.txt")
    pieces, timing, t, rate, ending_seen = [], [], 0.0, None, False
    for i, (no, desc, text) in enumerate(shots):
        r, audio = read_wav(p.voice_dir / f"shot_{no:02d}.wav")
        rate = rate or r
        is_title = "tiêu đề" in desc.lower()
        before = 0.0 if i == 0 else PAUSE
        if is_title:
            before = CHAPTER_BEFORE
        elif desc.startswith("Kết") and not ending_seen:
            before, ending_seen = ENDING_BEFORE, True
        elif i > 0 and "tiêu đề" in shots[i - 1][1].lower():
            before = CHAPTER_AFTER
        if before:
            pieces.append(np.zeros(int(before * rate), dtype=audio.dtype))
            t += before
        timing.append({"shot": no, "start": round(t, 2), "end": round(t + len(audio) / rate, 2),
                       "description": desc, "text": text, "chapter_title": is_title})
        pieces.append(audio)
        t += len(audio) / rate
    out = p.voice_dir.parent / "story-narration.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(pieces[0].dtype.itemsize)
        w.setframerate(rate)
        w.writeframes(np.concatenate(pieces).tobytes())
    write_json(p.voice_dir.parent / "story-timing.json", timing)
    print(f"  {len(shots)} đoạn -> {p.rel(out)} ({t / 60:.1f} phút)")


if __name__ == "__main__":
    main()
