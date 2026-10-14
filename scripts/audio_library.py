"""Shared audio library: music + ambience/SFX picked by tag, with loudness-based gain.

Workflow for the user: drop downloaded files into library/audio/inbox/<tag>/ (folder name = tag, e.g. forest,
rain, music-inspiring); optional license screenshot with the same base name (.png). Then:
  python scripts/audio_library.py ingest   # move into library/audio/<kind>/<tag>/, measure, add to catalog.csv
  python scripts/audio_library.py list     # what is in the library
Projects reference tags in project.json; the pipeline resolves tag -> file and computes volume from LUFS.
"""
import csv
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library" / "audio"
CATALOG = LIB / "catalog.csv"
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
COLUMNS = ["tag", "kind", "file", "duration_s", "lufs", "license_proof", "source", "added"]
# Pre-mix loudness targets that matched the hand-balanced P001 v4 mix (music ×0.35, forest ×3.0, wind ×2.5)
TARGET_LUFS = {"music": -22.0, "sfx": -30.0, "oneshot": -20.0}  # oneshot: per-shot SFX, not ducked


def kind_of(tag):
    return "music" if tag.startswith("music-") else "sfx"


def measure(path):
    """(duration seconds, integrated LUFS) via ffmpeg ebur128."""
    from assemble_vertical_video_with_narration import find_ffmpeg
    out = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", str(path), "-af", "ebur128=framelog=quiet",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0.0
    return round(seconds, 1), float(lufs[-1]) if lufs else -30.0


def read_catalog():
    if not CATALOG.exists():
        return []
    with CATALOG.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_catalog(rows):
    LIB.mkdir(parents=True, exist_ok=True)
    with CATALOG.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def ingest():
    rows, added = read_catalog(), 0
    for tag_dir in sorted(p for p in (LIB / "inbox").glob("*") if p.is_dir()):
        tag = tag_dir.name.lower()
        for audio in sorted(f for f in tag_dir.iterdir() if f.suffix.lower() in AUDIO_EXT):
            dest_dir = LIB / kind_of(tag) / tag
            dest_dir.mkdir(parents=True, exist_ok=True)
            proof = audio.with_suffix(".png")
            dest = dest_dir / audio.name
            shutil.move(str(audio), dest)
            if proof.exists():
                shutil.move(str(proof), dest_dir / proof.name)
            seconds, lufs = measure(dest)
            rows.append({"tag": tag, "kind": kind_of(tag), "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
                         "duration_s": seconds, "lufs": lufs,
                         "license_proof": "yes" if proof.exists() or (dest_dir / proof.name).exists() else "MISSING",
                         "source": "pixabay/youtube (see proof)", "added": date.today().isoformat()})
            added += 1
            print(f"  + [{tag}] {audio.name}: {seconds}s, {lufs} LUFS")
    write_catalog(rows)
    print(f"Ingested {added} file(s); library now has {len(rows)}.")


def find(tag, index=0):
    """Catalog row for a tag (index picks among several files of the same tag)."""
    matches = [r for r in read_catalog() if r["tag"] == tag.lower()]
    if not matches:
        raise SystemExit(f"Thư viện âm thanh chưa có tag '{tag}' — thả file vào library/audio/inbox/{tag}/ rồi chạy ingest")
    return matches[index % len(matches)]


def gain(row):
    """Linear volume bringing this file to the kind's pre-mix loudness target."""
    return round(10 ** ((TARGET_LUFS[row["kind"]] - float(row["lufs"])) / 20), 2)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    if command == "ingest":
        return ingest()
    for row in read_catalog():
        print(f"  [{row['tag']:<18}] {row['duration_s']:>6}s {row['lufs']:>6} LUFS  gain {gain(row):>5}  "
              f"proof:{row['license_proof']:<7} {Path(row['file']).name}")


if __name__ == "__main__":
    main()
