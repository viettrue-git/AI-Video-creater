# Research: models, licenses, Vietnamese TTS, Wan on 12GB (2026-10-05)

Target: RTX 3060 12GB, 16GB RAM (→32-64GB), Win11, ComfyUI 0.37, commercial use, 9:16, VI narrator, stylized 3D (non-trademark).
Not legal advice. Civitai "allowCommercialUse=Image" = selling/monetizing generated images OK; "Rent/RentCivit" = hosting inference for money OK.

---

## 1. Image models

### 1a. SDXL stylized-3D checkpoints (all base SDXL 1.0, NOT Pony/Illustrious)

| Model | Source | License / Civitai perms | Commercial outputs? | Size | Notes |
|---|---|---|---|---|---|
| **DynaVision XL** v0.6.1.0 | https://civitai.com/models/122606 | OpenRAIL(++)-M; Image + RentCivit, no credit, derivatives OK | YES (images) | ~6.8GB | Purpose-built "stylized 3D CG animation" look; best style fit. Merge of NightVision XL + 3D cartoon LoRAs. Some mirrors (HF imagepipeline) show stricter text — trust Civitai author page |
| **Samaritan 3D Cartoon** v4.0 SDXL | https://civitai.com/models/81270 | Image OK, no credit, derivatives OK | YES (images) | ~6.5GB | Explicit 3D-cartoon fine-tune |
| **RealCartoon-XL** V7 | https://civitai.com/models/125907 | CreativeML OpenRAIL-M; Image+Rent+RentCivit, no credit | YES | ~7.1GB | 2.5D/3D cartoon, very popular, last update 2024-07 |
| **ProtoVision XL** v6.6.0 | https://civitai.com/models/125703 | Image + RentCivit, no credit | YES | ~6.4GB | Same author as DynaVision; 3D/semi-real, more realistic |
| **AlbedoBase XL** v3.1 | https://civitai.com/models/140737 | Image+Rent+RentCivit; credit REQUIRED; no different license | YES (with credit) | ~6.5GB | Generalist; needs style prompt/LoRA for 3D look |
| (Cartoon Arcadia) | https://civitai.com/models/136113 | Image+RentCivit; credit req. | yes | latest version is SD1.5 — skip for SDXL |

Caveats: all are community merges → provenance of merged LoRAs unknown; avoid prompts "Pixar/Disney/Dreamworks" (trademark), use "stylized 3D animated film, soft subsurface skin, big expressive eyes".
Pony / Illustrious flags:
- **Pony Diffusion V6 XL**: modified Fair AI Public License 1.0-SD; bans running inference on monetized sites/apps (applies to all merges); outputs not restricted, but derivatives inherit restriction. Avoid for "factory"/SaaS. https://civitai.com/models/257749
- **Illustrious XL**: FAIPL-1.0-SD (share-alike for model derivatives; outputs not covered) — local output commercial OK, but anime-oriented. https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0
- **NoobAI-XL**: own license w/ commercial restrictions → avoid.

### 1b. Newer image models (2026), permissive + 12GB-capable

| Model | License | Edit / ref-image? | 12GB route | Files (approx) | Verdict |
|---|---|---|---|---|---|
| **Qwen-Image-Edit-2511** (20B) | Apache-2.0 https://huggingface.co/Qwen/Qwen-Image-Edit-2511 | YES – strong character consistency, multi-image | GGUF (unsloth) Q4_0 11.9GB / Q4_K_M 13.2GB / Q3/Q2 7.5GB; partial offload; + Lightning 4-step LoRA | TE `qwen_2.5_vl_7b_fp8_scaled.safetensors` (~9.4GB), VAE `qwen_image_vae.safetensors` (~0.25GB), LoRA `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` (lightx2v, Apache) | **Best commercial ref-edit option.** Needs 32GB RAM realistically (TE+DiT > 16GB); slow on 3060 (~1-3 min/img w/ Lightning, est.) |
| **FLUX.2 [klein] 4B** | Apache-2.0 https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | YES – unified T2I + single/multi-ref edit | ~13GB bf16; fp8 / GGUF (unsloth/FLUX.2-klein-4B-GGUF) fits 12GB | small | **Best fit for 12GB + 16GB RAM.** NOTE: klein 9B & FLUX.2 dev = NON-commercial |
| **Z-Image-Turbo** (6B) | Apache-2.0 https://huggingface.co/Tongyi-MAI/Z-Image-Turbo | T2I only; Z-Image-Edit still "to be released" (Aug 2026) | fp8 ~8GB, GGUF 5-6GB, 8 steps | — | Fast, high quality T2I; no ref edit |
| HiDream-I1 | MIT | T2I (E1 edit separate) | heavy (Llama-3.1-8B TE) | large | Possible but heavy; Llama TE carries Llama license |
| **Qwen-Image 2.1** (2026-09-20) | **Qwen Research License – NON-COMMERCIAL** https://codersera.com/blog/how-to-run-qwen-image-2-1-locally-2026/ | yes | GGUF Q5/Q6 ~5-6GB | — | **Do NOT use** commercially |
| Flux.1 dev / Kontext dev | FLUX.1 dev Non-Commercial License v1.1.1 | — | — | — | see §5 |

---

## 2. Vietnamese TTS

### Local

| Model | License (code/weights) | Commercial | Quality notes | HW |
|---|---|---|---|---|
| **VieNeu-TTS v3 Turbo** https://github.com/pnnbao97/VieNeu-TTS / https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo | Apache-2.0; preset voices (consented) explicitly OK for monetized content | **YES** | 0.1B, 48kHz, 23-25 preset N/C/S voices, 3-8s cloning, emotion cues, VI-EN code-switch. v4 (better cloning) is API-only at vieneu.io | 3060: ~1.1GB VRAM, RTF ~0.02; CPU ok |
| **G-OmniVoice** https://huggingface.co/g-group-ai-lab/g-omnivoice | Apache-2.0 BUT audio tokenizer = Boson Higgs Audio 2 Community License (commercial OK < 100k annual active users, attribution to Boson & Meta) | YES w/ cap | VI fine-tune of k2-fsa/OmniVoice; reported VI WER 2.6%, SIM 0.89 (best-of-both claim) | 0.6B, fits easily |
| **VoxCPM2** https://huggingface.co/openbmb/VoxCPM2 | Apache-2.0 | YES | 2B, 30 langs incl. VI (extra SEA focus), 48kHz, voice design by text + cloning; can be unstable on long text | ~8GB VRAM |
| **ZeroTTS** https://github.com/south1907/ZeroTTS | MIT (code + weights) | YES | claims 1.03% WER (best open VI); 8 preset voices; voice encoder NOT published (clone only via their platform) | CPU realtime |
| piper-v3-vietnamese-5speakers (CakeByVPBank) https://huggingface.co/CakeByVPBank/piper-v3-vietnamese-5speakers | MIT | YES | 22kHz VITS, robotic-ish vs above, no cloning; trained on synthetic data from OmniVoice/VoxCPM2 | CPU |
| Piper official vi_VN (vais1000, 25hours_single, vivos) | per-voice MODEL_CARD; vivos dataset CC-BY-NC-SA | check each; vivos = NO | low quality | CPU |
| viXTTS (capleaf) | Coqui Public Model License | **NO** | good but non-commercial; Coqui defunct → no commercial license purchasable | — |
| F5-TTS-Vietnamese (hynt 100h/150h/1000h, EraX) | CC-BY-NC-SA-4.0 | **NO** | good | — |
| Valtec / V-TTS | CC-BY-NC-4.0 | **NO** | — | — |
| Kokoro | Apache | n/a | **no Vietnamese** | — |

### Cloud (prices ~2026, verify on official page)

| Service | VI voices | Price | Commercial | Notes |
|---|---|---|---|---|
| **Google Cloud TTS** | vi-VN Standard/WaveNet/Neural2/Chirp 3 HD (+Gemini TTS) | Chirp 3 HD ~$30/1M chars (1M free/mo); Neural2 $16/1M; Standard $4/1M (secondary-source claim WaveNet cut to $4 in 2026 — verify) https://cloud.google.com/text-to-speech/pricing | YES | Chirp 3 HD most natural |
| **Azure Speech** | vi-VN HoaiMy, NamMinh (neural) | ~$16/1M neural; Neural HD $22/1M (since 03/2026); 0.5M free/mo https://texttolab.com/blog/azure-text-to-speech-pricing | YES | SSML control, stable; only 2 VI voices |
| **FPT.AI** | many VI regional voices | 500k VND/1.5M chars (~$13/1M) … 5M VND/27M chars (~$7/1M); 100k free/mo https://docs.fpt.ai/docs/vi/speech/documentation/tts-pricing/ | yes (paid) | native VI prosody |
| **Viettel AI** | VI regional | 320k VND/1M chars (~$12.5/1M) pay-as-go; 3.2M VND/mo for 10M https://viettel-idc.com.vn/index.php/tin-tuc/tin-cong-nghe/bang-gia-dich-vu-viettel-ai-text-to-speech-speech-to-text-viettel-ai-61.html | yes | good native |
| Vbee AIVoice | 700+ voices, strong VI | 149k-399k VND/mo plans https://vbee.vn/en | YES on paid plans | creator-friendly UI |
| Zalo AI | VI | pricing not public | unclear | low priority |
| **ElevenLabs** | VI in v3 / Flash v2.5 | Creator $22/mo (~100-220k chars), overage ~$0.10/1k chars (~$100/1M) https://www.cekura.ai/blogs/elevenlabs-pricing | YES (paid plans only, not Free) | most expressive; VI accent quality varies, costly |

Rough volume: 60s Short ≈ 700-900 VI chars → 1M chars ≈ 1,100+ Shorts; cost is negligible at any provider except ElevenLabs.

**A/B recommendation**
- Local #1 **VieNeu-TTS v3 Turbo** (Apache, consented presets, tiny VRAM, can run alongside ComfyUI).
- Local #2 **VoxCPM2** (Apache, expressive/voice design) — alt: G-OmniVoice if <100k-user cap acceptable.
- Cloud #1 **Google Chirp 3 HD vi-VN** (quality, free 1M/mo).
- Cloud #2 **FPT.AI** or **Viettel AI** (native VI prosody, cheap); ElevenLabs only if expressiveness worth ~$100/1M.

---

## 3. Wan video (I2V) on 12GB / 16GB RAM

Open-weights status: latest OPEN = **Wan 2.2** (Apache-2.0, Jul 2025) + Wan-Dancer-14B (Jul 2026, music-to-dance). Wan 2.5/2.6/2.7/3.0 = API-only / unverified; many "open Wan 2.7/3.0" pages are SEO fakes. Verify only at https://huggingface.co/Wan-AI / https://github.com/Wan-Video. Sources: https://www.digitalapplied.com/blog/wan-3-0-reality-check-rumor-vs-shipped , https://localaimaster.com/blog/wan-2-7-open-source

### Specs

| | Wan2.2 TI2V-5B | Wan2.2 I2V-A14B (MoE: high+low noise) |
|---|---|---|
| Native res | 720p: 1280×704 / **704×1280** | 480p (832×480) & 720p (1280×720) |
| FPS | **24** | **16** |
| Frames | 4n+1, default 121 (~5s) | 4n+1, default 81 (~5s) |
| 9:16 rec. | 704×1280 (native); faster 544×960 / 480×864 (dims multiple of 32) | **480×832** (12GB sweet spot); 576×1024 if RAM allows; 720×1280 heavy |
| Comfy-Org fp files | `wan2.2_ti2v_5B_fp16.safetensors` 10GB | `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` + `..._low_noise_14B_fp8_scaled.safetensors` 14.3GB each |
| GGUF | QuantStack/Wan2.2-TI2V-5B-GGUF: Q4_K_M 3.43GB, Q5_K_M 3.81GB, Q6_K 4.21GB, Q8_0 5.4GB | QuantStack/Wan2.2-I2V-A14B-GGUF (HighNoise/ + LowNoise/ folders): Q3_K_S 6.5GB, Q4_K_S 8.75GB, **Q4_K_M 9.65GB**, Q5_K_M 10.8GB, Q6_K 12GB, Q8_0 15.4GB (each, ×2) |
| Text encoder | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (~6.7GB) or city96/umt5-xxl-encoder-gguf (Q5_K_M ~4GB, est.) | same |
| VAE | **`wan2.2_vae.safetensors`** (5B only) | **`wan_2.1_vae.safetensors`** |
| License | Apache-2.0 | Apache-2.0 |

Repos: https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged , https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF , https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF , docs https://docs.comfy.org/tutorials/video/wan/wan2_2 . GGUF loader: city96/ComfyUI-GGUF (Apache-2.0).

### Speed LoRAs (all Apache-2.0)

| For | File | Steps/CFG | Source |
|---|---|---|---|
| I2V-A14B | `wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors` (635MB) + `..._low_noise_..._1022.safetensors` (739MB) | 4 steps total (2 high + 2 low), CFG 1 | https://huggingface.co/lightx2v/Wan2.2-Distill-Loras |
| I2V-A14B (older) | `Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/{high,low}_noise_model.safetensors` (1.23GB each) | 4 / CFG 1 | https://huggingface.co/lightx2v/Wan2.2-Lightning |
| TI2V-5B | `Wan22_TI2V_5B_Turbo_lora_rank_64_fp16.safetensors` (332MB) (or Turbo full GGUF hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF) | 4 steps, CFG 1, euler/unipc; good for I2V, weak for T2V | https://huggingface.co/Kijai/WanVideo_comfy (LoRAs/Wan22-Turbo), https://huggingface.co/hum-ma/Wan2.2-TI2V-5B-Turbo-GGUF |

Kijai repo has no explicit license on that file; Turbo GGUF card says Apache-2.0 (origin quanhaol/Wan2.2-TI2V-5B-Turbo).

### RTX 3060 render times (sparse, low-confidence)
- 14B GGUF, no speed LoRA, 840×420, 81f: ~900s (15 min). https://www.nextdiffusion.ai/tutorials/how-to-run-wan22-image-to-video-gguf-models-in-comfyui-low-vram
- 14B Q4 + lightx2v 4-step, 480p 81f: ~95s claimed (wan27.org — SEO-ish site, treat as optimistic). Realistic expect ~3-6 min incl. model swap on 16GB RAM.
- 5B: "5-10s video in a few minutes" on 3060 (https://note.com/secret_r/n/n7ac9c75be880). Est. 704×1280×121f w/ Turbo 4-step ≈ 3-6 min, VAE decode is a big chunk (use tiled decode).

### 16GB RAM verdict
- **5B GGUF Q5/Q6 + umt5 fp8**: workable on 16GB; pagefile 16-24GB recommended.
- **14B A14B**: two experts swapped per run (2×9.6GB Q4_K_M) + TE 6.7GB ⇒ exceeds 16GB → heavy pagefile thrash. Workable only with Q3_K_S/Q4_K_S + GGUF TE + **pagefile ≥32GB on NVMe** (system-managed or fixed 32-48GB); expect slow first loads. 32GB RAM strongly recommended (64GB ideal) before standardizing on 14B.
- Tips: `--cache-none` or small LRU cache on low RAM, tiled VAE decode, generate at 16fps then RIFE ×2.

Recommendation: start pipeline on **TI2V-5B (Q6_K/Q8_0) + Turbo LoRA at 704×1280**; upgrade to **I2V-A14B Q4_K_M + lightx2v 1022 LoRAs at 480×832 → upscale** after RAM upgrade (better motion/identity).

---

## 4. Frame interpolation & upscaling

| Tool | Code license | Weights license | Commercial |
|---|---|---|---|
| ComfyUI-Frame-Interpolation (Fannovel16) https://github.com/Fannovel16/ComfyUI-Frame-Interpolation | MIT | per model | — |
| RIFE 4.x (Practical-RIFE) https://github.com/hzwer/Practical-RIFE | MIT | MIT (same as project); rec. 4.25/4.26 | **YES** |
| FILM (Google) | Apache-2.0 | Apache-2.0 | YES |
| GMFSS / AMT / others | check each | check | verify before use |
| Real-ESRGAN (x4plus, x4plus_anime, animevideov3) https://github.com/xinntao/Real-ESRGAN | BSD-3-Clause | BSD-3 | **YES** |
| SeedVR2 3B/7B (ByteDance) + numz ComfyUI node https://docs.comfy.org/tutorials/utility/seedvr2 | MIT (node) | Apache-2.0 | YES (heavy; 3B GGUF/fp8 for 12GB) |
| **4x-UltraSharp** (Kim2091) https://huggingface.co/Kim2091/UltraSharp/discussions/4 | — | CC-BY-NC-SA-4.0; author: commercial use incl. outputs "probably" not allowed w/o permission | **NO** |
| OpenModelDB models https://openmodeldb.info | — | per-model (many CC-BY-NC) | filter by license |

Pick: RIFE 4.25/4.26 (16→32fps) + Real-ESRGAN x4plus / animevideov3 (or SeedVR2 3B for quality).

---

## 5. License claim check

| Claim | Verdict |
|---|---|
| SDXL base 1.0 = CreativeML OpenRAIL++-M, commercial OK | **Correct** (use-based restrictions apply) |
| IP-Adapter (h94) Apache-2.0 | **Correct** https://huggingface.co/h94/IP-Adapter . Caveat: FaceID variants depend on InsightFace → effectively non-commercial. SDXL `vit-h` variants use ViT-H; base SDXL adapter uses ViT-bigG |
| CLIP-ViT-H-14-laion2B MIT | **Correct** (OpenCLIP LAION weights MIT; LAION dataset caveats) |
| InsightFace pretrained = non-commercial | **Correct**: "pretrained models … non-commercial research only" (buffalo_l, antelopev2); code MIT → affects InstantID, PuLID, FaceID, ReActor https://github.com/deepinsight/insightface/tree/master/python-package |
| Flux.1 dev non-commercial | **Partly**: MODEL is non-commercial (FLUX.1 dev NCL v1.1.1), but §2(d) "You may use Output for any purpose (including for commercial purposes)"; can't train competing models on outputs. Running it inside a commercial production pipeline is grey → avoid; klein 4B is the Apache alt |
| MusicGen weights CC-BY-NC | **Correct** (code MIT, weights CC-BY-NC-4.0) |
| XTTS-v2 CPML non-commercial | **Correct**; Coqui closed (2024) → no commercial license obtainable |
| F5-TTS weights CC-BY-NC | **Correct** (code MIT; weights CC-BY-NC due to Emilia data); VI fine-tunes CC-BY-NC-SA |
| Stable Audio Open community license | **Correct w/ threshold**: Stability Community License — free commercial if org annual revenue < US$1M; above → Enterprise license; outputs owned by user. Stable Audio 3.0 (May 2026) also open-weight under community terms https://stability.ai/news-updates/meet-stable-audio-3-the-model-family-built-for-artistic-experimentation-with-open-weight-models |
| ComfyUI GPL-3.0 | **Correct**; GPL governs code distribution, not generated outputs. Custom nodes have own licenses |
| cubiq/ComfyUI_IPAdapter_plus | **Maintenance-only since 2025-04-14** (author stopped using ComfyUI; only crucial PRs). Works but expect breakage on new ComfyUI; pin versions https://github.com/cubiq/ComfyUI_IPAdapter_plus |

---

## 6. Platform AI-disclosure rules (2026)

- **YouTube**: disclose ("Altered or synthetic content" toggle in Studio) only for *realistic* content (real person saying/doing things, altered real events/places, realistic fake scenes, AI music as main focus). Clearly animated/stylized 3D characters = **not required**; AI narration voice for scripted video not required. Disclosure doesn't affect reach/monetization; YT may auto-label via C2PA/detection. https://support.google.com/youtube/answer/14328491
- **YouTube monetization "inauthentic content"** (renamed from repetitious, 2025): mass-produced/template AI content w/o original value → YPP removal. Biggest risk for an "AI video factory": vary scripts/scenes, add original perspective. https://support.google.com/youtube/answer/1311392
- **TikTok**: must label AI-generated content depicting realistic scenes/people (toggle "AI-generated content"); auto-labels via C2PA Content Credentials; unlabeled realistic AI may be removed/restricted. Safe practice: toggle the AI label on every video (low cost). https://www.hypelive.io/en/blog/tiktok-ai-content-rules-2026 , https://storrito.com/resources/tiktoks-2026-ai-labeling-rules-and-what-they-signal-for-platform-governance/
- Vietnam: no specific AI-label law found in this pass (check Decree on AI / Law on Digital Technology Industry 2025 implementation).

---

## Unresolved questions
1. Exact RTX 3060 timings for 5B Turbo @704×1280×121f and 14B+lightx2v @480×832×81f — must benchmark locally.
2. Kijai `Wan22_TI2V_5B_Turbo_lora` file has no license on its repo page; confirm origin (quanhaol) license = Apache-2.0.
3. Google WaveNet price cut to $4/1M and Chirp 3 HD vi-VN voice list — confirm on official console.
4. ElevenLabs Vietnamese quality in v3 vs Flash v2.5 — needs listening test.
5. G-OmniVoice: Higgs Audio 2 license attribution/"no LLM training on outputs" terms acceptable? Data provenance of VI corpus unknown.
6. Civitai checkpoint provenance (merged LoRAs trained on copyrighted studio frames) — residual IP risk; consider own style LoRA trained on own renders.
7. Qwen-Image-Edit-2511 real VRAM/RAM on 3060 with Q4 + Lightning — benchmark; likely needs 32GB RAM.
8. FLUX.2 klein 4B character-consistency quality vs Qwen-Edit-2511 for 3D-cartoon characters — A/B test.
9. Official Piper vi_VN voice licenses (vais1000, 25hours) not verified.
10. TikTok official help page couldn't be fetched (redirect/JS); summary based on secondary sources.
