"""Burned-in subtitles for Muse episodes: exact script lines, timed by Whisper on each clip's own audio.

  tools/asr-venv/Scripts/python.exe scripts/muse_dialogue_subtitles.py P005
Text comes from shots.json "dialogue" (the lines Muse was told to speak) — never from speech recognition, so no
spelling mistakes. Whisper (faster-whisper "small", MIT, CPU int8) only gives word timings; each line takes its
share of the recognized words in order (by syllable count). Output: build/subtitles.srt in final-video time.
Dubbed shots (dialogue items {"who", "text", "at"}) need no Whisper: build/dub-timing.json has the exact times.
"""
import re
import sys
import wave

import numpy as np

from video_project_config import ROOT, VideoProject, read_json

MODEL = "small"
MODEL_DIR = ROOT / "tools" / "asr-models"
MIN_SHOW, MAX_SHOW = 0.8, 6.0  # seconds a line stays on screen


def load_16k_mono(wav):
    """16-bit PCM wav (ingest writes 48 kHz stereo) -> float32 16 kHz mono, as Whisper expects.
    Decoded here because faster-whisper's PyAV decoder breaks with the installed av version."""
    with wave.open(str(wav)) as w:
        rate, channels = w.getframerate(), w.getnchannels()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    audio = audio.reshape(-1, channels).mean(axis=1)
    target = np.arange(0, len(audio) / rate, 1 / 16000)
    return np.interp(target, np.arange(len(audio)) / rate, audio).astype(np.float32)


def speech_words(model, wav):
    """[(start, end)] of recognized words (Vietnamese: one per syllable)."""
    segments, _ = model.transcribe(load_16k_mono(wav), language="vi", word_timestamps=True, vad_filter=True)
    return [(w.start, w.end) for s in segments for w in (s.words or [])]


def time_lines(lines, words):
    """[(start, end)] per line: lines take consecutive recognized words in proportion to their syllables."""
    if not words:
        return []
    sizes = [max(len(re.findall(r"\w+", line)), 1) for line in lines]
    total, timed, used = sum(sizes), [], 0
    for i, size in enumerate(sizes):
        last = len(words) if i == len(sizes) - 1 else min(len(words), used + max(1, round(size * len(words) / total)))
        chunk = words[used:last] or words[-1:]
        timed.append((chunk[0][0], chunk[-1][1]))
        used = last
    return timed


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    plan = {r["id"]: r for r in p.plan()}
    dub_timing = read_json(p.build / "dub-timing.json", {})
    model, cues = None, []
    for shot in p.shots:
        lines = shot.get("dialogue") or []
        if not lines:
            continue
        trim, row = float(shot.get("trim_start", 0)), plan[shot["id"]]
        if shot["id"] in dub_timing:  # dubbed: exact times, no speech recognition
            timed = [(a, b) for a, b, _ in dub_timing[shot["id"]]]
            lines = [text for _, _, text in dub_timing[shot["id"]]]
            print(f"  {shot['id']}: {len(lines)} câu lồng tiếng")
        else:
            if model is None:
                from faster_whisper import WhisperModel  # heavy import, only when a shot needs it
                model = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=str(MODEL_DIR))
            words = speech_words(model, p.voice_dir / f"shot_{int(shot['id'][2:]):02d}.wav")
            timed = time_lines(lines, words)
            print(f"  {shot['id']}: {len(lines)} câu, nghe được {len(words)} âm tiết")
        for line, (start, end) in zip(lines, timed):
            start, end = start - trim, max(end - trim, start - trim + MIN_SHOW)
            if end <= 0 or start >= row["duration"]:
                continue  # spoken inside the trimmed part
            start, end = max(start, 0), min(end + 0.25, start + MAX_SHOW, row["duration"])
            cues.append((row["start"] + start, row["start"] + end, line))
    cues.sort()
    for i in range(len(cues) - 1):  # never overlap: end a cue where the next one starts
        if cues[i][1] > cues[i + 1][0]:
            cues[i] = (cues[i][0], cues[i + 1][0], cues[i][2])
    out = p.build / "subtitles.srt"
    out.write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(cues, 1)),
                   encoding="utf-8")
    print(f"  {len(cues)} dòng phụ đề -> {p.rel(out)}")


if __name__ == "__main__":
    main()
