"""Make new narrator voices by blending VieNeu Turbo preset speaker embeddings, and render a demo for each.

  tools/vieneu-tts-venv/Scripts/python.exe scripts/vieneu_blended_voice_demo.py --out experiments/voice-blend-tests
A V3 Turbo voice = 192-d speaker embedding (timbre) + reference codes (prosody prompt). A weighted mix of two
presets' embeddings gives a new timbre; the codes of a third preset set the speaking style; a higher sampling
temperature (default 0.8) gives livelier prosody. Each voice is saved as <out>/voices/<name>.npz for reuse.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

TEXT = ("Năm một nghìn hai trăm tám mươi lăm. Năm mươi vạn quân Nguyên Mông tràn qua biên giới. "
        "Giữa lúc ấy, tại điện Diên Hồng, nhà vua hỏi các bô lão khắp nơi: nên hòa, hay nên đánh? "
        "Muôn người như một, cùng đồng thanh hô vang: Đánh! "
        "Tiếng hô ấy vang dội khắp non sông, trở thành lời thề của cả một dân tộc. "
        "Và người đứng mũi chịu sào, dẫn dắt muôn quân đi vào cuộc chiến sinh tử ấy, "
        "chính là Hưng Đạo Đại Vương Trần Quốc Tuấn.")

# (file name, timbre mix [(preset, weight)], prosody preset (its reference codes), temperature)
BLENDS = [
    ("1-minhduc-quoctuan", [("Minh Đức", 0.5), ("Quốc Tuấn", 0.5)], "Thanh Bình", 0.9),
    ("2-minhduc-haidang", [("Minh Đức", 0.5), ("Hải Đăng", 0.5)], "Thanh Bình", 0.9),
    ("3-thanhbinh-minhduc", [("Thanh Bình", 0.5), ("Minh Đức", 0.5)], "Minh Đức", 0.9),
    ("4-quoctuan-xuanvinh", [("Quốc Tuấn", 0.5), ("Xuân Vĩnh", 0.5)], "Thiện Minh", 0.9),
    ("5-minhduc-phamtuyen", [("Minh Đức", 0.6), ("Phạm Tuyên", 0.4)], "Thanh Bình", 0.9),
    ("6-minhduc-bieucam", [("Minh Đức", 1.0)], "Minh Đức", 1.0),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from vieneu import Vieneu
    out = Path(args.out)
    (out / "voices").mkdir(parents=True, exist_ok=True)
    tts = Vieneu()
    for name, mix, prosody, temperature in BLENDS:
        emb = sum(w * np.asarray(tts.get_preset_voice(p)["speaker_emb"], dtype=np.float32) for p, w in mix)
        codes = np.asarray(tts.get_preset_voice(prosody)["codes"])
        np.savez(out / "voices" / f"{name}.npz", speaker_emb=emb, codes=codes, temperature=temperature)
        audio = np.asarray(tts.infer(TEXT, voice={"speaker_emb": emb, "codes": codes}, temperature=temperature),
                           dtype=np.float32)
        sf.write(out / f"{name}.wav", audio, tts.sample_rate)
        print(f"  {name}: {len(audio) / tts.sample_rate:.1f}s")


if __name__ == "__main__":
    main()
