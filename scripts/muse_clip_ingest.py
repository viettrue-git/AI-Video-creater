"""Bring Muse-made clips (projects/<id>/muse-inbox/SC01.mp4 ...) into the pipeline (project.json "video_source": "muse").

  python scripts/muse_clip_ingest.py P005          # ingest what is there, report missing scenes
  python scripts/muse_clip_ingest.py P005 --watch  # wait until every scene is in the inbox, then run make_video
  (dubbed episodes: --watch stops after the review sheets + speech check instead, so dub timing is set first)
Per scene SCnn -> shot SHnn: the clip is copied to build/clips/SHnn.mp4 and its own audio (Muse dialogue + sound
effects) is extracted to build/audio/clip/shot_NN.wav, which the assembler uses in place of TTS narration.
Durations go to build/muse-clips.json (the timing plan for Muse projects).
A scene Muse refuses to animate can come as still images SCnn-1.png, SCnn-2.png ... -> Ken Burns clip SCnn-ken-burns.mp4.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from assemble_vertical_video_with_narration import find_ffmpeg
from desktop_notification import notify
from muse_still_images_to_ken_burns_clip import IMAGE_EXTENSIONS, build_ken_burns_clip
from video_project_config import ROOT, VideoProject, read_json, write_json

ASR_PY = ROOT / "tools" / "asr-venv" / "Scripts" / "python.exe"  # faster-whisper (review speech check)
MIN_PORTRAIT_RATIO = 1.5  # height / width; 9:16 = 1.78 — landscape clips would be cropped to a blurry sliver


def probe(path):
    """(width, height, seconds, has_audio) via ffprobe."""
    ffmpeg = Path(find_ffmpeg())
    ffprobe = str(ffmpeg.with_name(ffmpeg.name.replace("ffmpeg", "ffprobe")))  # same folder as ffmpeg
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8").stdout
    data = json.loads(out or "{}")
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return video.get("width", 0), video.get("height", 0), float(data.get("format", {}).get("duration", 0)), has_audio


def unzip_inbox(inbox, extensions=(".mp4", *IMAGE_EXTENSIONS)):
    """Muse can deliver a whole episode as one .zip: extract its media files flat into the inbox, then archive the zip."""
    for archive in inbox.glob("*.zip"):
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                name = Path(member.filename).name  # flatten folders; never write outside the inbox
                target = inbox / name
                if name.lower().endswith(extensions) and not member.is_dir():
                    if target.exists():  # never overwrite a clip the user already put there
                        target = inbox / f"{target.stem}-from-zip{target.suffix}"
                    target.write_bytes(z.read(member))
        archive.rename(archive.with_suffix(".zip.done"))


def stills_to_clips(inbox):
    """Scenes delivered as still images (SC03-1.png, SC03-2.png; no real SC03 clip) -> SC03-ken-burns.mp4."""
    scenes = {}
    for f in sorted(inbox.iterdir()):
        if f.suffix.lower() in IMAGE_EXTENSIONS and (m := re.match(r"sc(\d+)", f.name, re.I)):
            scenes.setdefault(int(m.group(1)), []).append(f)
    for no, images in scenes.items():
        out = inbox / f"SC{no:02d}-ken-burns.mp4"
        real = [c for c in inbox.glob(f"[sS][cC]{no:02d}*.mp4") if c != out]
        if real or (out.exists() and out.stat().st_mtime > max(i.stat().st_mtime for i in images)):
            continue  # a real Muse clip wins; an up-to-date Ken Burns clip is reused
        build_ken_burns_clip(images, out)
        print(f"  SC{no:02d}: {len(images)} ảnh -> {out.name} (Ken Burns)")


def inbox_clips(p):
    """{shot_id: path} for SCnn*.mp4 files in the inbox (SC01.mp4, sc01-meeting.mp4, ... all match SH01).
    Name order: 'SC03.mp4' sorts after 'SC03-ken-burns.mp4', so a real clip replaces the stills version."""
    found = {}
    unzip_inbox(p.dir / "muse-inbox")
    stills_to_clips(p.dir / "muse-inbox")
    for f in sorted((p.dir / "muse-inbox").glob("*.mp4")):
        if (m := re.match(r"sc(\d+)", f.name, re.I)):
            found[f"SH{int(m.group(1)):02d}"] = f
    return found


def ingest(p):
    """Copy new/changed clips into build/, extract their audio; return (ingested ids, missing ids, problems)."""
    clips, state = inbox_clips(p), read_json(p.build / "muse-clips.json", {})
    ffmpeg, done, problems = find_ffmpeg(), [], []
    for shot in p.shots:
        sid, src = shot["id"], clips.get(shot["id"])
        if not src:
            continue
        stamp = f"{src.name}|{src.stat().st_size}|{int(src.stat().st_mtime)}"
        if state.get(sid, {}).get("source") == stamp:
            continue  # unchanged since last ingest
        width, height, seconds, has_audio = probe(src)
        if not width or height / width < MIN_PORTRAIT_RATIO:
            problems.append(f"{src.name}: khổ {width}x{height} không phải dọc 9:16 — tạo lại trong Muse ở 9:16")
            continue
        p.clip_path(sid).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, p.clip_path(sid))
        p.upscaled_path(sid).unlink(missing_ok=True)  # a new take must be upscaled again
        wav = p.voice_dir / f"shot_{int(sid[2:]):02d}.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        audio_in = ["-i", str(src)] if has_audio else ["-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=stereo"]
        subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *audio_in, "-vn", "-ac", "2", "-ar", "48000",
                        str(wav)], check=True)
        state[sid] = {"source": stamp, "seconds": round(seconds, 2), "size": f"{width}x{height}", "audio": has_audio}
        done.append(sid)
    tmp = p.build / "muse-clips.json.tmp"  # write-then-rename: a killed watcher must not leave a truncated file
    write_json(tmp, state)
    tmp.replace(p.build / "muse-clips.json")
    missing = [s["id"] for s in p.shots if s["id"] not in state]
    return done, missing, problems


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--watch", action="store_true", help="poll the inbox until complete, then run make_video")
    args = ap.parse_args()
    p = VideoProject(args.project)
    while True:
        done, missing, problems = ingest(p)
        for d in done:
            print(f"  nhận {d}: {read_json(p.build / 'muse-clips.json')[d]}")
        for problem in problems:
            print(f"  LỖI: {problem}")
            notify(f"{p.id}: clip Muse sai khổ", problem[:200])
        if not missing or not args.watch:
            break
        time.sleep(15)
    if missing:
        print(f"  còn thiếu: {missing} (bỏ SCnn.mp4 vào {p.rel(p.dir / 'muse-inbox')})")
        sys.exit(1)
    print("  đủ clip.")
    if not args.watch:
        return
    if any(isinstance(d, dict) for s in p.shots for d in s.get("dialogue", [])):
        # dubbed episode: dub timing/trims depend on what Muse actually drew -> stop for review instead of building
        subprocess.run([str(ASR_PY), "-u", str(ROOT / "scripts" / "muse_clip_review_sheet_and_speech_check.py"), p.id,
                        "--apply"], cwd=ROOT)
        print(f"  CHỜ SOÁT: xem {p.rel(p.build / 'review')}, chỉnh at/trim trong shots.json, rồi chạy make_video {p.id}")
        notify(f"{p.id}: đã nhận đủ clip Muse — chờ soát", "Tờ soát + kiểm tra tiếng clip đã xong; chưa dựng video")
        return
    notify(f"{p.id}: đã nhận đủ clip Muse", "Đang upscale + ghép video…")
    subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / "make_video.py"), p.id], cwd=ROOT)


if __name__ == "__main__":
    main()
