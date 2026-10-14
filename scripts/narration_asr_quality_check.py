"""Listen back to every TTS paragraph with Whisper and flag the ones that do not match the script.

  tools/asr-venv/Scripts/python.exe scripts/narration_asr_quality_check.py P006 [--threshold 0.85]
Catches misreads, skipped words and stray babble that the silence-based check misses. Similarity = difflib ratio of
the normalized script text vs. the recognized text (lowercase, no punctuation). Report: build/audio/asr-check.json.
"""
import argparse
import difflib
import re
import sys
import unicodedata

from muse_dialogue_subtitles import MODEL, MODEL_DIR, load_16k_mono
from video_project_config import VideoProject, parse_shots, write_json


NUMBER_WORDS = {"không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười", "mươi", "mốt", "tư",
                "lăm", "trăm", "nghìn", "ngàn", "lẻ", "linh", "triệu"}


def normalize(text):
    """Lowercase words without numbers: Whisper writes years as digits ("1258") while scripts spell them out
    ("một nghìn hai trăm năm mươi tám") — comparing both forms flagged nearly every history paragraph (P008)."""
    text = unicodedata.normalize("NFC", text.lower())
    return " ".join(w for w in re.findall(r"\w+", text) if not w.isdigit() and w not in NUMBER_WORDS)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--threshold", type=float, default=0.6)  # word-level, numbers ignored; accents (Nam Bộ) lower ASR accuracy
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    p = VideoProject(args.project)
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=str(MODEL_DIR))
    report, flagged = [], []
    for no, desc, text in parse_shots(p.dir / "script.txt"):
        # no initial_prompt / VAD: with them Whisper skipped whole sentences of complete paragraphs (P006: 3 false alarms)
        segments, _ = model.transcribe(load_16k_mono(p.voice_dir / f"shot_{no:02d}.wav"), language="vi",
                                       vad_filter=False, condition_on_previous_text=False)
        heard = " ".join(s.text for s in segments)
        # word-level, autojunk off: on long strings difflib's autojunk skipped common characters → 0.04 scores (P008)
        score = difflib.SequenceMatcher(None, normalize(text).split(), normalize(heard).split(), autojunk=False).ratio()
        report.append({"shot": no, "score": round(score, 3), "script": text, "heard": heard.strip()})
        if score < args.threshold and len(normalize(text).split()) >= 8:  # very short titles: too few words to judge
            flagged.append(no)
            print(f"  ! đoạn {no} ({score:.2f}): nghe được «{heard.strip()[:120]}»")
    write_json(p.voice_dir.parent / "asr-check.json", report)
    scores = [r["score"] for r in report]
    print(f"  {len(report)} đoạn, trung bình {sum(scores) / len(scores):.2f}, cần nghe lại: {flagged or 'không'}")


if __name__ == "__main__":
    main()
