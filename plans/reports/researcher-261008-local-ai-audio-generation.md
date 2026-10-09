# Research: Local AI Audio Generation for Auto BGM/Ambience (2026-10-08)

Target: RTX 3060 12GB, 16GB RAM + 32GB pagefile, ComfyUI 0.37.0, ~30 s vertical clips, monetized (YT/TikTok) -> commercial-use license required.
Legend: OK = commercial use of outputs allowed; NC = non-commercial only. Speeds marked "est." are my estimates (no 3060 benchmarks found).

## 1. Text -> ambience / SFX

| Model | License (outputs) | HF gated? | Disk | VRAM | Max len | ComfyUI | Notes |
|---|---|---|---|---|---|---|---|
| **Stable Audio 3 Small-SFX** (May 2026, 459M) | Stability Community License: OK free if org revenue < $1M/yr | Comfy-Org repack: not gated (stabilityai originals likely gated, accept form) | ckpt 2.27 GB + T5Gemma TE 1.19 GB = ~3.5 GB | runs on CPU; GPU trivial (<4 GB) | 2:00 | **Native**, official templates (needs ComfyUI >= 0.22) | trained on licensed AudioSparx + Freesound CC; user reports mixed ("~10% better than SAO 1.0", some noisy outputs) |
| Stable Audio 3 Medium (1.4B) | same | same | 9.22 GB (+TE) | GPU req; est. 6-10 GB | ~6:20 | Native | music+SFX, better structure; also does inpainting/editing |
| Stable Audio Open 1.0 (2024) | Community License, OK < $1M | **Gated** (form: name/email/country/use) | ~4.8 GB ckpt + T5 | ~6-8 GB | 47 s | Native (CheckpointLoader + EmptyLatentAudio + VAEDecodeAudio) | superseded by SA3 |
| AudioLDM2 | CC-BY-NC-SA 4.0 | no | ~3-4 GB | ~6 GB | ~10 s typical | custom nodes | **NC - skip** |
| Tango / Tango2 | CC-BY-NC-SA | no | ~3 GB | ~8 GB | 10 s | custom | **NC - skip** |
| TangoFlux | uses SAO VAE; license unclear (check) | no | ~2 GB | ~6 GB | 30 s | custom | unverified license |

## 2. Text -> background music (instrumental)

| Model | License | Disk | VRAM | Len | ComfyUI | Quality for 30-60 s cinematic/ambient |
|---|---|---|---|---|---|---|
| **ACE-Step 1.5** (Jan/Feb 2026, StepFun+ACE Studio) | Apache-2.0 per HF/wiki, MIT per GitHub - both permissive, OK | turbo DiT 4.79 GB + Qwen 0.6B/1.7B TE + VAE (~7-9 GB); XL variants 9.97 GB each | turbo <4-8 GB; XL needs >=12 GB w/ offload (20 GB rec.) | 10 s - 10 min | **Native** (Comfy-Org/ace_step_1.5_ComfyUI_files, AIO ckpt or split) | best open option for full tracks; 4-min song <10 s on 3090; instrumental via tags/empty lyrics ("[instrumental]"); 1000+ instrument tags. Pop/song-biased, ambient OK but can be "busy" |
| ACE-Step 1.0 (2025) | Apache-2.0 | ~7 GB | ~8 GB | 4 min | native | superseded |
| **Stable Audio 3 Small-Music / Medium** | Community License OK < $1M | 2.27 / 9.22 GB | CPU / GPU | 2:00 / 6:20 | Native | instrumental only (no vocals) - fine for BGM; trained on licensed WMG/UMG-partner data -> lowest copyright risk; good for loops/ambient pads |
| SongGeneration 2 / LeVo 2 (Tencent, Mar 2026, 4B) | **NC** (code+weights) | ~10+ GB | 10-16 GB | 4:30 | custom | **skip** (NC) |
| YuE | Apache-2.0 (from memory, verify) | ~15 GB | 24 GB+ ideal | minutes | custom | song/lyrics-focused, slow on 12 GB; overkill |
| DiffRhythm | Apache-2.0 (code+DiT) | ~4 GB | ~8 GB | 95 s / 4:45 | custom | song-focused, vocals; weaker instrumentals |
| MusicGen (Meta) | weights **CC-BY-NC 4.0** | - | - | - | - | **skip** |

## 3. Video -> audio (Foley synced to frames)

| Model | Weights license | Disk | VRAM | Len | ComfyUI | Notes |
|---|---|---|---|---|---|---|
| MMAudio v2 | **CC-BY-NC 4.0** | ~4 GB | ~6 GB | 8 s trained | kijai/ComfyUI-MMAudio | best sync but **NC - not usable for monetized** |
| HunyuanVideo-Foley (Tencent) | Tencent Hunyuan Community License: commercial OK, **excludes EU/UK/S.Korea**, >100M MAU needs separate license | main 10.3 GB fp16 / 5.34 GB fp8 + Synchformer ~0.5-1 GB + DAC-VAE ~0.7-1.5 GB + SigLIP2 + CLAP (~8-10 GB total fp8) | 10-12 GB fp16; <8 GB fp8; <4 GB block-swap | ~5-10 s clips (chunk 30 s) | custom: phazei/ComfyUI-HunyuanVideo-Foley (fp8, BlockSwap, torch.compile e5m2 on 30xx) | high quality; slow on 3060 (block-swap up to ~60 s per 5 s audio) |
| ThinkSound | Apache tag but README says **research/edu only, no commercial** | ~5 GB | ~8-12 GB | ~10 s | community | **skip** |

Takeaway: V2A is not worth it for this pipeline. 3D-animated narration videos need ambience bed + music, not frame-accurate foley; the only commercial-OK V2A option (Hunyuan) is heavy, geo-restricted, and clip-length limited.

## 4. Automatic retrieval alternatives

| Source | Key? | Limits | Commercial / automation terms | Verdict |
|---|---|---|---|---|
| Freesound APIv2 | free API key (token); **OAuth2 needed for original-file download**, previews (mp3/ogg HQ) via token only | 60 req/min, 2000/day; downloads 30/min, 500/day | filter `license:"Creative Commons 0"`; **API ToS: commercial use of API "negotiated case by case" with UPF**; copies only as needed, no DB mirroring | legally grey for monetized automation without asking UPF; CC0 sound itself is fine. Also quality curation needs ranking (rating/downloads) |
| Pixabay API | free key | 100 req/60 s, cache 24 h | docs say "made for real human requests... systematic mass downloads not allowed"; music/SFX mention exists but public endpoints documented only for images/videos | not suitable for automated audio pulls |

## 5. Recommendation for this PC

**Pick: Stable Audio 3 (Small-SFX for ambience) + ACE-Step 1.5 Turbo (music).** Both native ComfyUI, commercial OK, no gated download (Comfy-Org repacks).
- Alt minimal: SA3 Small-SFX + SA3 Small-Music only (one TE, ~5.7 GB disk) - simplest, lowest copyright risk; music less "song-like" but ambient/cinematic pads fit narration BGM.
- Optional quality step: SA3 Medium (9.22 GB) for music instead of ACE-Step.

Disk:
| Option | Files | Total |
|---|---|---|
| A (rec.) | SA3 small_sfx 2.27 + t5gemma 1.19 + ACE turbo DiT 4.79 + qwen0.6B (~1.2) + VAE (~0.3) (or AIO ckpt) | ~10 GB |
| B (minimal) | SA3 small_sfx + small_music + t5gemma | ~5.7 GB |
| C (+Medium) | B + medium 9.22 | ~15 GB |

Sequencing with Wan video (12 GB VRAM / 16 GB RAM):
- Do NOT co-load with Wan. Run audio as separate ComfyUI API job **after** Wan job finishes (ComfyUI unloads/swaps models; call `POST /free {"unload_models":true,"free_memory":true}` between jobs to be safe).
- Audio models are small (<=~8 GB VRAM peak est.), so they fit comfortably once Wan is unloaded; RAM pressure low (SA3 small ~3.5 GB, ACE turbo ~7 GB). Pagefile covers model swap.
- Better: audio depends only on the script, not the video -> generate audio **before/parallel-in-queue** with TTS, independent of Wan frames.

Est. generation time per 30 s clip on 3060 (est., scaled from 3090/H200 numbers):
| Model | est. time |
|---|---|
| SA3 Small-SFX 30 s (GPU) | ~3-10 s (+model load ~10-20 s) |
| SA3 Medium 30-60 s | ~15-40 s |
| ACE-Step 1.5 Turbo 30-60 s | ~5-15 s (+load) |
| HunyuanFoley fp8 30 s (6x5 s chunks) | ~3-6 min (not recommended) |

Integration approach:
- **ComfyUI API workflow** (recommended): export workflow JSON (API format) from official templates; Python driver patches prompt text, duration (e.g. 32 s), seed; POST /prompt; poll /history; fetch from output/. Same mechanism already used for Wan -> DRY, no extra venv.
- Prompt gen: LLM/script step derives `ambience_prompt` + `music_prompt` (mood, bpm, instruments, "no vocals") from scene script.
- Mix with ffmpeg: narration 0 dB, music ~-20 to -24 dB with sidechain ducking (`sidechaincompress`) or fixed -18 dB, ambience ~-26 dB; `loudnorm` to -14 LUFS (YouTube/TikTok); fade in/out 1 s.
- Separate venv only needed for ACE-Step standalone (Gradio/API, own portable package) if ComfyUI node lags - not needed now.
- Keep a small curated CC0 fallback library (manually pre-approved) for when generation is rejected by QC.

## Sources
- SA3 specs/license: https://studio.aifilms.ai/blog/stable-audio-3-stability-ai-open-weight-music-sfx ; https://aiweekly.co/alerts/stability-ai-ships-stable-audio-3-with-open-weight-models ; https://blog.dubspot.com/stable-audio-3-review
- SA3 ComfyUI: https://docs.comfy.org/tutorials/audio/stable-audio/stable-audio-3 ; https://blog.comfy.org/p/stable-audio-3-day-0-support ; files https://huggingface.co/Comfy-Org/stable-audio-3/tree/main/checkpoints
- SA3 user feedback: https://reddit.sentinel-team.org/posts/1tj7afx/snapshots/2026-05-21T18%3A20%3A48.87163Z
- SAO 1.0: https://huggingface.co/stabilityai/stable-audio-open-1.0
- ACE-Step 1.5: https://github.com/ace-step/ACE-Step-1.5 ; https://docs.comfy.org/tutorials/audio/ace-step/ace-step-v1-5 ; https://comfyui-wiki.com/en/models/ace-step/ace-step-v1-5 ; https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files
- SongGeneration 2: https://gaga.art/blog/songgeneration-2/ ; https://huggingface.co/tencent/SongGeneration
- DiffRhythm: https://www.huggingface.co/ASLP-lab/DiffRhythm-base
- MMAudio license: https://huggingface.co/AEmotionStudio/mmaudio-models/blob/main/README.md
- HunyuanVideo-Foley: https://github.com/phazei/ComfyUI-HunyuanVideo-Foley ; https://studio.aifilms.ai/blog/hunyuanvideo-foley
- ThinkSound: https://huggingface.co/FunAudioLLM/ThinkSound
- Freesound: https://freesound.org/docs/api/overview.html ; https://freesound.org/help/tos_api/
- Pixabay: https://pixabay.com/api/docs/

## Unresolved questions
1. SA3 Community License: verify exact text re outputs ownership + whether $1M threshold counts individual creator income (likely yes, well under).
2. ACE-Step 1.5 license: GitHub says MIT, HF/wiki Apache-2.0 - both permissive; confirm on HF model card before use.
3. No real RTX 3060 timings found for SA3/ACE-Step 1.5 - benchmark after install.
4. SA3 Small-SFX quality for nature ambience (lake, crickets) unverified; some users report noise - A/B vs Medium needed.
5. Does ComfyUI 0.37.0 ACE-Step 1.5 native node expose instrumental-only mode / which TE (0.6B vs 1.7B) fits alongside 16 GB RAM.
6. HunyuanVideo-Foley territory clause: does EU/UK audience on YouTube matter for output use? Moot if V2A skipped.
7. YuE, TangoFlux licenses not re-verified this session.
8. YouTube/TikTok AI-audio disclosure policies + Content ID false-match risk for AI music not researched.
