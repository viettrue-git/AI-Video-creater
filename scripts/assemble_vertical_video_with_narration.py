"""Assemble shot clips + per-shot narration into one 9:16 MP4 with FFmpeg.

Each shot: video trimmed to its duration, center-cropped to 1080x1920 @ 24 fps; narration placed at the
shot start and padded with silence to the same duration. Optional music bed is ducked under the voice.
Final audio is loudness-normalized (-14 LUFS, Shorts/TikTok) -> H.264 yuv420p + AAC 48 kHz stereo.

Manifest JSON (paths relative to repo root):
  {"output": "projects/P001_rung_co/final/vs.mp4", "music": null, "music_start": 0, "music_volume": 0.25,
   "fade_out": 1.5, "ambience": [{"file": "...mp3", "start": 0, "end": 19.4, "volume": 0.3, "fade": 1.5}],
   "shots": [{"id": "SH01", "clip": "...mp4", "narration": "...wav", "duration": 3.16}, ...]}
Usage: python scripts/assemble_vertical_video_with_narration.py projects/P001_rung_co/vertical-slice-manifest.json
"""
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT, FPS = 1080, 1920, 24


def find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    # winget installs here; the PATH update only reaches newly started shells
    pattern = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
    matches = sorted(glob.glob(pattern))
    if not matches:
        sys.exit("ffmpeg not found (winget install Gyan.FFmpeg)")
    return matches[-1]


def build_command(ffmpeg, manifest):
    shots = manifest["shots"]
    cmd, filters, concat_inputs = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"], [], ""
    for shot in shots:
        cmd += ["-i", str(ROOT / shot["clip"]), "-i", str(ROOT / shot["narration"])]
    music = manifest.get("music")
    if music:
        # music_start: skip into the track so its build-up lands on the story's turning point
        cmd += ["-ss", str(manifest.get("music_start", 0)), "-stream_loop", "-1", "-i", str(ROOT / music)]
    for i, shot in enumerate(shots):
        d = shot["duration"]
        v, a = 2 * i, 2 * i + 1
        grade = f"eq={shot['eq']}," if shot.get("eq") else ""  # per-shot color fix, e.g. "gamma=1.2"
        # scale to cover 1080x1920 then center-crop (never stretch); hold last frame if clip is short
        filters.append(f"[{v}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
                       # deflicker: safety net vs brightness pulses (VAE temporal-tile seams, 2026-10-05)
                       f"crop={WIDTH}:{HEIGHT},fps={FPS},deflicker=mode=pm:size=9,{grade}"
                       f"tpad=stop_mode=clone:stop_duration={d},"
                       f"trim=duration={d},setpts=PTS-STARTPTS,setsar=1[v{i}]")
        filters.append(f"[{a}:a]aresample=48000,aformat=channel_layouts=stereo,apad,"
                       f"atrim=duration={d},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs += f"[v{i}][a{i}]"
    total = sum(s["duration"] for s in shots)
    fade = float(manifest.get("fade_out", 0))
    video_fade = f",fade=t=out:st={total - fade:.3f}:d={fade}" if fade else ""
    filters.append(f"{concat_inputs}concat=n={len(shots)}:v=1:a=1[vcat][voice]")
    filters.append(f"[vcat]null{video_fade}[vout]")
    # background bed = music + ambience layers; the whole bed is ducked under the narrator
    bed_layers, next_input = [], 2 * len(shots)
    if music:
        filters.append(f"[{next_input}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={total},"
                       f"volume={manifest.get('music_volume', 0.25)}[music]")
        bed_layers.append("[music]")
        next_input += 1
    for k, amb in enumerate(manifest.get("ambience", [])):
        start, end = float(amb.get("start", 0)), float(amb.get("end", total))
        dur, fd = end - start, float(amb.get("fade", 1.0))
        cmd += ["-stream_loop", "-1", "-i", str(ROOT / amb["file"])]  # loop if the sound is shorter
        delay = int(start * 1000)
        filters.append(f"[{next_input}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={dur},"
                       f"afade=t=in:d={fd},afade=t=out:st={dur - fd:.3f}:d={fd},volume={amb.get('volume', 0.3)},"
                       f"adelay={delay}|{delay},apad,atrim=duration={total}[amb{k}]")
        bed_layers.append(f"[amb{k}]")
        next_input += 1
    if bed_layers:
        if len(bed_layers) > 1:
            filters.append(f"{''.join(bed_layers)}amix=inputs={len(bed_layers)}:normalize=0[bed]")
        else:
            filters.append(f"{bed_layers[0]}anull[bed]")
        filters.append("[voice]asplit=2[vo1][vo2]")
        filters.append("[bed][vo2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]")
        filters.append("[vo1][ducked]amix=inputs=2:normalize=0[mix]")
        last = "mix"
    else:
        last = "voice"
    audio_fade = f",afade=t=out:st={total - fade:.3f}:d={fade}" if fade else ""
    filters.append(f"[{last}]loudnorm=I=-14:TP=-1.5:LRA=11{audio_fade}[aout]")
    out = ROOT / manifest["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(out)]
    return cmd, out, total


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    manifest = json.loads((ROOT / sys.argv[1]).read_text(encoding="utf-8-sig"))
    missing = [p for s in manifest["shots"] for p in (s["clip"], s["narration"]) if not (ROOT / p).exists()]
    if missing:
        sys.exit("Missing inputs:\n  " + "\n  ".join(missing))
    cmd, out, total = build_command(find_ffmpeg(), manifest)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{result.stderr[-2000:]}")
    print(f"OK {out} ({total:.2f}s, {len(manifest['shots'])} shots)")


if __name__ == "__main__":
    main()
