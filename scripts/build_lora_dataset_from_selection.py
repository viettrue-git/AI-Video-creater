"""Build a kohya-style LoRA dataset folder (NNNN.png + NNNN.txt caption) from lora/<name>/dataset-selection.json.

  python scripts/build_lora_dataset_from_selection.py lora/tam-explorer-v1
Caption = "<trigger>, <caption>". The dataset folder is rebuilt from scratch each run (selection = source of truth).
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lora_dir = ROOT / sys.argv[1]
    selection = json.loads((lora_dir / "dataset-selection.json").read_text(encoding="utf-8-sig"))
    dataset = lora_dir / "dataset"
    if dataset.exists():
        shutil.rmtree(dataset)  # also drops stale cached latents (*.npz)
    dataset.mkdir(parents=True)
    missing = [img["src"] for img in selection["images"] if not (ROOT / img["src"]).exists()]
    if missing:
        sys.exit("Missing source images:\n  " + "\n  ".join(missing))
    for i, img in enumerate(selection["images"], 1):
        shutil.copy(ROOT / img["src"], dataset / f"{i:04d}.png")
        (dataset / f"{i:04d}.txt").write_text(f"{selection['trigger']}, {img['caption']}", encoding="utf-8")
    print(f"OK {len(selection['images'])} images + captions -> {dataset}")


if __name__ == "__main__":
    main()
