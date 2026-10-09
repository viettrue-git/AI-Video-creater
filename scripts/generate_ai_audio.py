"""Generate ambience (Stable Audio 3 Small-SFX) or instrumental music (ACE-Step 1.5 turbo) via the ComfyUI API.

  python scripts/generate_ai_audio.py sfx "calm lake water lapping, crickets at night" 30 out.flac
  python scripts/generate_ai_audio.py music "warm acoustic guitar, soft piano, calm, hopeful" 40 out.flac --bpm 80
ComfyUI must be running (restart it first if it holds the Wan video model: RAM is tight on 16GB).
"""
import argparse
import sys
import time
from pathlib import Path

from comfyui_api_client import ComfyUIClient, ComfyUIError
from workflow_template_utils import load_workflow_template, with_inputs

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = {"sfx": "workflows/api/sfx-stable-audio-3-small-v1.json",
             "music": "workflows/api/music-ace-step-1-5-turbo-v1.json"}
SFX_NEGATIVE = "music, melody, singing, speech, voice, talking, distortion, clipping, low quality"


def build(kind, prompt, seconds, seed, bpm):
    template = load_workflow_template(ROOT / WORKFLOWS[kind])
    common = {"IN_Seconds": {"seconds": float(seconds)}, "IN_Sampler": {"seed": seed}}
    if kind == "sfx":  # ambience must stay non-musical
        return with_inputs(template, {**common, "IN_PositivePrompt": {"text": prompt},
                                      "IN_NegativePrompt": {"text": SFX_NEGATIVE}})
    return with_inputs(template, {**common, "IN_Music": {"tags": prompt, "lyrics": "[Instrumental]", "seed": seed,
                                                         "duration": float(seconds), "bpm": bpm}})


def generate(kind, prompt, seconds, out, seed=111111, bpm=90):
    client = ComfyUIClient(timeout=120)
    if not client.is_alive():
        raise SystemExit("ComfyUI is not running")
    started = time.time()
    entry = client.wait_for_result(client.queue_prompt(build(kind, prompt, seconds, seed, bpm)), max_wait_seconds=1800)
    if not client.download_images(entry, [Path(out)]):
        raise ComfyUIError("finished but returned no audio")
    return round(time.time() - started, 1)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=WORKFLOWS)
    p.add_argument("prompt")
    p.add_argument("seconds", type=float)
    p.add_argument("out")
    p.add_argument("--seed", type=int, default=111111)
    p.add_argument("--bpm", type=int, default=90)
    a = p.parse_args()
    seconds = generate(a.kind, a.prompt, a.seconds, ROOT / a.out, a.seed, a.bpm)
    print(f"OK {a.out} ({a.kind}, {a.seconds}s audio) in {seconds}s")


if __name__ == "__main__":
    main()
