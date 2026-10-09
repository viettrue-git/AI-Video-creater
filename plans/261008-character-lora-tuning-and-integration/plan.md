# Kế hoạch 08/10/2026 — Tinh chỉnh Character LoRA "Tâm" & đưa vào pipeline

**KẾT QUẢ (08/10, ✅ xong):** Test L04 → chọn phối **A: LoRA 0.8, tắt IP-Adapter** (~8/12 cảnh khó so với ~1–2/12 phối cũ; ngồi & nhìn từ sau 3/3; cận mặt vẫn yếu 1/3).
Đã đưa vào pipeline: `characters/explorer-v1.json` có `lora`; project bật bằng `"use_lora": true` (ảnh vào `build/images-lora/`, chỉ render shot chưa chọn).
Kiểm chứng: P002 `--redo SH03 images` → `final/P002-v2.mp4` (~15 phút máy, 7 shot khác giữ nguyên). Lều vẫn không xuất hiện — bạn chọn giữ nguyên.
Chưa làm: LoRA v2 cho cận mặt (để sau nếu cần).

Trạng thái đầu ngày: LoRA `tam-explorer-v1` đã train (epoch 3/4/6/8 trong `ComfyUI/models/loras/`).
Kết quả 07/10: **nhân vật giữ gần như tuyệt đối**, nhưng LoRA 0.8 + IP-Adapter 0.5 làm **mất bố cục cảnh**
(cận mặt / ngồi / nhìn từ sau thất bại; ~6/15 so với 9/15 không LoRA) + lem màu theo prompt (hoodie tím).
Ảnh: `experiments/L02-seen-lora-grid.jpg`, `experiments/L03-unseen-compare-grid.jpg`.

## Bước 1 — Test phối LoRA × IP-Adapter (~15 phút máy)
4 cảnh khó: S2 cận mặt hoàng hôn, S3 ngồi bên bàn, S5 nhìn từ sau, N2 cận mặt ga tàu · 3 seed · epoch 6.
| Phối | LoRA | IP-Adapter |
|---|---|---|
| A | 0.8 | tắt (weight 0) |
| B | 0.7 | 0.2 |
| C | 0.6 | tắt |
Chấm Identity + Adherence → chọn phối tốt nhất. So thêm epoch 3 nếu cần.

## Bước 2 — Quyết định
- Phối mới đạt ≥ 12/15 (cả hai tiêu chí) → chốt, sang bước 3.
- Chưa đạt → **LoRA v2**: dataset cân bằng tư thế (thêm ảnh ngồi / cận mặt / từ sau / nghiêng), caption ghi rõ tư thế; train lại ~75 phút.

## Bước 3 — Đưa LoRA vào pipeline
- `characters/explorer-v1.json` thêm `lora` (file + strength) và `ipa` mới; trigger `tamxplr man` vào khối nhân vật.
- `make_video.py` stage images dùng `--lora` khi nhân vật có LoRA.
- Kiểm chứng: `make_video P002 --redo SH03 images` (shot dựng lều) với LoRA.

## Ghi chú
- Cách làm việc: tôi đề xuất → **bạn đồng ý** → mới chạy.
- Lem màu theo prompt (ví dụ "purple sky") → tránh từ màu sát nhân vật hoặc thêm màu áo vào prompt.
