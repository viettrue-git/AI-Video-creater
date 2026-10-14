"""Check a video project before rendering (fields, shot count, ~30 s length, prompts, trigger, narrator person, audio).

  python scripts/validate_video_project.py P005             # report LỖI (errors) / CẢNH BÁO (warnings), exit 1 on errors
  python scripts/validate_video_project.py P005 --approve   # no errors -> record the user's script approval
Approval stores a fingerprint of script.txt + shots.json + project audio; make_video refuses to run if the script
was edited after approval (projects without "script_approved" are not gated).
"""
import argparse
import csv
import hashlib
import json
import re
import sys

from video_project_config import (MAX_FRAMES, FPS, RISKY_MOTION, ROOT, VideoProject, parse_shots, read_json,
                                  write_json)

TOTAL_RANGE = (25.0, 33.0)  # seconds; target ~30 s Shorts/TikTok (P003 was approved at 26 s)
SHOT_RANGE = (5, 8)
WARN_WORDS = re.compile(r"\b(extreme close-up|text|signs?|letters|words|talking|speaking|says|said)\b", re.I)
THIRD_PERSON = re.compile(r"\b(anh ấy|cậu ấy|chú cáo|cô ấy|nó)\b", re.I)


POST_PRODUCTION_KEYS = {"at", "trim_start", "trim_end", "clip_audio"}  # clip tuning after review: no re-approval


def without_tuning(value):
    if isinstance(value, dict):
        return {k: without_tuning(v) for k, v in value.items() if k not in POST_PRODUCTION_KEYS}
    return [without_tuning(v) for v in value] if isinstance(value, list) else value


def fingerprint(p):
    """What the user approved: narration, shot prompts/dialogue, audio prompts, voice/character (any edit -> re-approve);
    post-production clip tuning (dub timing, trims, muting) is excluded."""
    data = (p.dir / "script.txt").read_text(encoding="utf-8-sig") + json.dumps(without_tuning(p.shots), sort_keys=True)
    approved_config = {k: v for k, v in p.config.items() if k != "script_approved"}
    data += json.dumps([approved_config, p.voice, p.narration], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(data.encode("utf-8")).hexdigest()[:12]


def check_approved(p):
    """Called by make_video before any stage/--redo: stop if the project changed after the user approved it."""
    approved = p.config.get("script_approved")
    if approved and approved != fingerprint(p):
        raise SystemExit("DỪNG: kịch bản/prompt đã bị sửa sau khi duyệt — chạy validate_video_project.py "
                         f"{p.id} --approve sau khi bạn duyệt lại")


def syllables(text):
    return len(re.findall(r"\w+", text))


def check_config(p):
    errors = [f"project.json thiếu '{key}'" for key in ("id", "title", "character", "music") if not p.config.get(key)]
    if p.config.get("music", {}).get("prompt") and "instrumental" not in p.config["music"]["prompt"]:
        errors.append("music.prompt phải có 'instrumental' (nhạc không lời, không lấn giọng đọc)")
    return errors


def check_muse(p):
    """Muse mode: Muse renders the picture (and dialogue unless dubbed), so only shots.json + muse-pack.txt are checked."""
    errors, warnings = check_config(p), []
    shot_ids = [s.get("id") for s in p.shots]
    if shot_ids != [f"SH{n:02d}" for n in range(1, len(shot_ids) + 1)]:
        errors.append(f"shots.json phải đánh số SH01..SHnn liên tục: {shot_ids}")
    pack = p.dir / "muse-pack.txt"
    scenes = set(re.findall(r"^SC(\d{2})\b",pack.read_text(encoding="utf-8"), re.M)) if pack.exists() else set()
    if not pack.exists():
        errors.append("thiếu muse-pack.txt")
    elif scenes != {sid[2:] for sid in shot_ids}:
        errors.append(f"muse-pack.txt có cảnh SC{sorted(scenes)} không khớp shots.json {shot_ids}")
    cast = p.character.get("cast", {})
    for shot in p.shots:
        lines = shot.get("dialogue", [])
        for line in (d for d in lines if isinstance(d, dict)):  # dubbed line: needs a cast voice + text
            if not line.get("text") or not cast.get(line.get("who"), {}).get("voice"):
                errors.append(f"{shot.get('id')}: câu lồng tiếng cần 'text' và 'who' có voice trong cast: {line}")
        count = syllables(" ".join(d["text"] if isinstance(d, dict) else d for d in lines))
        if count > 30:
            warnings.append(f"{shot.get('id')}: {count} âm tiết thoại — Muse dễ nói vội/cắt câu (nên ≤ 30 mỗi cảnh)")
    return errors, warnings, []


def check(p):
    if p.muse:
        return check_muse(p)
    errors, warnings = check_config(p), []
    cfg, rate = p.config, p.narration.get("syllables_per_second", 4.5)
    shot_ids = [s.get("id") for s in p.shots]
    for amb in cfg.get("ambience", []):
        if amb.get("prompt") and "no music" not in amb["prompt"]:
            warnings.append(f"ambience '{amb['prompt'][:40]}…' nên có 'no music'")
        for key in ("from_shot", "to_shot"):
            if key in amb and amb[key] not in shot_ids:
                errors.append(f"ambience {key}={amb[key]} không có trong shots.json")

    for fx in cfg.get("sfx", []):
        if not fx.get("prompt") or fx.get("shot") not in shot_ids:
            errors.append(f"sfx cần 'prompt' và 'shot' có trong shots.json: {fx}")
        elif "no music" not in fx["prompt"]:
            warnings.append(f"sfx '{fx['prompt'][:40]}…' nên có 'no music'")

    script = parse_shots(p.dir / "script.txt")
    numbers = [no for no, _, _ in script]
    if not SHOT_RANGE[0] <= len(script) <= SHOT_RANGE[1]:
        errors.append(f"cần {SHOT_RANGE[0]}–{SHOT_RANGE[1]} shot có lời, đang có {len(script)}")
    if numbers != list(range(1, len(numbers) + 1)):
        errors.append(f"[SHOT n] phải đánh số liên tục từ 1: {numbers}")
    if shot_ids != [f"SH{n:02d}" for n in numbers]:
        errors.append(f"shots.json {shot_ids} không khớp các [SHOT n] trong script.txt {numbers}")

    if p.narration.get("person") == "first":
        text = " ".join(t for _, _, t in script)
        if p.narration.get("self") and not re.search(rf"\b{re.escape(p.narration['self'])}\b", text, re.I):
            errors.append(f"nhân vật kể ngôi thứ nhất: lời đọc phải xưng '{p.narration['self']}'")
        name = p.narration.get("name")  # narrator calling himself by name instead of 'tớ'
        if (m := THIRD_PERSON.findall(text) + (re.findall(re.escape(name), text) if name else [])):
            warnings.append(f"lời đọc ngôi thứ nhất nhưng có {sorted(set(m))}")

    trigger = p.lora["trigger"] if p.lora else None
    for shot in p.shots:
        sid = shot.get("id", "?")
        for key in ("scene", "motion"):
            value = shot.get(key, "")
            if not value:
                errors.append(f"{sid}: thiếu '{key}'")
            elif not value.isascii():
                errors.append(f"{sid}: '{key}' phải là tiếng Anh không dấu")
        if "stylized 3D animated movie" not in shot.get("motion", ""):
            warnings.append(f"{sid}: motion nên kết thúc bằng 'stylized 3D animated movie, ...'")
        if (m := RISKY_MOTION.findall(shot.get("motion", ""))):
            warnings.append(f"{sid}: motion có {sorted(set(m))} — dễ nhấp nháy/lỗi tay chân")
        if (m := WARN_WORDS.findall(shot.get("scene", "") + " " + shot.get("motion", ""))):
            warnings.append(f"{sid}: có {sorted(set(m))} — không lip-sync/không chữ trong ảnh")
        if not p.lora and "ipa_weight" not in shot:
            errors.append(f"{sid}: thiếu 'ipa_weight' (cần khi không dùng LoRA)")
        if trigger and trigger in shot.get("scene", ""):
            errors.append(f"{sid}: đừng viết trigger '{trigger}' trong scene (pipeline tự thêm)")
    if p.lora and not (ROOT / "ComfyUI" / "models" / "loras" / p.lora["file"]).exists():
        errors.append(f"không thấy LoRA ComfyUI/models/loras/{p.lora['file']}")
    return errors, warnings, length_table(p, script, rate)


def length_table(p, script, rate):
    """Estimated (or measured, if TTS already ran) seconds per shot and in total."""
    measured = {}
    timing = p.voice_dir / "timing.csv"
    if timing.exists() and timing.stat().st_mtime > (p.dir / "script.txt").stat().st_mtime:  # not stale
        with timing.open(encoding="utf-8-sig") as f:
            measured = {int(r["shot"]): float(r["seconds"]) for r in csv.DictReader(f)}
    pad, tail, rows = p.config.get("pad_seconds", 0.9), p.config.get("tail_seconds", 0), []
    for i, (no, _, text) in enumerate(script):
        estimate = syllables(text) / rate
        shot = measured.get(no, estimate) + pad + (tail if i == len(script) - 1 else 0)
        rows.append((no, syllables(text), estimate, measured.get(no), shot))
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--approve", action="store_true")
    args = ap.parse_args()
    p = VideoProject(args.project)
    errors, warnings, rows = check(p)
    max_shot = MAX_FRAMES / FPS
    print(f"{p.id} — {p.config.get('title')} (giọng {p.voice}, {p.narration.get('syllables_per_second', 4.5)} âm tiết/giây)")
    for no, count, estimate, measured, shot in rows:
        real = f" | đo thật {measured:.1f}s" if measured is not None else ""
        hold = "  (dài hơn clip tối đa, sẽ giữ khung cuối)" if shot > max_shot else ""
        print(f"  SHOT {no}: {count} âm tiết ≈ {estimate:.1f}s lời{real} -> shot {shot:.1f}s{hold}")
    total = sum(r[4] for r in rows)
    if p.muse:
        print(f"  Muse: {len(p.shots)} cảnh, thời lượng do clip Muse quyết định")
    else:
        print(f"  Tổng ước tính: {total:.1f}s (mục tiêu {TOTAL_RANGE[0]:.0f}–{TOTAL_RANGE[1]:.0f}s)")
    if rows and not TOTAL_RANGE[0] <= total <= TOTAL_RANGE[1]:
        errors.append(f"tổng {total:.1f}s ngoài khoảng {TOTAL_RANGE[0]:.0f}–{TOTAL_RANGE[1]:.0f}s — thêm/bớt lời")
    for w in warnings:
        print(f"  CẢNH BÁO: {w}")
    for e in errors:
        print(f"  LỖI: {e}")
    if errors:
        sys.exit(1)
    if args.approve:
        config = read_json(p.dir / "project.json")
        config["script_approved"] = fingerprint(p)
        write_json(p.dir / "project.json", config)
        print(f"Đã ghi nhận duyệt kịch bản ({config['script_approved']}).")
    else:
        print("Hợp lệ.")


if __name__ == "__main__":
    main()
