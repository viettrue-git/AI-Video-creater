"""Turn still images into one vertical clip with slow Ken Burns zooms + crossfades (scenes Muse refuses to animate).

  python scripts/muse_still_images_to_ken_burns_clip.py out.mp4 img1.png img2.png [--seconds 10]
Used by muse_clip_ingest: SC03-1.png, SC03-2.png in muse-inbox/ (and no SC03*.mp4) -> SC03-ken-burns.mp4.
Images share the clip evenly, in name order (image 1 = 0–5 s, image 2 = 5–10 s for two images), so the dub timeline
of a 2-speaker scene still lines up. Output: 720x1280, 30 fps, silent.
"""
import argparse
import subprocess

from assemble_vertical_video_with_narration import find_ffmpeg

FPS, FADE, ZOOM = 30, 0.6, 0.10  # crossfade seconds; zoom range per image (1.0 -> 1.10)
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def build_ken_burns_clip(images, out, seconds=10.0):
    n = len(images)
    each = (seconds + FADE * (n - 1)) / n  # crossfades overlap, so each image runs a bit longer than seconds/n
    frames = int(round(each * FPS))
    chains, inputs = [], []
    for i, image in enumerate(images):
        inputs += ["-i", str(image)]
        # alternate zoom in / zoom out; 2x canvas first so zoompan's integer crop does not jitter
        zoom = f"1+{ZOOM}*on/{frames}" if i % 2 == 0 else f"{1 + ZOOM}-{ZOOM}*on/{frames}"
        chains.append(f"[{i}:v]scale=1440:2560:force_original_aspect_ratio=increase,crop=1440:2560,"
                      f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps={FPS},"
                      f"setsar=1,format=yuv420p[v{i}]")
    last = "v0"
    for i in range(1, n):
        chains.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={i * (each - FADE):.3f}[x{i}]")
        last = f"x{i}"
    subprocess.run([find_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(chains), "-map", f"[{last}]", "-t", str(seconds),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--seconds", type=float, default=10.0)
    args = ap.parse_args()
    build_ken_burns_clip(args.images, args.out, args.seconds)


if __name__ == "__main__":
    main()
