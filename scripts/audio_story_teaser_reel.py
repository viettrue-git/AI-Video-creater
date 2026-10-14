"""Vertical 9:16 teaser reel (Facebook Reels / Shorts) cut from a finished long-form audio story.

  python scripts/audio_story_teaser_reel.py P006
project.json "teaser": {"hook_text", "segments": [{"shot", "image", "focus"}], "end_card": {...}, "music_index"}.
Each segment = one narrated paragraph (build/audio/<voice>/shot_NN.wav) over a 16:9 illustration cropped to 9:16
with a slow pan around "focus" (0 = left edge, 1 = right edge). Burned-in captions (reels autoplay muted), a hook
line on top for the first seconds, an end card with the call to action. Output: final/<id>-teaser-reel-vN.mp4.
"""
import re
import subprocess
import sys
import wave

from assemble_vertical_video_with_narration import find_ffmpeg
from audio_library import measure
from audio_story_overlays import FONT_TEXT, FONT_TITLE, write_srt
from audio_story_video_assembler import IMAGE_EXT
from video_project_config import ROOT, VideoProject, parse_shots, read_json

W, H, FPS, GAP, PAN = 1080, 1920, 24, 0.35, 320


def seconds_of(wav):
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def image_path(p, image_id):
    return next(f for f in sorted((p.dir / "illustration-inbox").iterdir())
                if f.stem.upper() == image_id and f.suffix.lower() in IMAGE_EXT)


def textfile(p, name, text):
    path = p.build / "story-text" / f"teaser-{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return p.rel(path)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = VideoProject(sys.argv[1])
    cfg, texts = p.config["teaser"], {n: t for n, _, t in parse_shots(p.dir / "script.txt")}
    layers = read_json(p.voice_dir.parent / "story-layers.json")
    cmd, filters, vlabels, alabels, timing, t = [find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"], [], [], [], [], 0.0
    for i, seg in enumerate(cfg["segments"]):
        wav = p.voice_dir / f"shot_{seg['shot']:02d}.wav"
        dur = round(seconds_of(wav) + GAP, 2)
        timing.append({"start": t, "end": t + dur - GAP, "text": texts[seg["shot"]]})
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", str(image_path(p, seg["image"])), "-i", str(wav)]
        v, a = 2 * i, 2 * i + 1
        # scale the 16:9 art to reel height, then pan a 1080-wide window across the focus point
        x0 = f"max(0,min(iw-{W},iw*{seg.get('focus', 0.5)}-{W / 2}-{PAN / 2}))"
        filters.append(f"[{v}:v]scale=-2:{H},crop={W}:{H}:x='{x0}+{PAN}*t/{dur}':y=0,setsar=1,fps={FPS},"
                       f"format=yuv420p[v{i}]")
        filters.append(f"[{a}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={dur}[a{i}]")
        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")
        t += dur
    card = cfg["end_card"]
    n = len(cfg["segments"])
    cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(card["seconds"]), "-i", str(image_path(p, card["image"]))]
    on = "enable='gte(t,0.2)'"
    lines = [("title", card["title"], FONT_TITLE, 130, "0xE8C887", 0.30), ("sub", card["sub"], FONT_TEXT, 58, "white", 0.39),
             ("cta", card["cta"], FONT_TEXT, 50, "white", 0.70)]
    draws = ",".join(f"drawtext=fontfile='{font}':textfile='{textfile(p, key, text)}':fontsize={size}:fontcolor={color}:"
                     f"x=(w-text_w)/2:y=h*{y}:line_spacing=14:borderw=4:bordercolor=black@0.8:{on}"
                     for key, text, font, size, color, y in lines)
    filters.append(f"[{2 * n}:v]scale=-2:{H},crop={W}:{H}:x='iw*{card.get('focus', 0.6)}-{W / 2}':y=0,setsar=1,fps={FPS},"
                   f"eq=brightness=-0.18,{draws},format=yuv420p[vcard]")
    total = round(t + card["seconds"], 2)
    srt = p.build / "teaser.srt"
    write_srt(timing, srt)
    style = ("FontName=Segoe UI Black,FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,"
             "Outline=1.8,Shadow=0,Alignment=2,MarginV=78,MarginL=18,MarginR=18")
    hook = f"drawtext=fontfile='{FONT_TITLE}':textfile='{textfile(p, 'hook', cfg['hook_text'])}':fontsize=70:" \
           f"fontcolor=0xE8C887:x=(w-text_w)/2:y=h*0.10:line_spacing=16:borderw=5:bordercolor=black@0.8:" \
           f"enable='lt(t,{cfg.get('hook_seconds', 5)})'"
    filters.append(f"{''.join(vlabels)}[vcard]concat=n={n + 1}:v=1:a=0,subtitles='{p.rel(srt)}':force_style='{style}',"
                   f"{hook},fade=t=in:d=0.4[vout]")
    k = 2 * n + 1
    music, sting = layers["music"][cfg.get("music_index", 0)]["file"], layers["stings"][0]["file"]
    cmd += ["-i", str(ROOT / music), "-i", str(ROOT / sting)]
    vol = lambda f, target: round(10 ** ((target - measure(ROOT / f)[1]) / 20), 3)  # noqa: E731
    filters.append(f"{''.join(alabels)}concat=n={n}:v=0:a=1,apad,atrim=duration={total},asplit=2[voice][key]")
    filters.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={total},"
                   f"volume={vol(music, -24)},afade=t=out:st={total - 2:.2f}:d=2[mus]")
    filters.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=500[duck]")
    d = int(t * 1000)
    filters.append(f"[{k + 1}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol(sting, -20)},"
                   f"adelay={d}|{d},apad,atrim=duration={total}[sting]")
    filters.append("[voice][duck][sting]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    versions = [int(m.group(1)) for f in (p.dir / "final").glob("*teaser-reel-v*.mp4") if (m := re.search(r"-v(\d+)\.mp4$", f.name))]
    out = p.dir / "final" / f"{p.id}-teaser-reel-v{max(versions, default=0) + 1}.mp4"
    graph = p.build / "teaser-filter.txt"
    graph.write_text(";\n".join(filters), encoding="utf-8")
    cmd += ["-/filter_complex", p.rel(graph), "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            "-t", str(total), str(out)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.exit(f"FFmpeg lỗi:\n{result.stderr[-3000:]}")
    print(f"OK {p.rel(out)} ({total:.1f}s)")


if __name__ == "__main__":
    main()
