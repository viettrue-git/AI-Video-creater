# Research: SDXL Character LoRA Training on RTX 3060 12GB (Windows 11)

Date: 2026-10-07 · Scope: tool choice, install, config, captioning, eval, gotchas · Read-only research (nothing installed).
Local check: `py -0p` -> Python 3.14 (default) + 3.12 only. **No 3.10.** `C:\AIVideoManager\tools\` exists (has `vieneu-tts-venv`).

## 1. Tool comparison

| Tool | Type | Windows | Python | Torch | Install size (venv) | License | Fit |
|---|---|---|---|---|---|---|---|
| **kohya-ss/sd-scripts** v0.12.0 (2026-09-24) | CLI, TOML configs | Yes (official steps; ARM64 added) | 3.10 official; 3.11/3.12 "untested, may work" | 2.6.0 cu124 min (2.8+ cu128 for RTX 50) | ~6-7 GB (torch ~2.5-3 GB, rest deps) + pip cache | Apache-2.0 | **Best**: scriptable, SDXL reference impl, smallest |
| bmaltais/kohya_ss v26.0.0 | Gradio GUI wrapping sd-scripts | Yes (setup.bat, uv or pip) | 3.10 (`.python-version`) | bundled | ~8-10 GB | Apache-2.0 | GUI overhead, wants 3.10; no benefit for automation |
| OneTrainer | GUI + CLI (JSON config) | Yes | >=3.10, <3.14 | own reqs | ~7-9 GB | AGPL-3.0 (tool only; outputs unaffected) | Good but configs GUI-centric, masked training nice-to-have |
| ostris/ai-toolkit | CLI YAML + web UI | Yes (manual or Easy-Install) | 3.10+, 3.12 recommended | 2.13 cu130 | ~8-10 GB (+ node UI optional) | MIT | Flux/Wan-focused; SDXL supported but less tuned/tested for 12GB |
| SimpleTuner | CLI | Linux-first, Windows via WSL only | 3.11-3.12 | recent | large | AGPL-3.0 | Not recommended on native Windows |

License note: all are tools; trained LoRA weights are your output. Commercial use limited only by SDXL base license (CreativeML Open RAIL++-M -> commercial OK with use restrictions).

**Recommendation: kohya-ss/sd-scripts (CLI)** — reference SDXL LoRA impl, TOML config = easy automation, Apache-2.0, smallest footprint, LoRA format loads natively in ComfyUI LoraLoader. Use Python **3.12** (only option without installing 3.10; widely reported working; fallback = install 3.10.11 if a dep fails).

### Install (proposed, NOT executed)
```powershell
cd C:\AIVideoManager\tools
git clone https://github.com/kohya-ss/sd-scripts.git lora-trainer
cd lora-trainer
git checkout v0.12.0            # pin tag (verify exact tag name)
py -3.12 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
pip install --upgrade -r requirements.txt     # includes bitsandbytes (Windows wheels native since 0.43+)
accelerate config   # This machine / No distributed / NO / NO / NO / all / bf16
```
- If torch 2.6 has no cp312 issue (it has cp312 wheels: OK). Newer torch (2.8 cu128) also fine on 3060; keep README-pinned version for least surprise.
- Skip xformers; use `--sdpa`.
- Set `HF_HOME=C:\AIVideoManager\tools\lora-trainer\hf-cache` (tokenizers/CLIP configs download ~ small, but keeps C:\Users clean).
- Base model: reuse ComfyUI's `sd_xl_base_1.0.safetensors` by absolute path (no copy, read-only).

## 2. Recommended config (12GB VRAM / 16GB RAM)

| Param | Value | Why |
|---|---|---|
| Network | plain LoRA (`networks.lora`) | Most compatible with ComfyUI + IP-Adapter; LoCon/LoKr add little for single character |
| Rank / alpha | 32 / 16 | Char identity; 16/8 if overfits/small set. File ~170 MB (r32) |
| Train | **UNet only** (`--network_train_unet_only`) | Kohya docs: "highly recommended for SDXL"; enables TE caching |
| Optimizer A (default) | AdamW8bit, lr 1e-4, cosine, warmup 5% | Predictable; `--network_alpha` half of dim |
| Optimizer B | Prodigy lr=1.0, `d_coef=1 decouple=True weight_decay=0.01 use_bias_correction=True safeguard_warmup=True`, constant | Auto-LR, good when unsure; more VRAM (~+1GB) |
| Optimizer C (lowest VRAM) | Adafactor lr 1e-4..3e-4 (civitai 3060 guide used 3e-4), args `scale_parameter=False relative_step=False warmup_init=False` | If OOM |
| Precision | `mixed_precision=bf16`, `save_precision=bf16` (or fp16 for max loader compat) | RTX 3060 = Ampere -> **bf16 supported**, fewer NaN than fp16 |
| `--full_bf16` | optional | Saves ~1-2GB VRAM; slight quality risk; use only if OOM |
| VAE | `--no_half_vae` | SDXL VAE NaNs in fp16 (or use madebyollin fp16-fix VAE) |
| Resolution | `resolution=1024` (area cap), `enable_bucket`, `bucket_no_upscale`, `bucket_reso_steps=64`, `min_bucket_reso=640`, `max_bucket_reso=1536` | 768x1344 = 1.03 MP <= 1024² -> trained at native 768x1344 (standard SDXL bucket) |
| Batch | 1 (grad accum 1-2) | 12GB limit |
| Grad checkpointing | on | Mandatory at 12GB |
| Caching | `cache_latents`, `cache_latents_to_disk`, `cache_text_encoder_outputs`, `cache_text_encoder_outputs_to_disk` | Frees VRAM; VAE/TE not held. Note: TE cache disables caption shuffle/dropout |
| Attention | `--sdpa` | No xformers needed |
| Steps | 30 imgs × 10 repeats = 300 steps/epoch × 8 epochs = **2400 steps**; save every epoch | Typical char: 1500-3000 steps. 40 imgs -> repeats 8 |
| noise_offset | 0.0357 (or 0) | Mild; stylized 3D renders don't need dark/light extremes |
| min_snr_gamma | 5 | Stabilizes, faster convergence |
| Samples | every epoch, 3 prompts, 28 steps, euler_a | Costs ~30-60 s each at 3060 |
| Seed | fixed (e.g. 42) | Reproducible |

### dataset.toml
```toml
[general]
enable_bucket = true
bucket_no_upscale = true
bucket_reso_steps = 64
caption_extension = ".txt"
shuffle_caption = false        # TE cached -> must be false
keep_tokens = 1

[[datasets]]
resolution = 1024
batch_size = 1
  [[datasets.subsets]]
  image_dir = 'C:\AIVideoManager\characters\<char>\lora-dataset\img'
  num_repeats = 10
```

### train.toml (run: `accelerate launch --num_cpu_threads_per_process 1 sdxl_train_network.py --config_file train.toml`)
```toml
pretrained_model_name_or_path = 'C:\path\to\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors'
dataset_config = 'C:\AIVideoManager\tools\lora-trainer\configs\dataset.toml'
output_dir = 'C:\AIVideoManager\tools\lora-trainer\output\<char>'
output_name = '<char>_sdxl_lora_r32_v1'
save_model_as = 'safetensors'
save_precision = 'bf16'
save_every_n_epochs = 1
max_train_epochs = 8
network_module = 'networks.lora'
network_dim = 32
network_alpha = 16
network_train_unet_only = true
optimizer_type = 'AdamW8bit'
learning_rate = 1e-4
unet_lr = 1e-4
lr_scheduler = 'cosine'
lr_warmup_steps = 120
mixed_precision = 'bf16'
no_half_vae = true
gradient_checkpointing = true
sdpa = true
cache_latents = true
cache_latents_to_disk = true
cache_text_encoder_outputs = true
cache_text_encoder_outputs_to_disk = true
min_snr_gamma = 5
noise_offset = 0.0357
max_data_loader_n_workers = 1
persistent_data_loader_workers = true
seed = 42
logging_dir = 'C:\AIVideoManager\tools\lora-trainer\logs'
sample_every_n_epochs = 1
sample_prompts = 'C:\AIVideoManager\tools\lora-trainer\configs\sample-prompts.txt'
sample_sampler = 'euler_a'
```
sample-prompts.txt (kohya syntax): `ohwx boy, standing in jungle ruins, full body --w 768 --h 1344 --s 28 --l 6 --d 42 --n blurry, lowres`

## 3. Speed / memory (RTX 3060 12GB, estimates from community reports)

| Metric | Expected |
|---|---|
| Speed | ~1.4-2.0 s/it (768x1344, bs1, grad ckpt, sdpa, AdamW8bit); Prodigy ~10-20% slower |
| Total | 2400 steps ≈ 60-80 min + caching ~3-5 min + samples ~8×2 min ≈ **~1.5 h** |
| Peak VRAM | ~9-11 GB (AdamW8bit, r32); Adafactor/full_bf16 ~8 GB |
| Peak RAM | ~10-14 GB during model load (fp16 checkpoint 6.9 GB expanded), ~6-8 GB during training |

OOM avoidance (16 GB RAM):
- Close ComfyUI before training (frees VRAM + RAM). Never run both.
- `max_data_loader_n_workers=1` (each worker copies dataset state on Windows spawn).
- `--lowram` loads model straight to VRAM (helps RAM peak; only useful because VRAM is 12GB) — try if RAM OOM at load.
- Caching to disk (done above). Pagefile 32 GB as safety.
- VRAM OOM ladder: rank 32->16 -> `full_bf16` -> Adafactor -> `fused_backward_pass` (Adafactor only, big saving).
- Disable Windows GPU-accelerated apps (browser HW accel) ~0.5-1 GB VRAM.

## 4. Captioning

| Rule | Detail |
|---|---|
| Trigger | rare short token, not real word: `ohwx`, `sks` (sks has weak gun bias), or made-up `zrkexplorer`. Must tokenize to few CLIP tokens. Put **first** in every caption |
| Class word | Yes: `ohwx boy` / `ohwx young man` — anchors to prior, helps prompt composition |
| Omit (binds to trigger) | fixed identity: face shape, hair color/style, eye color, skin, signature outfit (if outfit always same), art style "3d render" if all same style |
| Describe (variable) | pose, action, expression, camera angle/framing (close-up/full body), background, lighting, props, outfit changes |
| Length | 1-2 short sentences or 10-30 tags; consistent format across set |
| Style | SDXL works with natural language or booru tags; pick one. E.g. `ohwx boy, full body, walking on rope bridge, jungle background, soft morning light, low angle` |
| Dataset | vary angles (front/3/4/side/back), distances, expressions, backgrounds; drop near-duplicates; avoid same background in >30% |
| Reg images | skip (adds time; not needed for single char with UNet-only) |

## 5. Evaluation / ComfyUI use

- Keep all 8 epoch checkpoints. Pick via fixed-seed grid: epochs × strength (0.6/0.8/1.0) with prompts: (a) trigger simple, (b) trigger + new scene/pose not in dataset, (c) no trigger (check leakage), (d) another character (bleed).
- Overfit signs: background/lighting from dataset reappear, same pose, ignores prompt, burnt contrast, artifacts at strength 1.0. Underfit: identity drifts. Usually best = epoch 5-7 of 8.
- Optional: kohya `--validation_split` / val loss (newer versions), but visual grid more reliable.
- ComfyUI: `LoraLoaderModelOnly` (UNet-only LoRA has no TE weights; LoraLoader works too, clip strength irrelevant).
- With IP-Adapter PLUS: LoRA 0.7-0.9 + IPA weight 0.4-0.6, IPA end_at 0.6-0.8. Both pulling identity -> lower each; start LoRA 0.8 / IPA 0.5 and tune. If LoRA is strong enough, IPA may be used only for pose/style or dropped.

## 6. Gotchas

| Issue | Note |
|---|---|
| Python 3.12 | Officially untested; most deps have cp312 wheels. Python 3.14 **don't use** (no torch/bnb wheels guarantee). Fallback: install 3.10.11 |
| bitsandbytes Windows | Official Windows wheels since 0.43 -> AdamW8bit works; if import fails, use Adafactor (no bnb) |
| xformers vs sdpa | Use `--sdpa`; xformers wheel must match exact torch build, extra 100s MB, no gain |
| HF cache | Default `%USERPROFILE%\.cache\huggingface`; set `HF_HOME` per venv. Only tokenizers/configs download (single-file SDXL checkpoint used) |
| Output naming | `output_name` + `-000001.safetensors` per epoch, final without suffix. Use kebab/underscore, version suffix; copy chosen file to `ComfyUI\models\loras\` |
| TE caching | Disables `shuffle_caption`, caption dropout, `token_warmup` |
| fp16 NaN | Use bf16 + `no_half_vae` |
| accelerate config | Can skip interactive by passing `--mixed_precision bf16 --num_processes 1` to `accelerate launch` |
| Windows paths in TOML | Use single quotes (literal strings) to avoid backslash escapes |
| ComfyUI venv | Separate venv; different torch (2.6 vs 2.11) is fine as long as nothing installs into ComfyUI venv |

## Sources
- https://github.com/kohya-ss/sd-scripts (README, v0.12.0, install, license)
- https://github.com/kohya-ss/sd-scripts/blob/main/docs/train_SDXL-en.md
- https://github.com/bmaltais/kohya_ss
- https://github.com/ostris/ai-toolkit
- https://offlinecreator.com/compare/kohya-vs-onetrainer-for-lora-training
- https://civitai.com/articles/5255/my-sdxl-lora-experience-12gb-rtx3060-gpu-local-training-wkohya-ss
- https://github.com/FurkanGozukara/Stable-Diffusion/blob/main/Tutorials/How-To-Do-Kohya-SDXL-LoRA-Training-With-Weak-Low-VRAM-GPUs.md
- https://localaimaster.com/blog/image-lora-training-local-guide

## Unresolved questions
1. Python 3.12 with sd-scripts v0.12.0 requirements unverified locally — confirm at install; may need 3.10.11.
2. Exact v0.12.0 tag name and whether it raised min torch above 2.6 (README says 2.6 min) — check `requirements.txt` after clone.
3. s/it figures are community estimates, not measured on this PC — measure on first run.
4. Trigger token choice: confirm character name convention for project (`ohwx` vs custom).
5. Outfit: is it fixed across all shots? Decides whether outfit is omitted (bound to trigger) or captioned.
6. Path to ComfyUI SDXL base checkpoint not checked.
