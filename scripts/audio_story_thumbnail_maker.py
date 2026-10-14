"""YouTube thumbnail (1280x720 JPG) for an audio-story episode: Muse THUMB image + darkened left side + title text.

  python scripts/audio_story_thumbnail_maker.py P006 "CỬU VĨ HỒ" "Từ điềm lành thành yêu nữ"
Reads illustration-inbox/THUMB.*; writes final/thumbnail.jpg.
"""
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from video_project_config import VideoProject

W, H = 1280, 720
GOLD, WHITE = (232, 200, 135), (245, 245, 245)


def font(name, size):
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def fit(draw, text, name, size, max_width):
    """Largest font size (down from `size`) whose rendered text fits max_width."""
    while size > 20 and draw.textlength(text, font=font(name, size)) > max_width:
        size -= 4
    return font(name, size)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p, title, subtitle = VideoProject(sys.argv[1]), sys.argv[2], sys.argv[3]
    src = next((p.dir / "illustration-inbox").glob("THUMB.*"))
    img = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
    shade = Image.new("L", (W, H), 0)  # dark gradient on the left 55% so the title reads on any image
    ImageDraw.Draw(shade).rectangle((0, 0, int(W * 0.55), H), fill=190)
    shade = shade.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGB", (W, H), (5, 8, 16)), img, shade)
    draw = ImageDraw.Draw(img)
    big = fit(draw, title, "seguibl.ttf", 150, W * 0.50)
    small = fit(draw, subtitle, "segoeuib.ttf", 54, W * 0.50)
    y = H * 0.30
    draw.text((60, y), title, font=big, fill=GOLD, stroke_width=4, stroke_fill=(0, 0, 0))
    draw.text((64, y + big.size * 1.15), subtitle, font=small, fill=WHITE, stroke_width=3, stroke_fill=(0, 0, 0))
    out = p.dir / "final" / "thumbnail.jpg"
    out.parent.mkdir(exist_ok=True)
    img.save(out, quality=92)
    print(f"OK {p.rel(out)}")


if __name__ == "__main__":
    main()
