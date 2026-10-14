"""Generate the music / ambience / chapter-sting layers of a long-form audio story and place them on its timeline.

  python scripts/audio_story_sound_layers.py P006
Reads project.json "story_audio" (layers by script shot ranges) + build/audio/story-timing.json (from
audio_story_narration_joiner.py). Each prompt is rendered once (ACE-Step for music, Stable Audio for ambience and
the sting), cached by prompt+length hash in build/audio-ai/. Writes build/audio/story-layers.json:
{"music": [{file, start, end}], "ambience": [...], "stings": [{file, start}], "sfx": [{file, start, duration}],
 "silences": [{start, end}]}. Needs ComfyUI running.
"""
import hashlib
import json
import sys

from generate_ai_audio import generate
from video_project_config import ROOT, VideoProject, read_json, write_json

MAX_AMBIENCE = 110.0  # Stable Audio 3 Small renders up to ~2 min; longer ambience is looped by the assembler
TAIL = 3.0            # extra seconds so music can fade out over the next chapter's first seconds


def span(timing, shots, total):
    """(start, end) seconds covering script paragraphs shots[0]..shots[1] (first layer starts at 0, last runs to the end)."""
    by_no = {t["shot"]: t for t in timing}
    start = 0.0 if shots[0] == timing[0]["shot"] else by_no[shots[0]]["start"] - 0.5
    end = total if shots[1] == timing[-1]["shot"] else by_no[shots[1]]["end"] + 0.8
    return round(max(start, 0.0), 2), round(min(end, total), 2)


def render(p, kind, prompt, seconds, seed=111111, bpm=80):
    key = hashlib.sha1(f"{kind}|{prompt}|{seconds}|{seed}".encode()).hexdigest()[:10]
    out = p.build / "audio-ai" / f"story-{kind}-{key}.flac"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        took = generate("music" if kind == "music" else "sfx", prompt, seconds, out, seed, bpm)
        print(f"  {kind}: {seconds}s «{prompt[:50]}» ({took}s)")
    return p.rel(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    cfg = p.config["story_audio"]
    timing = read_json(p.voice_dir.parent / "story-timing.json")
    total = timing[-1]["end"] + 3.0
    layers = {"music": [], "ambience": [], "stings": []}
    for m in cfg.get("music", []):
        start, end = span(timing, m["shots"], total)
        f = render(p, "music", m["prompt"], round(end - start + TAIL, 1), m.get("seed", 111111), m.get("bpm", 80))
        layers["music"].append({"file": f, "start": start, "end": end})
    for a in cfg.get("ambience", []):
        start, end = span(timing, a["shots"], total)
        f = render(p, "ambience", a["prompt"], round(min(end - start + 2, MAX_AMBIENCE), 1))
        layers["ambience"].append({"file": f, "start": start, "end": end})
    if (sting := cfg.get("chapter_sting")):
        f = render(p, "sting", sting["prompt"], sting.get("seconds", 6))
        layers["stings"] = [{"file": f, "start": round(max(t["start"] - 1.6, 0), 2)} for t in timing if t["chapter_title"]]
    by_no = {t["shot"]: t for t in timing}
    layers["sfx"] = []  # accents: {"prompt", "shot", "offset" (s after the paragraph starts, may be negative), "seconds"}
    for fx in cfg.get("sfx", []):
        seconds = float(fx.get("seconds", 2.5))
        f = render(p, "sfx", fx["prompt"], max(seconds + 1, 3.0))
        t = by_no[fx["shot"]]
        # "at": fraction of the paragraph (0..1, e.g. 0.7 = when that sentence is read); else "offset" seconds
        start = t["start"] + (fx["at"] * (t["end"] - t["start"]) if "at" in fx else fx.get("offset", 0))
        layers["sfx"].append({"file": f, "start": round(max(start, 0), 2), "duration": seconds})
    # silences: the music bed drops out from `before` s ahead of the paragraph until it ends (+`after`)
    layers["silences"] = [{"start": round(by_no[s["shot"]]["start"] - s.get("before", 1.2), 2),
                           "end": round(by_no[s["shot"]]["end"] + s.get("after", 0.3), 2)} for s in cfg.get("silences", [])]
    write_json(p.voice_dir.parent / "story-layers.json", layers)
    print(f"  {len(layers['music'])} nhạc, {len(layers['ambience'])} âm nền, {len(layers['stings'])} tiếng chuyển chương, "
          f"{len(layers['sfx'])} hiệu ứng, {len(layers['silences'])} khoảnh khắc lặng")


if __name__ == "__main__":
    main()
