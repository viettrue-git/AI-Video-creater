"""Build a labeled contact-sheet grid from test images, for side-by-side scoring."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THUMB_WIDTH = 256
LABEL_HEIGHT = 22


def _load_font():
    try:
        return ImageFont.truetype("arial.ttf", 15)
    except OSError:
        return ImageFont.load_default()


def build_contact_sheet(rows, out_path, thumb_width=THUMB_WIDTH):
    """rows: list of rows, each a list of (label, image_path or None). Missing images stay blank."""
    cells = [cell for row in rows for cell in row if cell[1] and Path(cell[1]).exists()]
    if not cells:
        return None
    # size thumbnails from a rendered image (last cell), not the REF in column 0
    with Image.open(cells[-1][1]) as sample:
        thumb_height = round(thumb_width * sample.height / sample.width)
    cols = max(len(row) for row in rows)
    cell_h = thumb_height + LABEL_HEIGHT
    sheet = Image.new("RGB", (cols * thumb_width, len(rows) * cell_h), (30, 30, 30))
    draw, font = ImageDraw.Draw(sheet), _load_font()
    for r, row in enumerate(rows):
        for c, (label, path) in enumerate(row):
            x, y = c * thumb_width, r * cell_h
            if path and Path(path).exists():
                with Image.open(path) as im:
                    im = im.convert("RGB")
                    im.thumbnail((thumb_width, thumb_height), Image.LANCZOS)
                    sheet.paste(im, (x + (thumb_width - im.width) // 2, y + LABEL_HEIGHT))
            draw.text((x + 4, y + 3), label, fill=(240, 240, 240), font=font)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=90)
    return Path(out_path)
