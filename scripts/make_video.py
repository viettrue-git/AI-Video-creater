"""One command per video: TTS -> plan -> images -> pick (web) -> videos -> upscale -> assemble.

  python scripts/make_video.py P002                 # run/resume until done (stops for the web picker)
  python scripts/make_video.py P002 status          # what is done / missing
  python scripts/make_video.py P002 --redo SH04 video   # redo one shot's clip (or 'images') then rebuild
  python scripts/make_video.py P002 --only assemble     # run a single stage
Every stage skips work already done, so stopping and re-running is always safe.
Run with the ComfyUI venv python (scripts/make-video.bat does this).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys

from desktop_notification import notify
from image_picker_web_server import run_picker
from video_project_config import ROOT, VideoProject, read_json, write_json

COMFY_PY = ROOT / "ComfyUI" / "venv" / "Scripts" / "python.exe"
TTS_PY = ROOT / "tools" / "vieneu-tts-venv" / "Scripts" / "python.exe"
STAGES = ["tts", "plan", "audio", "images", "pick", "videos", "upscale", "assemble"]


def run(cmd, py=COMFY_PY, check=True):
    """Run a pipeline script, streaming its output; by default stop the whole pipeline if it fails."""
    print("  $", " ".join(str(c) for c in cmd[:3]), "...")
    rc = subprocess.run([str(py), "-u", *map(str, cmd)], cwd=ROOT).returncode
    if rc != 0 and check:
        raise SystemExit(f"\nDỪNG: {cmd[0]} lỗi (mã {rc}). Sửa lỗi rồi chạy lại — phần đã xong sẽ được bỏ qua.")
    return rc


def restart_comfyui():
    with (ROOT / "experiments" / "restart.log").open("w") as log:  # never pipe: detached server keeps it open
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts" / "restart-comfyui-server-clean.ps1")], stdout=log, stderr=log)


def video_seed(shot, state):
    """Seed for the clip; each '--redo SHxx video' bumps it so the redo gives a different take."""
    return shot.get("video_seed", 111111) + 1000 * state.get("redo_count", {}).get(shot["id"], 0)


def clip_fingerprint(shot, pick, frames, seed):
    raw = json.dumps([pick["image"], shot["motion"], frames, seed])
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


# ---- stages ------------------------------------------------------------------------------------
def stage_tts(p):
    timing, script = p.voice_dir / "timing.csv", p.dir / "script.txt"
    if timing.exists() and timing.stat().st_mtime > script.stat().st_mtime:
        return print("  giọng đọc đã có")
    run(["scripts/vietnamese_narration_tts_generator.py", "--script", p.rel(script),
         "--voices", p.config["voice"], "--out", p.rel(p.build / "audio")], py=TTS_PY)


def stage_plan(p):
    timing = p.narration_seconds()
    missing = [s["id"] for s in p.shots
               if s["id"] not in timing or not (p.voice_dir / f"shot_{int(s['id'][2:]):02d}.wav").exists()]
    if missing:  # catch it now, not hours later at assemble time
        raise SystemExit(f"DỪNG: thiếu giọng đọc cho {missing} — kiểm tra [SHOT n] trong script.txt khớp shots.json")
    # lessons learned (P001/P002): these words in motion prompts tend to cause brightness flicker / finger glitches
    risky = re.compile(r"\b(flicker\w*|shimmer\w*|twinkl\w*|strob\w*|fingers?)\b", re.I)
    for shot in p.shots:
        if (m := risky.findall(shot["motion"])):
            print(f"  CẢNH BÁO {shot['id']}: prompt chuyển động có {sorted(set(m))} — dễ gây nhấp nháy/lỗi ngón tay")
    plan = p.plan()
    write_json(p.build / "plan.json", plan)
    for row in plan:
        freeze = row["duration"] - row["frames"] / 24
        note = f"  (giữ khung cuối {freeze:.1f}s — clip tối đa 117 frame)" if freeze > 0.05 else ""
        print(f"  {row['id']}: lời {row['narration']:.2f}s -> shot {row['duration']:.2f}s, {row['frames']} frame{note}")
    print(f"  Tổng: {sum(r['duration'] for r in plan):.1f}s")


def stage_audio(p):
    """AI music/ambience for prompt-based entries in project.json (seconds from the plan; skipped if unchanged)."""
    from generate_ai_audio import generate
    from project_audio_planning import ai_audio_jobs
    jobs = [j for j in ai_audio_jobs(p) if not j["path"].exists()]
    if not jobs:
        return print("  âm thanh AI đã có (hoặc project không dùng prompt âm thanh)")
    restart_comfyui()
    for job in jobs:
        job["path"].parent.mkdir(parents=True, exist_ok=True)
        took = generate(job["kind"], job["prompt"], job["seconds"], job["path"], job["seed"], job["bpm"])
        print(f"  {job['kind']}: {job['seconds']}s '{job['prompt'][:50]}' ({took}s)")


def shots_needing_images(p):
    """Only shots without a pick need candidates (so '--redo SHxx images' re-renders just that shot)."""
    picks = p.picks()
    return [s for s in p.shots if s["id"] not in picks
            and any(not p.image_path(s, seed).exists() for seed in p.seeds_for(s))]


def stage_images(p):
    scenes, ipa = p.scenes_file(), p.character["ipa"]
    lora_args = ["--lora", p.lora["file"], "--lora-strength", p.lora["strength"]] if p.lora else []
    for attempt in (1, 2):  # occasional RAM failures on 16GB: one clean restart + retry, then give up
        missing = shots_needing_images(p)
        if not missing:
            return print("  ảnh đã đủ")
        if attempt == 2:
            print("  thử lại các ảnh bị lỗi sau khi khởi động lại ComfyUI...")
        restart_comfyui()
        for shot in missing:
            run(["scripts/character_consistency_test_runner.py", "--test-id", f"{p.id}-{shot['id']}",
                 "--scenes-file", p.rel(scenes), "--scenes", shot["id"], "--weights", p.ipa_weight(shot),
                 "--seeds", ",".join(map(str, p.seeds_for(shot))), "--weight-type", ipa["weight_type"],
                 "--end-at", ipa["end_at"], "--ref", p.character["ref_image"], *lora_args,
                 "--out-dir", p.rel(p.image_path(shot, 0).parent), "--log-file", ""], check=False)
    still = [s["id"] for s in shots_needing_images(p)]
    if still:
        raise SystemExit(f"DỪNG: vẫn thiếu ảnh cho {still} sau 2 lần thử — xem experiments/comfyui-server-stderr.log")


def stage_pick(p):
    while any(s["id"] not in p.picks() for s in p.shots):
        notify(f"{p.id}: cần bạn chọn ảnh", "Trang chọn ảnh đã mở trên trình duyệt (127.0.0.1:8190).")
        if run_picker(p.id) == 3:  # user asked for more images: render them, then reopen the page
            stage_images(p)


def stage_videos(p):
    plan, picks = {r["id"]: r for r in p.plan()}, p.picks()
    state = read_json(p.build / "state.json", {"clips": {}})
    state.setdefault("clips", {})
    unpicked = [s["id"] for s in p.shots if s["id"] not in picks]
    if unpicked:
        raise SystemExit(f"DỪNG: chưa chọn ảnh cho {unpicked} — chạy lại không có --only để mở trang chọn ảnh")
    jobs = []
    for shot in p.shots:
        sid, clip, upscaled = shot["id"], p.clip_path(shot["id"]), p.upscaled_path(shot["id"])
        if sid not in state["clips"] and upscaled.exists():
            continue  # clip provided from outside the pipeline (e.g. migrated P001): never delete/re-render it
        seed = video_seed(shot, state)
        fp = clip_fingerprint(shot, picks[sid], plan[sid]["frames"], seed)
        if state["clips"].get(sid) == fp and (clip.exists() or upscaled.exists()):
            continue  # unchanged and already rendered (raw clip may have been cleaned up)
        if state["clips"].get(sid) != fp:  # inputs changed: the old take is stale
            clip.unlink(missing_ok=True)
            upscaled.unlink(missing_ok=True)
        if not (ROOT / picks[sid]["image"]).exists():
            raise SystemExit(f"DỪNG: ảnh đã chọn cho {sid} không còn tồn tại: {picks[sid]['image']}")
        state["clips"][sid] = fp
        jobs.append({"id": sid, "output": p.rel(clip), "frames": plan[sid]["frames"],
                     "start_image": picks[sid]["image"], "prompt": shot["motion"], "seed": seed})
    write_json(p.build / "state.json", state)
    if not jobs:
        return print("  video đã đủ")
    from datetime import datetime
    write_json(ROOT / "experiments" / "render-queue.json",  # also read by the progress monitor
               {"batch": f"{p.id} — {len(jobs)} clip", "started": datetime.now().isoformat(timespec="seconds"),
                "jobs": jobs})
    run(["scripts/render_video_queue.py"])


def stage_upscale(p):
    names = [s["id"] for s in p.shots if not p.upscaled_path(s["id"]).exists()]
    if not names:
        return print("  upscale đã đủ")
    run(["scripts/upscale_video_clips_batch.py", "--src", p.rel(p.build / "clips"),
         "--out", p.rel(p.build / "upscaled"), *names])


def stage_assemble(p):
    versions = [int(m.group(1)) for f in (p.dir / "final").glob("*.mp4")
                if (m := re.fullmatch(rf"{p.id}-v(\d+)\.mp4", f.name))]  # ignore e.g. P001-vertical-slice-v1
    output = p.dir / "final" / f"{p.id}-v{max(versions, default=0) + 1}.mp4"
    manifest = p.manifest(output)
    # signature = everything except the output name + modification times of every input file
    inputs = [s["clip"] for s in manifest["shots"]] + [s["narration"] for s in manifest["shots"]]
    signature = json.dumps([{k: v for k, v in manifest.items() if k != "output"},
                            [round((ROOT / f).stat().st_mtime) for f in inputs]], sort_keys=True)
    state = read_json(p.build / "state.json", {})
    last = state.get("last_assembly", {})
    if last.get("signature") == signature and (ROOT / last.get("output", "-")).exists():
        return print(f"  không có gì thay đổi — bản mới nhất vẫn là {last['output']}")
    write_json(p.build / "manifest.json", manifest)
    run(["scripts/assemble_vertical_video_with_narration.py", p.rel(p.build / "manifest.json")])
    state["last_assembly"] = {"signature": signature, "output": manifest["output"]}
    write_json(p.build / "state.json", state)


def status(p):
    picks = p.picks()
    print(f"{p.id} — {p.config.get('title', '')}")
    print(f"  giọng đọc: {'có' if (p.voice_dir / 'timing.csv').exists() else 'chưa'}")
    for s in p.shots:
        imgs = sum(p.image_path(s, seed).exists() for seed in p.seeds_for(s))
        print(f"  {s['id']}: ảnh {imgs}/{len(p.seeds_for(s))} | chọn {'✓' if s['id'] in picks else '-'} | "
              f"clip {'✓' if p.clip_path(s['id']).exists() else '-'} | upscale {'✓' if p.upscaled_path(s['id']).exists() else '-'}")
    finals = sorted((p.dir / "final").glob("*.mp4"))
    print(f"  bản final: {', '.join(f.name for f in finals) or 'chưa có'}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # SystemExit messages are Vietnamese
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("command", nargs="?", default="run", choices=["run", "status"])
    ap.add_argument("--only", choices=STAGES)
    ap.add_argument("--redo", nargs=2, metavar=("SHOT", "images|video"))
    args = ap.parse_args()
    p = VideoProject(args.project)
    if args.command == "status":
        return status(p)
    if args.redo:
        shot = next((s for s in p.shots if s["id"] == args.redo[0].upper()), None)
        if shot is None or args.redo[1] not in ("images", "video"):
            raise SystemExit(f"--redo cần: SHOT trong {[s['id'] for s in p.shots]} và 'images' hoặc 'video'")
        state = read_json(p.build / "state.json", {"clips": {}})
        if args.redo[1] == "video":  # new seed -> a different take of the same shot
            state.setdefault("redo_count", {})[shot["id"]] = state.get("redo_count", {}).get(shot["id"], 0) + 1
            write_json(p.build / "state.json", state)
        if args.redo[1] == "images":
            for seed in p.seeds_for(shot):
                p.image_path(shot, seed).unlink(missing_ok=True)
            picks = p.picks()
            picks.pop(shot["id"], None)
            write_json(p.dir / "picks.json", picks)
        p.clip_path(shot["id"]).unlink(missing_ok=True)
        p.upscaled_path(shot["id"]).unlink(missing_ok=True)
    try:
        for name in ([args.only] if args.only else STAGES):
            print(f"\n== {name.upper()} ==")
            globals()[f"stage_{name}"](p)
    except (SystemExit, Exception) as e:  # tell the user right away instead of failing silently
        notify(f"{p.id}: bị lỗi, đã dừng", str(e).strip()[:200] or type(e).__name__)
        raise
    if not args.only or args.only == "assemble":
        final = read_json(p.build / "state.json", {}).get("last_assembly", {}).get("output", "")
        notify(f"{p.id}: video đã xong", final or "Xem thư mục final.")
    print("\nXong. Xem trạng thái: make_video.py", p.id, "status")


if __name__ == "__main__":
    main()
