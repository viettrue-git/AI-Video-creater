# AI VIDEO FACTORY — TỔNG HỢP DỰ ÁN (v3)

Cập nhật: 05/10/2026 · Thay cho v2 (02/10/2026, file `AIVIDEOFACTORY - TỔNG HỢP DỰ ÁN v2.txt`)
Trạng thái: đang làm Character Consistency — đã có test A01 có số liệu (xem [character-consistency-test-protocol.md](character-consistency-test-protocol.md)).

Ký hiệu: **[CẦN CHỐT]** quyết định của bạn · **[ĐỀ XUẤT]** gợi ý · **[KIỂM TRA]** xác minh lại tại nguồn.

## Thay đổi chính so với v2
- Đã chốt: **9:16** (Shorts/TikTok/Reels), **narrator tiếng Việt**, ổ C còn **~200GB**.
- **TTS narrator chuyển lên TRƯỚC render**: độ dài lời đọc quyết định độ dài shot.
- **Bước 0 — chọn checkpoint** trước khi chạy ma trận IP-Adapter.
- DoD Character Consistency làm rõ (N/A, ngưỡng theo số ảnh).
- Upscale/nội suy bằng model AI (Real-ESRGAN/RIFE), không bằng FFmpeg.
- Đã có git repo + script tự chạy test qua ComfyUI API + log chấm điểm.
- Phát hiện: ComfyUI 0.37 trên 16GB RAM phải chạy với `--disable-pinned-memory`.
- Bảng license chuyển sang [models-license-register.csv](models-license-register.csv), bổ sung theo research 05/10.

## 0. Tóm tắt nhanh
**Đang dừng tại:** Character Consistency — đã qua A01 → A03, đang chạy Bước B.
- A01: weight ≥ 0.7 (`linear`, end_at 1.0) copy nền trắng / bố cục sheet → loại.
- A02: `ease in` + end_at 0.8 cho cảnh rừng đúng, nhân vật toàn thân.
- A03: sửa prompt ba lô → hết lỗi "áo gilê"; **w0.6 đạt 2/3 seed ở S1**.
- Cấu hình ứng viên: IPA PLUS · `ease in` · weight 0.6 · end_at 0.8 (chi tiết trong protocol).

- **B01 (30 ảnh, 5 scene): weight 0.5 đạt 9/15** → nhánh Bước C; mọi scene có ≥1/3 seed đạt (dùng được cho MVP nếu chọn ảnh).

**Việc tiếp theo (thứ tự):**
1. **Bạn duyệt bằng mắt** `experiments/B01-ease-in/sheet-S1..S5.jpg` · Bước C: sửa mũ trùm đầu, màu áo, weight theo shot.
2. Bước 0: thử 1–2 checkpoint 3D (license cho phép bán ảnh) với cấu hình ứng viên — có thể cải thiện style.
3. Song song: Video Spike Wan 2.2 TI2V-5B GGUF.
4. Song song: A/B test TTS tiếng Việt (2 local + 2 cloud).
5. Nếu B01 < 9/15 đạt → Bước C / Character LoRA.

## 1. Mục tiêu & phạm vi
Pipeline: Ý tưởng → Kịch bản → **Narrator TTS → đo thời lượng** → Shot list (có duration) → Ảnh scene (giữ nhân vật) → QC ảnh → Image→Video → QC video → Upscale/nội suy → Nhạc + SFX → FFmpeg → MP4 → (sau này) Python + Agent.

- Ưu tiên local (ComfyUI), cloud cho shot khó / TTS nếu local kém.
- Thương mại → chỉ dùng thành phần có `commercial_use = OK` trong bảng license.
- Loại nội dung: [CẦN CHỐT] (kênh kể chuyện / phim ngắn / quảng cáo).
- Ngân sách cloud tối đa/tháng: [CẦN CHỐT] … USD.

## 2. MVP & mốc
MVP: video **30 giây, 9:16**, 1 nhân vật, 5–8 shot × 3–5s, chỉ narrator tiếng Việt (không thoại, không lip-sync), nhạc nền + vài SFX, làm thủ công, license OK hết.

| Mốc | Hạn | Nội dung |
|---|---|---|
| M1 | 16/10/2026 | Character Consistency đạt DoD (hoặc quyết định LoRA) · Video Spike có số liệu · chọn TTS |
| M2 | 30/10/2026 | Workflow chuẩn (UI + API JSON trong git) · Vertical Slice 15s / 3 shot |
| M3 | 30/11/2026 | MVP 30s · **phụ thuộc nâng RAM — ngày mua dự kiến: [CẦN CHỐT]** |
| M4 | Q1/2027 | 1 lệnh Python chạy lại MVP từ shot list |
| M5 | sau M4 | Agent: ý tưởng → video |

## 3. Spec đầu ra (ĐÃ CHỐT 9:16)
| Hạng mục | Giá trị |
|---|---|
| Ảnh SDXL | 768 × 1344 |
| Video render | Wan 2.2 5B: 704 × 1280, 24 fps, 121 frame · Wan 14B: 480 × 832, 16 fps, 81 frame [KIỂM TRA khi spike] |
| Số frame | dạng 4n+1 (81, 121) |
| Output cuối | 1080 × 1920, 24 fps (14B: RIFE ×3 lên 48 rồi lấy 24) |
| Codec | H.264 yuv420p · AAC 48kHz stereo · MP4 |

Tỷ lệ lệch nhẹ (768×1344 = 0.571, 704×1280 = 0.55, 1080×1920 = 0.5625) → **luôn crop giữa, không kéo giãn**. Bố cục scene chừa lề trên/dưới ~3%.

## 4. Kiến trúc & tài nguyên
- LLM viết kịch bản/shot list: **cloud** (rẻ, tốt hơn) hoặc local Ollama chạy tuần tự (`keep_alive=0`; ComfyUI `/free` — đã có `free_memory()` trong `scripts/comfyui_api_client.py`).
- ComfyUI điều khiển qua HTTP API (`/prompt`, `/history`, `/upload/image`, `/view`).

## 5. Phần cứng
i5-12400F · RTX 3060 12GB · **RAM 16GB** · Windows 11 · ổ C còn ~200GB · pagefile hiện **10GB**.
- Nâng RAM 32GB (tối thiểu) / 64GB (khuyến nghị) **trước** Wan 14B.
- **Tăng pagefile lên 32GB** ngay (System → Advanced → Performance → Virtual memory; cần khởi động lại).
- Khi render: đóng Chrome/Teams/Discord (RAM trống chỉ còn ~4–7GB khi mở hết).

## 6. Môi trường (đã kiểm tra 05/10/2026)
ComfyUI **0.37.0** (commit `4ef23c34`) · Python 3.12.10 venv · PyTorch 2.11.0+cu128 · ComfyUI_IPAdapter_plus `a0f451a` (14/04/2025, chỉ bảo trì — **ghim, không update**).
- Chạy ComfyUI: `scripts\start-comfyui-server-low-ram.bat` (có `--disable-pinned-memory`). **Không** dùng `--disable-dynamic-vram` (crash access violation).
- ComfyUI cảnh báo: PyTorch **cu130** mới bật tối ưu CUDA → cân nhắc nâng sau khi có snapshot [KIỂM TRA tương thích custom node].
- **Chưa có ComfyUI-Manager** → chưa snapshot được. [KIỂM TRA bản Manager tích hợp của 0.37]
- **Chưa có FFmpeg** trên máy → cài trước Vertical Slice (`winget install Gyan.FFmpeg`).

## 7. Đã hoàn thành
ComfyUI + CUDA · SDXL text→image · Character Sheet · IP-Adapter PLUS (preset PLUS) · **ảnh ref sạch** cắt từ sheet (`projects/P001_rung_co/refs/char_main_front.png`, `char_full_body.png`) · **workflow API** `workflows/api/character-scene-ipadapter-v1.json` (node IN_*) · **runner test** + contact sheet + `experiments/log.csv` · test A01.

Lưu ý nhân vật: character sheet có **boots nâu, quần xám nâu có ốp gối, áo hoodie xám bên trong** (khác mô tả v2 "boots đen"). Khối prompt hiện theo ảnh ref. **[CẦN CHỐT]** boots nâu hay đen. Sheet có cả mũ bảo hiểm → negative có `helmet, hat`.
Tên nhân vật / trigger word LoRA: [CẦN CHỐT].

## 8. Character Consistency
Giao thức, DoD, kết quả và kế hoạch test: [character-consistency-test-protocol.md](character-consistency-test-protocol.md).

## 9. Tổ chức workflow
- Node thay đổi theo shot đặt title `IN_*`; output `OUT_Image`. Script tìm node theo title, không theo id.
- Mỗi workflow lưu 2 bản: `workflows/ui/*.json` (mở trong ComfyUI) + `workflows/api/*.json` (Python).
- Đổi cấu hình chuẩn → tăng version (`-v2`) + commit.

## 10. Video Spike (làm ngay, song song)
Phương án nhẹ: **Wan 2.2 TI2V-5B GGUF Q6_K (4.2GB) hoặc Q8 (5.4GB)** + `umt5_xxl_fp8_e4m3fn_scaled` + `wan2.2_vae` + node ComfyUI-GGUF; thử thêm Turbo LoRA 4 step (license **chưa rõ** → chỉ để đo, chưa dùng sản xuất).
Phương án chất lượng (sau nâng RAM): Wan 2.2 I2V-A14B Q4_K_M (2 × 9.65GB) + lightx2v 4-step LoRA (Apache-2.0).
Ghi: model/quant · res/frame · phút/clip · VRAM/RAM đỉnh · OOM/treo · chuyển động 1–5 · biến dạng 1–5.
Ngưỡng: ≤10 phút/clip → local · 10–20 → chấp nhận cho MVP, render đêm · >20 hoặc treo → nâng RAM trước, rồi mới cân nhắc cloud. **Kết quả trên 16GB RAM là trường hợp xấu nhất.**

**Kết quả Video Spike (05/10/2026)** — dùng định dạng gốc (không GGUF, không custom node): `wan2.2_ti2v_5B_fp16` + `umt5_xxl_fp8_e4m3fn_scaled` + `wan2.2_vae`, 704×1280, 24 fps, 20 step, CFG 5, uni_pc. Workflow `workflows/api/wan22-ti2v-5b-image-to-video-v1.json`, chạy bằng `scripts/video_spike_runner.py`, log `experiments/video-spike-log.csv`.

| Clip | Frame (giây) | Thời gian | VRAM / RAM đỉnh | Kết quả |
|---|---|---|---|---|
| V01 | 49 (2.0s) | 6.3 phút (15 s/step) | 10.3 / 10.3 GB | chuyển động 4, nhận diện 4; đi về camera quá nhanh → mất đầu cuối clip |
| V02 | 121 (5.0s) | — | — | **lỗi hết tài nguyên** (lúc đó có 5 tiến trình ComfyUI cũ chạy ngầm) |
| V03 | 81 (3.4s) | **11.7 phút** (29 s/step) | 10.1 / 11.6 GB | chuyển động 4, nhận diện 4; camera lùi theo giữ toàn thân; cuối clip sáng hơn |

**Quyết định:** chạy **local** cho MVP (nhánh 10–20 phút). Mặc định **81 frame (3.4s)** — đủ cho câu narrator dài nhất (4.3s ≈ 97–105 frame khi cần). Ước tính MVP 7 shot × 2–3 lần ≈ 3–4 giờ render (chạy qua đêm).
Bài học: **khởi động lại ComfyUI sạch trước khi làm video**; chỉ 1 server (bat đã chặn chạy trùng); prompt chuyển động phải nói rõ camera (`camera tracks backward … keeping full body in frame`).
Tăng tốc sau: Turbo/distill LoRA 4 step (~4–5× nhanh hơn) — chỉ dùng sau khi xác minh license; hoặc 14B + lightx2v sau nâng RAM.

## 11–12. Image→Video & QC
Như v2: clip 3–5s, ảnh vào phải qua QC ảnh, prompt chuyển động đơn giản. QC video: giữ nhận diện ≥4 đến hết clip, không biến dạng/flicker nặng, đúng chuyển động & độ dài. Tối đa 3 lần render lại/shot, sau đó đơn giản hóa / cloud / thay shot. MVP dùng **cắt cảnh (cut)**, chưa cần nối frame cuối→đầu.

## 13. Audio (MVP)
- **Narrator tiếng Việt** — A/B test (cùng 1 đoạn ~30s): local **VieNeu-TTS v3 Turbo**, **VoxCPM2**; cloud **Google Chirp 3 HD vi-VN**, **FPT.AI hoặc Viettel AI**. Chấm: tự nhiên, phát âm, ngữ điệu, tốc độ. Video 30–60s ≈ 400–800 ký tự → chi phí cloud không đáng kể.
- **Đã cài VieNeu-TTS v3 Turbo local (05/10)**: venv riêng `tools/vieneu-tts-venv` (ONNX, CPU, 774MB, không cần GPU). Script `scripts/vietnamese_narration_tts_generator.py` đọc kịch bản `[SHOT n]` → wav từng shot + `full.wav` + `timing.csv` (độ dài từng shot). ~10 giây cho 7 shot. Đã tạo 5 giọng mẫu tại `projects/P001_rung_co/audio-tts-tests/` — **chờ bạn nghe và chọn**. Lưu ý: VieNeu có watermark âm thanh tùy chọn (Perth), hiện chưa bật.
- **Nhạc/SFX cho MVP: thư viện royalty-free** (YouTube Audio Library, Pixabay…), lưu bằng chứng license từng file. Chưa cần AI tạo nhạc.
- Clone giọng người thật → cần đồng ý bằng văn bản.

## 14. Upscale, nội suy, FFmpeg
- Upscale: **Real-ESRGAN** (BSD-3) hoặc SeedVR2 trong ComfyUI. Tránh 4x-UltraSharp (NC).
- Nội suy: **RIFE** (MIT) qua ComfyUI-Frame-Interpolation.
- FFmpeg chỉ: nối clip, crop/scale cuối, trộn audio (ducking nhạc dưới giọng), `loudnorm`, xuất H.264/AAC. Lưu thành `scripts/assemble-*`.

## 15. Vertical Slice
15s, 3 shot, chất lượng thấp, đi đủ: TTS → shot duration → ảnh → video → upscale/nội suy → nhạc/SFX → FFmpeg. DoD: 1 MP4 đúng spec + danh sách vấn đề.

**✅ Hoàn thành 05/10/2026** → `projects/P001_rung_co/final/P001-vertical-slice-v1.mp4` (11.1s, 1080×1920, H.264 24fps, AAC 48kHz, -14 LUFS).
Quy trình đã chạy thật: kịch bản → TTS Thanh Bình (`timing.csv`) → duration = lời đọc + 0.6s → frame = 4n+1 → ảnh 4 seed/shot (chọn tay) → Wan 5B → `assemble_vertical_video_with_narration.py` (manifest `vertical-slice-manifest.json`).
| Shot | Ảnh chọn | Frame | Render |
|---|---|---|---|
| SH01 toàn cảnh | w0.3 s222222 | 77 | 11.0 phút |
| SH02 đi trong rừng | w0.5 s111111 | 101 | 15.5 phút |
| SH05 nhìn từ sau | w0.5 s111111 | 93 | 14.0 phút |

Vấn đề phát hiện & cách xử lý:
1. **Shot toàn cảnh**: IPA 0.5 kéo nhân vật to ra → dùng weight 0.2–0.3 cho shot wide; SDXL base vẫn khó ra "nhân vật nhỏ xíu".
2. **Áo nâu** ở 2/4 seed SH05 → chọn tay; đây là lý do giữ 4 seed/shot.
3. **Crash khi giải mã VAE** (RAM đỉnh 11.7GB, pagefile 10GB) → tile 384 / temporal 16 + **restart ComfyUI trước mỗi clip** + pagefile 32GB. Sau đó 3/3 clip chạy không lỗi.
4. Gọi `restart-comfyui-server-clean.ps1` qua pipe (`| tail`) làm treo lệnh → ghi ra file.
5. Lời đọc toàn kịch bản chỉ ~15.6s → video MVP ~22–25s, ngắn hơn mục tiêu 30s → thêm câu hoặc thêm nhịp nghỉ/nhạc mở đầu.
6. Chưa có nhạc nền, chưa upscale AI (đang scale lanczos 704→1080) → làm ở MVP.

## 16. Tự động hóa (sau MVP)
Thứ tự: FFmpeg script → Python đọc `shotlist.csv` gọi ComfyUI API (đã có client + runner làm mẫu) → TTS + ghép → QC tự động (VLM, đối chiếu điểm chấm tay) → cuối cùng LLM/Agent.
`shotlist.csv` lưu UTF-8 **có BOM**, prompt đặt trong ngoặc kép.

## 17. Cấu trúc repo (git tại `C:\AIVideoManager`)
```
ComfyUI/            engine (gitignore)
docs/               tài liệu này, protocol, models-license-register.csv
plans/reports/      báo cáo research/review
workflows/ui|api/   workflow JSON
scripts/            API client, runner, contact sheet, start bat
experiments/        scenes JSON, log.csv, <test_id>/ (ảnh gitignore)
projects/P001_rung_co/refs|shots|final
```
Khác v2: không tạo `factory\` riêng — repo đặt ở gốc dự án, `ComfyUI/` bị ignore. Ảnh/video/model không vào git → sao lưu riêng.

## 18. License
Xem [models-license-register.csv](models-license-register.csv). Chi tiết research: `plans/reports/researcher-261005-models-licenses-tts-wan.md`.
Điểm mới: Pony V6 cấm dùng thương mại (cả merge) · Flux.1 dev: model NC (output được phép, nhưng vẫn tránh) · XTTS/viXTTS không mua license được · Stable Audio Open OK dưới $1M doanh thu/năm.

## 19. Rủi ro
| ID | Rủi ro | Mức | Phương án |
|---|---|---|---|
| R1 | IP-Adapter không giữ đủ nhân vật (A01 xác nhận một phần) | Cao | A02 → LoRA |
| R2 | Video quá chậm / không chạy | Cao | Spike sớm, 5B trước, nâng RAM |
| R3 | RAM 16GB treo / lỗi bộ nhớ (đã gặp với SDXL) | Cao | `--disable-pinned-memory`, pagefile 32GB, đóng app, nâng RAM |
| R4 | Vi phạm license | Cao | Chỉ dùng mục OK trong register |
| R5 | Update phá custom node (IPAdapter_plus không còn phát triển) | TB | Ghim commit, snapshot trước update |
| R6 | Nhân vật biến dạng trong video | TB | Clip ngắn, ảnh vào đạt QC |
| R7 | TTS tiếng Việt kém | TB | A/B test sớm, có phương án cloud |
| R9 | Phạm vi phình | TB | Bám MVP |
| R10 | Mất dữ liệu | TB | git + backup media |
| R12 | YouTube "inauthentic content" (video AI hàng loạt bị tắt kiếm tiền) | TB | Nội dung đa dạng, có giá trị riêng |
| R13 | Nhãn AI: TikTok yêu cầu với nội dung giống thật, tự phát hiện C2PA | Thấp | Bật nhãn AI mọi video |
| R14 | Output AI có thể không được bảo hộ bản quyền ở một số nước | Thấp | Lưu ý khi bán cho khách |

## 20. Roadmap
[1–4] ComfyUI, SDXL, Character Design, IP-Adapter ✅ · [5] Character Consistency 🔄 (A01 xong) · [5a] Bước 0 checkpoint ⏭️ · [5b] LoRA nếu cần · [6] Video Spike ⏭️ song song · [6b] A/B TTS ⏭️ song song · [7] Workflow organization ⏳ · [8] Vertical Slice ⏳ · [9] Nâng RAM ⏳ (trước 14B) · [10] Scene 5–8 shot · [11] Image→Video · [11b] Upscale + nội suy · [12] QC · [13] Narrator/nhạc/SFX · [14] FFmpeg · [15] MVP 🎯 M3 · [16] Python 🎯 M4 · [17] Agent 🎯 M5

## 21. Checklist
- [x] Git repo, .gitignore, cấu trúc thư mục
- [x] Bảng license `docs/models-license-register.csv`
- [x] Chốt 9:16 + narrator tiếng Việt
- [x] Ảnh ref sạch + workflow API + runner test
- [x] Test A01 + chấm điểm
- [ ] Tăng pagefile 32GB · cài FFmpeg · bật/cài ComfyUI-Manager + snapshot
- [ ] Chốt boots nâu/đen, tên nhân vật
- [x] Test A02 → A03 → B01 → C01 (chốt: render 3–4 seed/shot rồi chọn)
- [x] Video Spike 5B (81 frame ≈ 11.7 phút/clip → local OK cho MVP)
- [x] Cài VieNeu-TTS local + tạo 5 giọng mẫu
- [x] Chọn giọng **Thanh Bình** · duyệt kịch bản v1
- [x] Cài FFmpeg 9.0.2 · pagefile 16–32GB
- [x] **Vertical Slice** → `final/P001-vertical-slice-v1.mp4`
- [x] Vertical Slice v2: sửa nhấp nháy (VAE temporal seams) + tiếng thừa TTS (auto-QC babble)
- [x] **MVP v2 30s** → `final/P001-mvp-v2-30s.mp4` (29.2s, 8 shot, kịch bản v2 rừng → thảo nguyên, nhạc Pixabay "Inspiring Cinematic", ducking, fade-out, -14.5 LUFS)
- [x] Workflow UI có nhóm + ghi chú tiếng Việt: `workflows/ui/*-ui.json` (sinh bởi `scripts/convert_api_workflow_to_ui_layout.py`)
- [x] Theo dõi tiến độ render: `scripts/show-video-render-progress.bat` (đọc `experiments/render-queue.json`)
- [x] **Bạn** xem MVP v2: nhịp ổn, âm thanh ổn; sửa dáng đi từ sau + cảnh bàn tay (07/10)
- [x] **MVP v3** → `final/P001-mvp-v3-30s.mp4`: SH04 bàn tay đặt phẳng (character override, IPA 0.1), SH05 dáng đi bản B (bạn chọn), SH01/SH02 render lại decode chuẩn, **cả 8 clip upscale Real-ESRGAN x2** (~1 giây/frame GPU, không tăng rung chi tiết)
- [x] **MVP v4 (bản demo hoàn chỉnh)** → `final/P001-mvp-v4-30s.mp4`: + tiếng rừng → gió thảo nguyên (crossfade quanh giây 18.7, cùng bị ducking dưới giọng; lấp khoảng lặng +2.6–5.3dB) + chỉnh màu SH04 (gamma 1.25) / SH08 (saturation 0.82). Assembler hỗ trợ `ambience[]` và `eq` theo shot.
- [ ] **Trước khi đăng công khai**: chụp ảnh license 2 file SFX (đang ghi PROOF MISSING trong register)
- [ ] Tự động hoá 1 lệnh (make_video) · Character LoRA · P002
- [ ] (sau) Bước 0: checkpoint 3D · xác minh license Turbo LoRA

## 22. Nhật ký quyết định
- 30/09 — ComfyUI làm engine, ưu tiên local · IPA preset PLUS.
- 02/10 — Test có đo lường · Video Spike song song · nâng RAM trước video · MVP chỉ narrator · chỉ dùng model license OK · không InsightFace.
- 05/10 — **9:16** · **narrator tiếng Việt** · TTS trước render · repo git ở gốc `C:\AIVideoManager` · `--disable-pinned-memory` · MVP dùng nhạc royalty-free · sampler test chuẩn `dpmpp_2m/karras`, 25 step, CFG 6.5 · A01: weight ≥0.7 loại.
- 05/10 — Hướng A: render 3–4 seed/shot rồi chọn · Wan 2.2 5B định dạng gốc (không GGUF) · TTS local VieNeu, **giọng Thanh Bình** · kịch bản v1 được duyệt · duration shot = lời đọc + 0.6s · restart ComfyUI trước mỗi clip video · pagefile 16–32GB · Vertical Slice hoàn thành.
