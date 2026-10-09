"""Run a Character Consistency test matrix (scene x IPA weight x seed) through ComfyUI.

Example (Step A: 1 scene, 5 weights incl. 0 = no-IPA baseline, 2 seeds):
  ComfyUI/venv/Scripts/python.exe scripts/character_consistency_test_runner.py ^
      --test-id A01 --scenes S1 --weights 0,0.5,0.7,0.85,1.0 --seeds 111111,222222

Images go to experiments/<test-id>/, one row per image is appended to experiments/log.csv
(score columns left blank for manual scoring), and a contact sheet is built for comparison.
Already-rendered images are skipped, so an interrupted run can simply be restarted.
"""
import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

from comfyui_api_client import DEFAULT_SERVER, ComfyUIClient, ComfyUIError
from experiment_contact_sheet_builder import build_contact_sheet
from workflow_template_utils import find_node_id_by_title, load_workflow_template, with_inputs

ROOT = Path(__file__).resolve().parent.parent
LOG_COLUMNS = ["date", "test_id", "checkpoint", "lora", "ref_image", "ipa_weight", "weight_type", "end_at",
               "seed", "steps", "cfg", "sampler", "width", "height", "scene", "render_seconds",
               "face", "hair", "clothes", "backpack", "body", "prompt_adherence", "artifacts",
               "identity_score", "image_file", "notes"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test-id", required=True)
    p.add_argument("--scenes", default="S1", help="comma list of scene ids from the scenes file")
    p.add_argument("--weights", default="0.5,0.7,0.85,1.0")
    p.add_argument("--seeds", default="111111,222222")
    p.add_argument("--ref", default="projects/P001_rung_co/refs/char_main_front.png")
    p.add_argument("--checkpoint", default="sd_xl_base_1.0.safetensors")
    p.add_argument("--weight-type", default="linear")
    p.add_argument("--end-at", type=float, default=1.0)
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--cfg", type=float, default=6.5)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=1344)
    p.add_argument("--workflow", default="workflows/api/character-scene-ipadapter-v1.json")
    p.add_argument("--scenes-file", default="experiments/character-consistency-test-scenes.json")
    p.add_argument("--server", default=DEFAULT_SERVER)
    p.add_argument("--out-dir", default=None, help="image folder (default experiments/<test-id>)")
    p.add_argument("--log-file", default="experiments/log.csv", help="scoring log CSV ('' = no log)")
    p.add_argument("--lora", default="", help="LoRA file in ComfyUI/models/loras (switches to the LoRA workflow)")
    p.add_argument("--lora-strength", type=float, default=0.8)
    return p.parse_args()


def _write_row(log_path, row):
    is_new = not log_path.exists() or log_path.stat().st_size == 0
    # utf-8-sig so Excel shows Vietnamese notes correctly
    with log_path.open("a", newline="", encoding="utf-8-sig" if is_new else "utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def append_log_row(row, log_file):
    """Append to the scoring log; if Excel locks it, keep the row in log-pending.csv instead of crashing."""
    if not log_file:
        return
    log_path = ROOT / log_file
    try:
        _write_row(log_path, row)
    except PermissionError:
        pending = log_path.with_name("log-pending.csv")
        _write_row(pending, row)
        print(f"  ! log.csv is locked (open in Excel?) -> row saved to {pending.name}, merge it later")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 consoles choke on Vietnamese errors
    args = parse_args()
    scenes_cfg = json.loads((ROOT / args.scenes_file).read_text(encoding="utf-8-sig"))
    workflow_file = "workflows/api/character-scene-ipadapter-lora-v1.json" if args.lora else args.workflow
    template = load_workflow_template(ROOT / workflow_file)
    scene_ids = args.scenes.split(",")
    weights = [float(w) for w in args.weights.split(",")]
    seeds = [int(s) for s in args.seeds.split(",")]
    out_dir = ROOT / (args.out_dir or f"experiments/{args.test_id}")

    client = ComfyUIClient(args.server)
    if not client.is_alive():
        sys.exit(f"ComfyUI is not running at {args.server}. Start it first.")
    ref_name = client.upload_image(ROOT / args.ref)
    sampler = template[find_node_id_by_title(template, "IN_Sampler")]["inputs"]

    total, done, failed = len(scene_ids) * len(weights) * len(seeds), 0, 0
    for scene_id in scene_ids:
        # optional per-shot character block (e.g. a hand close-up must not describe the face)
        character = scenes_cfg.get("character_overrides", {}).get(scene_id, scenes_cfg["character_block"])
        # empty override = shot without the character (e.g. campfire close-up, empty landscape)
        prompt = ", ".join(p for p in (scenes_cfg["scenes"][scene_id], character, scenes_cfg["style_block"]) if p)
        for seed in seeds:
            for weight in weights:
                done += 1
                image_path = out_dir / f"{scene_id}_w{weight:.2f}_s{seed}.png"
                if image_path.exists():
                    print(f"[{done}/{total}] skip existing {image_path.name}")
                    continue
                overrides = {"IN_Lora": {"lora_name": args.lora, "strength_model": args.lora_strength}} if args.lora else {}
                workflow = with_inputs(template, {
                    **overrides,
                    "IN_Checkpoint": {"ckpt_name": args.checkpoint},
                    "IN_PositivePrompt": {"text": prompt},
                    "IN_NegativePrompt": {"text": scenes_cfg["negative"]},
                    "IN_Size": {"width": args.width, "height": args.height},
                    "IN_RefImage": {"image": ref_name},
                    "IN_IPAdapter": {"weight": weight, "weight_type": args.weight_type, "end_at": args.end_at},
                    "IN_Sampler": {"seed": seed, "steps": args.steps, "cfg": args.cfg},
                    "OUT_Image": {"filename_prefix": f"tests/{args.test_id}/{image_path.stem}"},
                })
                started = time.time()
                try:
                    entry = client.wait_for_result(client.queue_prompt(workflow))
                    if not client.download_images(entry, [image_path]):
                        raise ComfyUIError("finished but returned no output image")
                except ComfyUIError as e:
                    message = str(e)
                    print(f"[{done}/{total}] FAILED {image_path.name}: {message[:300]}")
                    if "CUDA error" in message or "Cannot reach ComfyUI" in message:
                        # server/CUDA state is broken; every next job would fail too
                        sys.exit("Stopped -> restart ComfyUI, then re-run (finished images are skipped).")
                    failed += 1
                    continue
                seconds = client.execution_seconds(entry) or round(time.time() - started, 1)
                print(f"[{done}/{total}] {image_path.name} ({seconds}s)")
                append_log_row({
                    "date": date.today().isoformat(), "test_id": args.test_id, "checkpoint": args.checkpoint,
                    "lora": f"{args.lora}@{args.lora_strength}" if args.lora else "", "ref_image": Path(args.ref).name, "ipa_weight": weight,
                    "weight_type": args.weight_type, "end_at": args.end_at, "seed": seed, "steps": args.steps,
                    "cfg": args.cfg, "sampler": f"{sampler['sampler_name']}/{sampler['scheduler']}",
                    "width": args.width, "height": args.height, "scene": scene_id, "render_seconds": seconds,
                    "image_file": str(image_path.relative_to(ROOT)),
                }, args.log_file)

    rows = [[("REF", ROOT / args.ref)] + [(f"{sc} s{sd} w{w:.2f}", out_dir / f"{sc}_w{w:.2f}_s{sd}.png")
                                          for w in weights]
            for sc in scene_ids for sd in seeds]
    sheet = build_contact_sheet(rows, out_dir / "contact-sheet.jpg")
    print(f"Contact sheet: {sheet}")
    if failed:
        sys.exit(f"{failed} image(s) failed — re-run to retry (finished images are skipped)")


if __name__ == "__main__":
    main()
