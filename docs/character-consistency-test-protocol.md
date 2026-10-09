# Character Consistency — Giao thức test & kết quả

Mục tiêu: giữ nhận diện (mặt, tóc, trang phục, ba lô, vóc dáng) **và** đúng scene theo prompt khi đổi nền, pose, góc máy, ánh sáng. Cả hai phải đạt.

## Công cụ
- Workflow: `workflows/api/character-scene-ipadapter-v1.json` (LoadImage → PrepImageForClipVision `pad` → IPAdapterUnifiedLoader PLUS → IPAdapterAdvanced → KSampler).
- Scene + khối prompt nhân vật: `experiments/character-consistency-test-scenes.json`.
- Chạy (ComfyUI phải đang chạy qua `scripts\start-comfyui-server-low-ram.bat`):
  ```
  ComfyUI\venv\Scripts\python.exe scripts\character_consistency_test_runner.py --test-id A02 --scenes S1 --weights 0.4,0.5,0.6 --seeds 111111,222222 --weight-type "ease in" --end-at 0.8
  ```
  Ảnh → `experiments/<test_id>/`, contact sheet → `experiments/<test_id>/contact-sheet.jpg`, mỗi ảnh 1 dòng trong `experiments/log.csv` (cột điểm để trống cho chấm tay). Chạy lại sẽ bỏ qua ảnh đã có.
- ~22–26 giây/ảnh 768×1344, 25 step trên RTX 3060.

## Quy tắc prompt
- Prompt = `scene` + `character_block` + `style_block`. Khối nhân vật **giữ nguyên chữ** ở mọi shot (cũng là caption khi train LoRA).
- Không dùng "the same …" hay negative "different character/clothes" (model không hiểu).
- Negative chống copy sheet: `character sheet, reference sheet, multiple views, turnaround, collage, split screen, grid, helmet, hat, text, watermark…`.
- Mỗi lần chỉ đổi 1 biến; tinh chỉnh tham số phải cố định seed.

## Ảnh reference
- `projects/P001_rung_co/refs/char_main_front.png` — nửa người chính diện (mặc định).
- `projects/P001_rung_co/refs/char_full_body.png` — toàn thân (cho test sau).
Cắt từ nhân vật bên phải của `ComfyUI/input/ComfyUI_00007_.png`, đã xóa mảnh mũ/giày thừa. **Không đưa cả character sheet vào IPA** (ảnh 00008/00009 cũ ra lại bố cục sheet).

## Các bước
| Bước | Nội dung | Số ảnh |
|---|---|---|
| 0 | So 1–3 checkpoint, **weight 0** (không IPA), S1+S2, 2 seed → chọn style | 4/checkpoint |
| A | 1 scene, nhiều weight, 2 seed → chọn 2 weight tốt nhất | 8–10 |
| B | 2 weight × 3 seed (111111, 222222, 333333) × 5 scene | 30 |
| C | Với weight tốt nhất: weight_type, end_at, thêm ref thứ 2 | tùy |

Cấu hình cố định: 768×1344, `dpmpp_2m/karras`, 25 step, CFG 6.5.

Scene: S1 toàn thân đi trong rừng cổ, nắng xuyên tán · S2 cận mặt hoàng hôn · S3 ngồi bàn gỗ trong cabin, đèn ấm · S4 chạy phố đêm mưa, góc thấp · S5 nhìn từ sau 3/4 trên vách núi (ba lô).

## Chấm điểm (1–5)
Face · Hair · Clothes · Backpack · Body · Prompt adherence · Artifacts (5 = không lỗi).
- Tiêu chí không thấy được trong ảnh (Body/Backpack ở S2, Face ở S5) → ghi **N/A**.
- Identity = trung bình các ô có điểm trong 5 tiêu chí đầu.
- Chấm theo cả lô trong 1 buổi, mở contact sheet có REF bên cạnh.

## DoD
Với **weight tốt nhất** ở Bước B (15 ảnh): **≥ 12/15 ảnh đạt** (Identity ≥ 4 **và** Adherence ≥ 4) **và mỗi scene ≥ 2/3 ảnh đạt**.
- Đạt → chốt cấu hình, lưu `workflows/{ui,api}/character-scene-v1`, commit.
- 9–11/15 → Bước C.
- < 9/15 hoặc C không cải thiện → Character LoRA.

## Phương án LoRA
1. 20–30 ảnh tốt nhất (đa dạng góc/pose/ánh sáng/khoảng cách), **sửa lỗi bằng inpaint trước** để không "nướng" lỗi vào LoRA.
2. Caption = khối nhân vật + trigger word riêng.
3. Train SDXL LoRA bằng kohya_ss / OneTrainer trên 12GB (gradient checkpointing, cache latents); rank 16–32, ~1500–3000 step [KIỂM TRA].
4. Dùng LoRA 0.7–0.9 + IPA 0.3–0.5; test lại theo giao thức này.
Phương án khác (sau nâng RAM): model edit ảnh theo reference, license Apache-2.0 (Qwen-Image-Edit-2511, FLUX.2 klein 4B) [KIỂM TRA].
Tránh: FaceID / InstantID / PuLID / ReActor (InsightFace non-commercial).

## Kết quả

### A01 — 05/10/2026 · SDXL base · ref char_main_front · linear · end_at 1.0 · S1
| Weight | Identity (s111111 / s222222) | Adherence | Nhận xét |
|---|---|---|---|
| 0.00 | 3.5 / 2.75 | 5 / 5 | đúng cảnh, nhưng nhìn từ sau / quá nhỏ → không giữ nhân vật |
| 0.50 | 3.6 / 3.6 | 3 / 2 | mặt + tóc giống; quai ba lô thành áo gilê nâu; nền nhợt; s222222 không toàn thân |
| 0.70 | 3.8 / 3.8 | 2 / 1 | nền studio trắng; s222222 ra 2 nhân vật + chữ |
| 0.85 | 3.8 / 3.8 | 1 / 1 | copy ref / bố cục poster |
| 1.00 | 3.8 / 3.8 | 1 / 1 | copy ref |

Kết luận A01:
- **Loại weight ≥ 0.7** với `linear` + end_at 1.0: nền trắng của ref bị kéo vào ảnh.
- Vùng khả thi **0.4–0.6**, nhưng 0 ảnh nào đạt DoD (Identity tối đa 3.8, chưa có ảnh vừa ≥4 vừa adherence ≥4).
- Ba lô là điểm yếu nhất ở mọi weight (ref chính diện chỉ thấy quai).
- SDXL base cho style 3D nhạt → **Bước 0 (đổi checkpoint) có thể cải thiện cả hai trục**.

### A02 — 05/10/2026 · weight 0.4/0.5/0.6 × weight_type × end_at 0.8 · S1 · 2 seed (18 ảnh)
| weight_type | Kết quả |
|---|---|
| `linear` | end_at 0.8 đã giúp ra toàn thân trong rừng (s111111), nhưng nền nhợt; s222222 ở 0.5–0.6 vẫn cận trung + nền trắng |
| **`ease in`** | **tốt nhất**: rừng thật, có nắng, đi toàn thân ở cả 2 seed. w0.6 s222222 **đạt DoD** (Identity 4.0, Adherence 5) |
| `weak input` | gần `ease in` nhưng nền nhợt hơn |

Lỗi lặp lại: quai ba lô to trên ngực bị hiểu thành **áo gilê nâu** (Clothes/Backpack = 3). Nguyên nhân một phần từ prompt ("backpack straps").

### A03 — 05/10/2026 · sửa prompt · ease in · end_at 0.8 · w0.6/0.7 · 3 seed
Prompt: `brown leather backpack straps` → `brown leather backpack`; negative thêm `vest, gilet`.
- **Hết áo gilê** ở 6/6 ảnh; quai + ba lô nâu đúng → Clothes/Backpack lên 4.
- w0.6: **2/3 đạt** (s111111, s222222); s333333 ra trung cảnh (Adherence 3).
- w0.7: 1/3 đạt — weight cao kéo khung hình về cận/trung cảnh như ref.

**Cấu hình ứng viên:** SDXL base · ref `char_main_front.png` · IPA PLUS · `ease in` · **weight 0.6** · end_at 0.8 · `dpmpp_2m/karras` 25 step CFG 6.5 · 768×1344.

### B01 — 05/10/2026 · ease in · end_at 0.8 · w0.5/0.6 × 3 seed × 5 scene (30 ảnh)
Contact sheet theo scene: `experiments/B01-ease-in/sheet-S1.jpg` … `sheet-S5.jpg`.

| Scene | w0.5 đạt | w0.6 đạt | Ghi chú |
|---|---|---|---|
| S1 rừng | 2/3 | 2/3 | s333333 ra trung cảnh |
| S2 cận mặt hoàng hôn | 1/3 | 1/3 | áo lệch olive/kaki dưới nắng ấm; s333333 **đội mũ trùm đầu** |
| S3 cabin, bàn gỗ | 2/3 | 2/3 | s333333 đội mũ, không có bàn |
| S4 phố đêm mưa | 2/3 | 2/3 | quần kaki thay vì xám ở 1 ảnh |
| S5 nhìn từ sau, vách núi | **2/3** | **0/3** | w0.6 kéo nhân vật quay mặt ra trước như ref |
| **Tổng** | **9/15** | 7/15 | |

**Kết luận B01:** weight tốt nhất **0.5** → 9/15, nhưng S2 chỉ 1/3 → theo DoD rơi vào nhánh **Bước C** (9–11/15). Chưa cần LoRA.
- Mọi scene đều có **≥ 1/3 seed đạt** → về mặt sản xuất, render 3–4 seed/shot rồi chọn là dùng được ngay cho MVP.
- Lỗi lặp lại & cách sửa cho Bước C:
  1. **Mũ trùm đầu** (seed 333333, 3 scene): prompt `hood down`, negative `hood up, hooded head`.
  2. **Màu áo lệch** dưới ánh sáng ấm: nhấn `dark green jacket` hoặc tăng nhẹ weight riêng cho cận cảnh.
  3. **Shot nhìn từ sau** kém khi weight cao (ref chính diện): dùng **weight theo shot** (0.4–0.5 cho shot lưng) hoặc thêm ref thứ 2 nhìn từ sau.
- Weight nên là **thuộc tính của từng shot** trong shotlist, không phải 1 giá trị chung.

### C01 — 05/10/2026 · chỉ đổi prompt · ease in · w0.5 · end_at 0.8 · 5 scene × 3 seed
Prompt: `hooded adventure jacket` → `adventure jacket with the hood down, grey hoodie underneath`; negative thêm `hood up, hooded head, olive jacket, khaki pants`.
Grid: `experiments/C01-hood-color-fix/grid-scenes-by-seed.jpg`.

| Scene | B01 w0.5 | C01 | Thay đổi |
|---|---|---|---|
| S1 | 2/3 | 2/3 | = |
| S2 | 1/3 | 0/3 | mất khung cận mặt; s333333 **vẫn** đội mũ |
| S3 | 2/3 | 1/3 | 1 ảnh ra ngoài trời |
| S4 | 2/3 | **3/3** | áo xanh đúng, hết quần kaki |
| S5 | 2/3 | 2/3 | = |
| **Tổng** | 9/15 | 8/15 | |

**Kết luận:** màu áo cải thiện, nhưng tổng không tăng — SDXL base + IPA đã **chạm trần ~55–60% ảnh đạt**; sửa prompt chỉ dao động ±1. Lỗi mũ trùm đầu gắn với seed 333333, không phải prompt.
**Quyết định (hướng A, 05/10):** dừng tinh chỉnh; sản xuất MVP theo **render 3–4 seed/shot → chọn ảnh đạt**. Giữ prompt C01 (màu áo tốt hơn). Cải thiện thật sự để sau: Bước 0 (checkpoint 3D) hoặc Character LoRA.
Lưu ý cận mặt (S2): cần prompt khung hình mạnh hơn (`extreme close-up, face fills the frame`) khi làm shot list.
