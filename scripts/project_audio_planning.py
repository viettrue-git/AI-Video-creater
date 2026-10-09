"""Where/how long each project audio layer plays, and the file an AI-generated layer is saved to.

project.json audio entries may use one of:
  {"prompt": "campfire crackling at night", "from_shot": "SH04", "to_shot": "SH06"}  -> AI-generated (Stable Audio 3 / ACE-Step)
  {"tag": "forest", ...}                                                              -> shared library
  {"file": "path.mp3", ...}                                                           -> explicit file
"music" is one entry (whole video); "ambience" is a list of entries placed by shot range.
"""
import hashlib

MIN_AI_SECONDS, MAX_SFX_SECONDS, TAIL_MARGIN = 10.0, 120.0, 2.0  # Stable Audio 3 Small-SFX: up to 2:00


def segment_bounds(plan, entry, total):
    """(start, end) seconds of an ambience layer: from 0.8 s before from_shot to 0.9 s after to_shot."""
    start = plan[entry["from_shot"]]["start"] - 0.8 if entry.get("from_shot") else 0.0
    end = plan[entry["to_shot"]]["start"] + plan[entry["to_shot"]]["duration"] + 0.9 if entry.get("to_shot") else total
    return max(start, 0.0), min(end, total)


def ai_audio_jobs(project):
    """One job per prompt-based entry: {kind, prompt, seconds, seed, bpm, path}. Path changes when the prompt does."""
    plan = {p["id"]: p for p in project.plan()}
    total = sum(p["duration"] for p in plan.values())
    entries = [("music", project.config.get("music"))] + [("sfx", a) for a in project.config.get("ambience", [])]
    jobs = []
    for kind, entry in entries:
        if not entry or "prompt" not in entry:
            continue
        if kind == "music":
            seconds = total + TAIL_MARGIN
        else:
            start, end = segment_bounds(plan, entry, total)
            seconds = min(max(end - start + TAIL_MARGIN, MIN_AI_SECONDS), MAX_SFX_SECONDS)
        seconds = round(seconds, 1)
        seed = entry.get("seed", 111111)
        key = hashlib.sha1(f"{kind}|{entry['prompt']}|{seconds}|{seed}|{entry.get('bpm', 90)}".encode()).hexdigest()[:10]
        jobs.append({"kind": kind, "entry": entry, "prompt": entry["prompt"], "seconds": seconds, "seed": seed,
                     "bpm": entry.get("bpm", 90), "path": project.build / "audio-ai" / f"{kind}-{key}.flac"})
    return jobs
