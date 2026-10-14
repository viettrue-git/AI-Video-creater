"""Build the 16:9 long-form video of an audio story: illustrations (slow Ken Burns + crossfades), chapter titles,
name cards, narration + music bed (ducked) + ambience + chapter stings, loudness-normalized.

  python scripts/audio_story_video_assembler.py P006 [--placeholders]
Inputs: build/audio/story-narration.wav + story-timing.json (narration joiner), build/audio/story-layers.json
(sound layers), illustrations.json + illustration-inbox/IMGnn.(png|jpg|webp) or a zip from Muse.
--placeholders renders missing illustrations as labeled dark frames (to test timing before the art arrives).
Outputs final/<id>-vN.mp4 (captions burned in unless project.json "burn_subtitles": false) and final/<id>-vN.srt.
"""
import argparse
import re
import subprocess
import sys

from assemble_vertical_video_with_narration import find_ffmpeg
from audio_library import measure
from audio_story_overlays import burned_subtitle_filter, chapter_title_filters, name_card_filters, write_srt
from muse_clip_ingest import unzip_inbox
from video_project_config import ROOT, VideoProject, read_json

W, H, FPS, XFADE = 1920, 1080, 24, 1.2
TARGET = {"music": -27.0, "ambience": -33.0, "sting": -24.0, "sfx": -21.0}  # pre-mix loudness of each layer (LUFS)
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


def find_image(inbox, image_id):
    return next((f for f in sorted(inbox.iterdir()) if f.stem.upper().startswith(image_id) and
                 f.suffix.lower() in IMAGE_EXT), None)


def placeholder(p, image_id):
    from PIL import Image, ImageDraw
    path = p.build / "placeholders" / f"{image_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), (18, 22, 34))
    ImageDraw.Draw(img).text((60, 60), f"{image_id} (chờ ảnh Muse)", fill=(200, 190, 150))
    img.save(path)
    return path


def gain(path, kind):
    return round(10 ** ((TARGET[kind] - measure(ROOT / path)[1]) / 20), 3)


def silence_filter(silences, ramp=0.8):
    """Music/ambience bed fades to silence inside each window (start, end) so a key line stands alone.
    Per window: max(min(1,(a-t)/ramp), min(1,(t-b)/ramp), 0) = 1 outside, linear ramps, 0 inside; windows multiply."""
    if not silences:
        return "anull"
    # FFmpeg expression max()/min() take exactly two arguments → nest them
    terms = [f"max(max(min(1,({s['start']:.2f}-t)/{ramp}),min(1,(t-{s['end']:.2f})/{ramp})),0)" for s in silences]
    return f"volume='{'*'.join(terms)}':eval=frame"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--placeholders", action="store_true")
    ap.add_argument("--preview", type=float, default=0, help="only render the first N seconds (quick check)")
    args = ap.parse_args()
    p = VideoProject(args.project)
    audio_dir = p.voice_dir.parent
    timing, layers = read_json(audio_dir / "story-timing.json"), read_json(audio_dir / "story-layers.json")
    mix_cfg = p.config.get("story_audio", {})  # per-project mix: music loudness + how hard music ducks under the voice
    TARGET["music"] = float(mix_cfg.get("music_lufs", TARGET["music"]))
    duck_ratio = float(mix_cfg.get("duck_ratio", 6))
    plan = read_json(p.dir / "illustrations.json")
    inbox = p.dir / "illustration-inbox"
    unzip_inbox(inbox, IMAGE_EXT)
    total = round(timing[-1]["end"] + 3.0, 2)
    by_no = {t["shot"]: t for t in timing}
    starts = [0.0] + [by_no[img["shots"][0]]["start"] - 0.6 for img in plan["images"][1:]]

    cmd, filters, labels = [find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"], [], []
    for i, img in enumerate(plan["images"]):
        src = find_image(inbox, img["id"])
        if not src:
            if not args.placeholders:
                sys.exit(f"Thiếu ảnh {img['id']} trong {p.rel(inbox)} (hoặc chạy với --placeholders để thử)")
            src = placeholder(p, img["id"])
        end = starts[i + 1] if i + 1 < len(starts) else total
        length = round(end - starts[i] + (XFADE if i + 1 < len(starts) else 0), 2)
        frames = int(length * FPS)
        zoom_in = i % 2 == 0  # alternate slow push-in / pull-out so consecutive images do not feel repetitive
        z = f"1+0.10*on/{frames}" if zoom_in else f"1.10-0.10*on/{frames}"
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(length), "-i", str(src)]
        filters.append(f"[{i}:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                       f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
                       f"setsar=1,format=yuv420p[img{i}]")
        labels.append(f"[img{i}]")
    last = labels[0]
    for i in range(1, len(labels)):
        filters.append(f"{last}{labels[i]}xfade=transition=fade:duration={XFADE}:offset={starts[i]:.2f}[x{i}]")
        last = f"[x{i}]"
    versions = [int(m.group(1)) for f in (p.dir / "final").glob("*.mp4") if (m := re.search(r"-v(\d+)\.mp4$", f.name))]
    out = p.dir / "final" / f"{p.id}-v{max(versions, default=0) + 1}.mp4"
    out.parent.mkdir(exist_ok=True)
    srt = out.with_suffix(".srt")
    cue_count = write_srt(timing, srt)
    text = chapter_title_filters(p, timing) + name_card_filters(p, timing, plan.get("cards", []))
    if p.config.get("burn_subtitles", True):  # on-screen captions following the narration (opt out per project)
        text.append(burned_subtitle_filter(p.rel(srt)))
    fades = ["fade=t=in:d=1.5", f"fade=t=out:st={total - 2.5:.2f}:d=2.5"]
    filters.append(f"{last}{','.join(text + fades)}[vout]")

    n = len(labels)
    cmd += ["-i", str(audio_dir / "story-narration.wav")]
    filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={total},"
                   f"asplit=2[voice][key]")
    bed, k = [], n + 1
    for kind, items in (("music", layers["music"]), ("ambience", layers["ambience"])):
        for item in items:
            dur, delay, fd = item["end"] - item["start"], int(item["start"] * 1000), 3.0 if kind == "music" else 2.0
            cmd += (["-stream_loop", "-1"] if kind == "ambience" else []) + ["-i", str(ROOT / item["file"])]
            filters.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={dur:.2f},"
                           f"afade=t=in:d={fd},afade=t=out:st={max(dur - fd, 0):.2f}:d={fd},"
                           f"volume={gain(item['file'], kind)},adelay={delay}|{delay},apad,atrim=duration={total}[b{k}]")
            bed.append(f"[b{k}]")
            k += 1
    filters.append(f"{''.join(bed)}amix=inputs={len(bed)}:normalize=0[bedmix]")
    filters.append(f"[bedmix]{silence_filter(layers.get('silences', []))}[bedq]")
    filters.append(f"[bedq][key]sidechaincompress=threshold=0.03:ratio={duck_ratio}:attack=30:release=600[ducked]")
    mix = ["[voice]", "[ducked]"]
    if layers.get("stings"):
        cmd += ["-i", str(ROOT / layers["stings"][0]["file"])]
        g = gain(layers["stings"][0]["file"], "sting")
        filters.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={g},"
                       f"asplit={len(layers['stings'])}" + "".join(f"[s{j}]" for j in range(len(layers["stings"]))))
        for j, s in enumerate(layers["stings"]):
            d = int(s["start"] * 1000)
            filters.append(f"[s{j}]adelay={d}|{d},apad,atrim=duration={total}[st{j}]")
            mix.append(f"[st{j}]")
    for j, fx in enumerate(layers.get("sfx", [])):  # accent effects at a paragraph, on top (never ducked)
        cmd += ["-i", str(ROOT / fx["file"])]
        d, dur = int(fx["start"] * 1000), float(fx["duration"])
        filters.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={dur},"
                       f"afade=t=out:st={max(dur - 0.4, 0):.2f}:d=0.4,volume={gain(fx['file'], 'sfx')},"
                       f"adelay={d}|{d},apad,atrim=duration={total}[fx{j}]")
        mix.append(f"[fx{j}]")
        k += 1
    filters.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0,"
                   f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={total - 2.5:.2f}:d=2.5[aout]")

    script = p.build / "story-filter.txt"  # long graph: a file avoids the Windows command-line length limit
    script.write_text(";\n".join(filters), encoding="utf-8")
    cmd += ["-/filter_complex", p.rel(script),  # FFmpeg 7+: "-/opt file" reads the value from a file
            "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264",
            "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-t", str(args.preview or total), str(out)]
    print(f"  dựng {len(labels)} tranh, {total / 60:.1f} phút -> {p.rel(out)} (có thể mất 15–30 phút)")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        sys.exit(f"FFmpeg lỗi:\n{result.stderr[-3000:]}")
    print(f"  phụ đề: {cue_count} câu -> {p.rel(srt)}")
    print(f"OK {p.rel(out)}")


if __name__ == "__main__":
    main()
