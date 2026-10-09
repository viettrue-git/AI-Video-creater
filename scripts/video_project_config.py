"""Load a video project (projects/<id>/) and derive everything the pipeline stages need.

Project folder: project.json, script.txt, shots.json, picks.json (written by the picker), build/ (generated),
final/ (MP4s). Character definitions live in characters/<name>.json and are shared across projects.
"""
import csv
import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 24
MIN_FRAMES, MAX_FRAMES = 49, 117  # Wan 5B: 117 frames is the longest clip proven stable on 16GB RAM
DEFAULT_SEEDS = [111111, 222222, 333333, 444444, 555555, 666666, 777777, 888888]


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


SHOT_HEADER = re.compile(r"^\[SHOT\s+(\d+)\s*[—-]?\s*(.*?)\]\s*$")


def parse_shots(script_path):
    """Return [(shot_no, description, narration_text)] from a '[SHOT n — description]' narrator script."""
    shots, current = [], None
    for line in Path(script_path).read_text(encoding="utf-8-sig").splitlines():
        if line.strip() == "---":
            break
        header = SHOT_HEADER.match(line.strip())
        if header:
            current = [int(header.group(1)), header.group(2), []]
            shots.append(current)
        elif current is not None and line.strip():
            current[2].append(line.strip())
    return [(no, desc, " ".join(text)) for no, desc, text in shots if text]


def slug(name):
    """ASCII folder name ('Thanh Bình' -> 'thanh-binh'): diacritics break some FFmpeg/shell tooling."""
    ascii_name = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = ascii_name.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def frames_for(seconds):
    """Smallest 4n+1 frame count covering `seconds` at 24 fps, clamped to the stable range."""
    frames = max(math.ceil(seconds * FPS), MIN_FRAMES)
    frames += (1 - frames % 4) % 4  # round up to 4n+1
    return min(frames, MAX_FRAMES)


class VideoProject:
    def __init__(self, project_id):
        project_id = project_id.upper()
        matches = [d for d in (ROOT / "projects").glob(f"{project_id}*")
                   if d.name == project_id or d.name.startswith(f"{project_id}_")]  # P001 must not match P0010
        if len(matches) != 1 or not (matches[0] / "project.json").exists():
            raise SystemExit(f"Không tìm thấy đúng 1 project projects/{project_id}_*/project.json (thấy {len(matches)})")
        self.dir = matches[0]
        self.config = read_json(self.dir / "project.json")
        self.id = self.config.get("id", project_id)
        self.character = read_json(ROOT / "characters" / f"{self.config['character']}.json")
        self.shots = read_json(self.dir / "shots.json")["shots"]
        self.build = self.dir / "build"
        # LoRA mode (opt-in per project): character LoRA replaces IP-Adapter (IPA pulled poses to the front-facing ref)
        self.lora = self.character.get("lora") if self.config.get("use_lora") else None

    def ipa_weight(self, shot):
        return 0.0 if self.lora else float(shot["ipa_weight"])

    def rel(self, path):
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")

    # ---- paths -------------------------------------------------------------------------------
    @property
    def voice_dir(self):
        return self.build / "audio" / slug(self.config["voice"])

    def image_path(self, shot, seed):
        folder = "images-lora" if self.lora else "images"  # keep LoRA candidates apart from older IPA ones
        return self.build / folder / f"{shot['id']}_w{self.ipa_weight(shot):.2f}_s{seed}.png"

    def clip_path(self, shot_id):
        return self.build / "clips" / f"{shot_id}.mp4"

    def upscaled_path(self, shot_id):
        return self.build / "upscaled" / f"{shot_id}.mp4"

    # ---- picks / seeds ------------------------------------------------------------------------
    def picks(self):
        return read_json(self.dir / "picks.json", {})

    def seeds_for(self, shot):
        extra = read_json(self.build / "rerolls.json", {}).get(shot["id"], 0)
        count = self.config.get("seeds_per_shot", 4) + extra
        return [DEFAULT_SEEDS[i] if i < len(DEFAULT_SEEDS) else 111111 * (i + 1) for i in range(count)]

    # ---- timing plan --------------------------------------------------------------------------
    def narration_seconds(self):
        timing = self.voice_dir / "timing.csv"
        with timing.open(encoding="utf-8-sig") as f:
            return {f"SH{int(r['shot']):02d}": float(r["seconds"]) for r in csv.DictReader(f)}

    def plan(self):
        """Per shot: narration, duration (narration + pad, + tail on the last shot), frames, start time."""
        narration, pad = self.narration_seconds(), self.config.get("pad_seconds", 0.9)
        plan, start = [], 0.0
        for i, shot in enumerate(self.shots):
            seconds = narration.get(shot["id"], 0.0)
            duration = round(seconds + pad + (self.config.get("tail_seconds", 0) if i == len(self.shots) - 1 else 0), 2)
            plan.append({"id": shot["id"], "narration": seconds, "duration": duration,
                         "frames": frames_for(duration), "start": round(start, 2)})
            start += duration
        return plan

    # ---- generated inputs for the existing scripts ----------------------------------------------
    def scenes_file(self):
        """Scenes JSON in the format character_consistency_test_runner.py reads."""
        path = self.build / "scenes.json"
        overrides = {s["id"]: s["character_override"] for s in self.shots if "character_override" in s}
        block = self.character["character_block"]
        if self.lora:  # trigger word only on the full character block (not on hand/landscape overrides)
            block = f"{self.lora['trigger']}, {block}"
        write_json(path, {"character_block": block,
                          "style_block": self.character["style_block"], "negative": self.character["negative"],
                          "scenes": {s["id"]: s["scene"] for s in self.shots}, "character_overrides": overrides})
        return path

    @staticmethod
    def resolve_audio(entry, kind="sfx"):
        """{'tag': 'forest', ...} -> adds 'file' + loudness-based 'volume' from the shared audio library.
        {'file': ...} without 'volume' -> volume measured from the file's loudness (e.g. AI-generated audio)."""
        if not entry or ("file" in entry and "volume" in entry):
            return entry
        from audio_library import find, gain, measure  # lazy: only needed when something must be resolved
        if "file" in entry:
            _, lufs = measure(ROOT / entry["file"])
            return {**entry, "volume": gain({"kind": kind, "lufs": lufs})}
        row = find(entry["tag"], entry.get("index", 0))
        return {**entry, "file": row["file"], "volume": entry.get("volume", gain(row))}

    def manifest(self, output):
        """Assembler manifest from plan + upscaled clips + narration + project audio settings."""
        from project_audio_planning import ai_audio_jobs, segment_bounds
        plan = {p["id"]: p for p in self.plan()}
        total = sum(p["duration"] for p in plan.values())
        # prompt-based (AI) entries -> the file the audio stage generated for them
        generated = {id(job["entry"]): self.rel(job["path"]) for job in ai_audio_jobs(self)}
        with_file = lambda e: {**e, "file": generated[id(e)]} if e and id(e) in generated else e  # noqa: E731
        music = self.resolve_audio(with_file(self.config.get("music")), kind="music")
        manifest = {"output": self.rel(output), "fade_out": self.config.get("fade_out", 1.5),
                    "music": music["file"] if music else None,
                    "music_start": music.get("start", 0) if music else 0,
                    "music_volume": music.get("volume", 0.3) if music else 0, "ambience": [], "shots": []}
        for amb in (self.resolve_audio(with_file(a)) for a in self.config.get("ambience", [])):
            start, end = segment_bounds(plan, amb, total)
            manifest["ambience"].append({"file": amb["file"], "start": start, "end": end,
                                         "volume": amb.get("volume", 0.3), "fade": amb.get("fade", 1.5)})
        for shot in self.shots:
            entry = {"id": shot["id"], "clip": self.rel(self.upscaled_path(shot["id"])),
                     "narration": self.rel(self.voice_dir / f"shot_{int(shot['id'][2:]):02d}.wav"),
                     "duration": plan[shot["id"]]["duration"]}
            if shot.get("eq"):
                entry["eq"] = shot["eq"]
            manifest["shots"].append(entry)
        return manifest
