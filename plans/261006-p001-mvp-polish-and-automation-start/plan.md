# Kế hoạch 06/10/2026 — Hoàn thiện MVP P001 & bắt đầu tự động hoá

Trạng thái đầu ngày: MVP v2 30s đã có (`projects/P001_rung_co/final/P001-mvp-v2-30s.mp4`).
Bạn đánh giá 05/10: **nhịp ổn, âm thanh ổn**; cần sửa (1) dáng đi từ sau lưng trong rừng chưa tự nhiên, (2) cảnh bàn tay: cử chỉ ngón áp út lạ → chỉ nên đặt bàn tay lên vỏ cây.

## Việc đầu ngày (bạn, ~5 phút)
- [ ] Khởi động lại máy (pagefile 16–32GB có hiệu lực đầy đủ)
- [ ] Đóng app nặng không dùng (Chrome nhiều tab, Teams, Discord) trước khi render

## Khối 1 — Sửa theo góp ý (máy chạy ~70–80 phút)
| Shot | Sửa | Ai |
|---|---|---|
| SH04 bàn tay | Ảnh mới: bàn tay đặt phẳng, ngón khép tự nhiên (6 seed → chọn) · video: tay **đứng yên**, chỉ ánh sáng/bụi chuyển động | Tôi render, **bạn duyệt ảnh** |
| SH05 đi từ sau | Prompt dáng đi tự nhiên + negative chống trượt chân/chân cứng · render **2 seed** → chọn | Tôi, **bạn chọn bản tự nhiên hơn** |
| SH01, SH02 | Render lại với decode đã sửa (bỏ phụ thuộc bộ lọc khử nhấp nháy) | Tôi |
| SH06 (đi về phía ánh sáng, cũng quay sau lưng) | Bạn xác nhận có cần làm lại không | **Bạn** |
→ Ghép **MVP v3** → bạn xem lại.

## Khối 2 — Nâng chất lượng (sau khi v3 ổn)
- [ ] **Upscale AI Real-ESRGAN** (BSD, model ~64MB) 704→1080 — *cần bạn đồng ý tải*
- [ ] **Tiếng môi trường**: bạn chọn trên Pixabay Sound Effects (gợi ý: `forest birds ambience`, `forest wind`, `meadow wind grass`), lưu kèm ảnh chụp license như nhạc
- [ ] Chỉnh màu đồng đều giữa các shot (FFmpeg)
→ **MVP v4** = bản hoàn chỉnh M3.

## Khối 3 — Thiết kế tự động hoá (song song lúc máy render)
Mục tiêu: 1 lệnh cho 1 video, người chỉ viết kịch bản + chọn ảnh.
- [ ] Chuẩn thư mục project + `shotlist` (mỗi shot: cảnh, chuyển động, IPA weight, số frame, seed đã chọn)
- [ ] Trang chọn ảnh (contact sheet bấm chọn) thay cho chọn qua chat
- [ ] Tự sinh `render-queue.json` để công cụ tiến độ chạy cho mọi lô; render qua đêm
- [ ] Bản thiết kế viết vào `plans/` để bạn duyệt trước khi code

## Quyết định cần bạn (không gấp, càng sớm càng tốt)
1. Kênh đăng: YouTube Shorts / TikTok / cả hai (ảnh hưởng chọn nhạc Content ID, nhãn AI)
2. Nội dung: series 1 nhân vật hay mỗi video 1 chủ đề (series → nên train Character LoRA)
3. Nâng RAM 32GB: có/không, khi nào
4. Ý tưởng video thứ 2 (P002) để kiểm chứng quy trình

## Ghi chú
- Cách làm việc: góp ý → tôi chẩn đoán + đề xuất → **bạn đồng ý** → mới sửa.
- Xem tiến độ render: bấm đúp `scripts/show-video-render-progress.bat`.
- Git chưa commit (theo ý bạn).
