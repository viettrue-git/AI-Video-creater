"""Flag library 'sfx' files that are probably MUSIC (common when searching stock sites by keyword).

Heuristics per file (first 60 s, mono 22 kHz): harmonic energy ratio (HPSS), beat regularity (pulse clarity),
integrated loudness from the catalog. Ambience = noisy, no steady beat, quiet; music = tonal and/or rhythmic, loud.
Run with the TTS venv (has librosa): tools/vieneu-tts-venv/Scripts/python.exe scripts/classify_ambience_vs_music.py
"""
import sys

import librosa
import numpy as np

from audio_library import ROOT, read_catalog


def features(path):
    y, sr = librosa.load(path, sr=22050, mono=True, duration=60)
    harmonic, percussive = librosa.effects.hpss(y)
    harmonic_ratio = float(np.sum(harmonic ** 2) / (np.sum(y ** 2) + 1e-9))
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    pulse = librosa.beat.plp(onset_envelope=onset, sr=sr)
    pulse_clarity = float(np.mean(pulse))  # high when there is a steady beat
    return harmonic_ratio, pulse_clarity


def verdict(harmonic_ratio, pulse, lufs):
    score = (harmonic_ratio > 0.65) + (pulse > 0.35) + (lufs > -20)
    return "NHẠC?" if score >= 2 else "ambience"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"{'tag':<18} {'harm':>5} {'pulse':>5} {'LUFS':>6}  kết luận   file")
    for row in read_catalog():
        if row["kind"] != "sfx":
            continue
        h, p = features(ROOT / row["file"])
        print(f"{row['tag']:<18} {h:5.2f} {p:5.2f} {float(row['lufs']):6.1f}  {verdict(h, p, float(row['lufs'])):<9}  "
              f"{row['file'].split('/')[-1][:45]}")


if __name__ == "__main__":
    main()
