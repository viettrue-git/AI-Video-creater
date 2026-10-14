"""Create a new video project folder (next free P-number) with skeleton files, or list a series' episodes.

  python scripts/new_video_project.py --title "Tiểu Mão đi câu cá" --character fox-tieu-mao-v1 --series tieu-mao
  python scripts/new_video_project.py --list-series tieu-mao
The writer (Claude via the video-idea skill) then fills script.txt / shots.json / project.json and runs
scripts/validate_video_project.py. Never overwrites an existing folder.
"""
import argparse
import re
import sys

from video_project_config import ROOT, read_json, slug, write_json

PROJECTS = ROOT / "projects"


def next_project_id():
    """P + (highest existing 3-digit number + 1); any folder counts, so ids are never reused."""
    numbers = [int(m.group(1)) for d in PROJECTS.iterdir() if (m := re.match(r"P(\d{3})(?:_|$)", d.name))]
    return f"P{max(numbers, default=0) + 1:03d}"


def series_episodes(series):
    """[(id, episode, title, summary, has_final)] of projects whose project.json has "series": series."""
    rows = []
    for config_path in sorted(PROJECTS.glob("P*/project.json")):
        try:
            config = read_json(config_path)
        except ValueError as e:  # one broken project.json must not block scaffolding
            print(f"  (bỏ qua {config_path.parent.name}: project.json lỗi — {e})")
            continue
        if config.get("series") == series:
            has_final = any((config_path.parent / "final").glob("*.mp4"))
            rows.append((config.get("id"), config.get("episode"), config.get("title"), config.get("summary", ""), has_final))
    return sorted(rows, key=lambda r: r[1] or 0)


def create(title, character, series):
    character_file = ROOT / "characters" / f"{character}.json"
    if not character_file.exists():
        sys.exit(f"Không có nhân vật characters/{character}.json")
    has_lora = "lora" in read_json(character_file)
    project_id = next_project_id()
    name = slug(title)[:40].strip("-") or "untitled"  # short ASCII folder name (Windows path limit)
    folder = PROJECTS / f"{project_id}_{name.replace('-', '_')}"
    folder.mkdir()  # raises if it exists: never overwrite
    episode = (max((r[1] or 0 for r in series_episodes(series)), default=0) + 1) if series else None
    config = {"id": project_id, "title": title, "character": character, "use_lora": has_lora,
              "pad_seconds": 0.9, "tail_seconds": 2.0, "seeds_per_shot": 4, "fade_out": 1.5,
              "music": {"prompt": "", "bpm": 90}, "ambience": []}
    if series:
        config.update({"series": series, "episode": episode, "summary": ""})
    write_json(folder / "project.json", config)
    (folder / "script.txt").write_text(
        "".join(f"[SHOT {n} — ]\n\n" for n in range(1, 7)) + "---\n", encoding="utf-8")
    write_json(folder / "shots.json", {"shots": []})
    return project_id, folder, episode


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title")
    ap.add_argument("--character")
    ap.add_argument("--series", default="")
    ap.add_argument("--list-series", metavar="SERIES")
    args = ap.parse_args()
    if args.list_series:
        rows = series_episodes(args.list_series)
        for pid, episode, title, summary, has_final in rows:
            print(f"{pid} | tập {episode} | {title} | {summary} | {'đã có video' if has_final else 'chưa xong'}")
        return print(f"({len(rows)} tập)")
    if not (args.title and args.character):
        ap.error("cần --title và --character (hoặc --list-series)")
    project_id, folder, episode = create(args.title, args.character, args.series)
    print(f"{project_id} -> {folder.relative_to(ROOT)}" + (f" (series {args.series}, tập {episode})" if episode else ""))


if __name__ == "__main__":
    main()
