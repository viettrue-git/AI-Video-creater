"""Text layers of a long-form audio-story video: chapter titles, name cards (FFmpeg drawtext) and an .srt for YouTube.

Used by audio_story_video_assembler.py. Text goes through drawtext textfile= (written to build/story-text/) so
Vietnamese text, colons and quotes need no escaping.
"""
import re

FONT_TITLE = "C\\:/Windows/Fonts/seguibl.ttf"   # Segoe UI Black (Vietnamese glyphs); colon escaped for drawtext
FONT_TEXT = "C\\:/Windows/Fonts/segoeuib.ttf"   # Segoe UI Bold
CARD_SECONDS = 6.0


def _textfile(p, name, text):
    folder = p.build / "story-text"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return p.rel(path)


def _fade(start, end, fade=0.6):
    """drawtext alpha expression: fade in at start, out before end."""
    return f"if(lt(t,{start + fade:.2f}),(t-{start:.2f})/{fade},if(gt(t,{end - fade:.2f}),({end:.2f}-t)/{fade},1))"


def chapter_title_filters(p, timing):
    """Big centered title while a chapter-title paragraph is read: 'CHƯƠNG MỘT' + subtitle line."""
    out = []
    for t in (x for x in timing if x["chapter_title"]):
        head, _, rest = t["text"].partition(".")
        start, end = t["start"] - 0.4, t["end"] + 2.2
        on = f"enable='between(t,{start:.2f},{end:.2f})':alpha='{_fade(start, end)}'"
        f1 = _textfile(p, f"chapter{t['shot']:02d}-a", head.strip().upper())
        f2 = _textfile(p, f"chapter{t['shot']:02d}-b", rest.strip().rstrip("."))
        out.append(f"drawtext=fontfile='{FONT_TEXT}':textfile='{f1}':fontsize=44:fontcolor=0xE8C887:"
                   f"x=(w-text_w)/2:y=h*0.40:borderw=3:bordercolor=black@0.7:{on}")
        out.append(f"drawtext=fontfile='{FONT_TITLE}':textfile='{f2}':fontsize=78:fontcolor=white:"
                   f"x=(w-text_w)/2:y=h*0.48:borderw=4:bordercolor=black@0.7:{on}")
    return out


def name_card_filters(p, timing, cards):
    """Left card above the burned subtitles (dark box + gold title + white subtitle) when a person/book/place is first mentioned.
    Careful: in drawbox "h" is the BOX height (frame height = "ih"); in drawtext "h" is the frame height."""
    by_no, out = {t["shot"]: t for t in timing}, []
    for i, card in enumerate(cards):
        start = by_no[card["shot"]]["start"] + 0.5
        end = start + CARD_SECONDS
        between = f"between(t,{start:.2f},{end:.2f})"
        alpha = _fade(start, end, 0.4)
        f1, f2 = _textfile(p, f"card{i:02d}-a", card["title"]), _textfile(p, f"card{i:02d}-b", card["sub"])
        out.append(f"drawbox=x=70:y=ih-420:w=900:h=150:color=black@0.55:t=fill:enable='{between}'")
        out.append(f"drawbox=x=70:y=ih-420:w=8:h=150:color=0xE8C887@0.95:t=fill:enable='{between}'")
        out.append(f"drawtext=fontfile='{FONT_TITLE}':textfile='{f1}':fontsize=48:fontcolor=0xE8C887:"
                   f"x=105:y=h-402:enable='{between}':alpha='{alpha}'")
        out.append(f"drawtext=fontfile='{FONT_TEXT}':textfile='{f2}':fontsize=34:fontcolor=white:"
                   f"x=105:y=h-335:enable='{between}':alpha='{alpha}'")
    return out


def _words(text):
    return len(re.findall(r"\w+", text))


def _chunks(sentence, max_words):
    """Split a long sentence at commas (then evenly by words) so one caption fits ~2 short lines on screen."""
    if _words(sentence) <= max_words:
        return [sentence]
    out, cur = [], ""
    for clause in re.split(r"(?<=[,;:])\s+", sentence):
        if cur and _words(cur) + _words(clause) > max_words:
            out.append(cur)
            cur = clause
        else:
            cur = f"{cur} {clause}".strip()
    out.append(cur)
    final = []
    for piece in out:  # a single clause still too long → even word split
        words = piece.split()
        n = -(-len(words) // max_words)
        size = -(-len(words) // n)
        final += [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
    return final


def caption_cues(timing, max_words=14):
    """[(start, end, text)] following the narration: each paragraph split into short pieces, timed in proportion to
    their syllables (+1 per piece for the pause at its punctuation). Chapter-title paragraphs are skipped: the big
    on-screen title already shows them."""
    cues = []
    for t in (x for x in timing if not x.get("chapter_title")):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", t["text"]) if s.strip()]
        pieces = [c for s in sentences for c in _chunks(s, max_words)]
        sizes = [max(_words(c), 1) + 1 for c in pieces]
        start, span = t["start"], t["end"] - t["start"]
        for piece, size in zip(pieces, sizes):
            length = span * size / sum(sizes)
            cues.append((start, start + length, piece))
            start += length
    return cues


def write_srt(timing, path):
    """Captions (.srt) for YouTube upload and for burning into the video."""
    def stamp(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    cues = caption_cues(timing)
    path.write_text("".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{s}\n\n" for i, (a, b, s) in enumerate(cues, 1)),
                    encoding="utf-8")
    return len(cues)


def burned_subtitle_filter(srt_rel):
    """libass filter drawing the .srt at the bottom center (path relative to the repo root: no drive colon to escape).
    Srt sizes are in a 288-px-high script space: FontSize 15 ≈ 56 px on 1080p, MarginV 22 ≈ 82 px from the bottom."""
    style = ("FontName=Segoe UI,Bold=1,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=1.6,Shadow=0.8,MarginV=22,MarginL=60,MarginR=60,Alignment=2")
    return f"subtitles=filename='{srt_rel.replace(chr(92), '/')}':charenc=UTF-8:force_style='{style}'"
