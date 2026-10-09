# Phase 03 — Trang chọn ảnh cục bộ

**Ưu tiên:** cao · **Trạng thái:** chờ duyệt · Phụ thuộc: phase 02 (stage images)

## Trải nghiệm
1. Ảnh render xong → máy tự mở trình duyệt `http://127.0.0.1:8190`.
2. Mỗi shot 1 hàng: ảnh REF nhân vật + 4 ảnh ứng viên + mô tả shot (tiếng Việt) + lời narrator.
3. Bấm chọn 1 ảnh/shot (hoặc "làm lại shot này" → thêm 4 seed mới).
4. Bấm **"Xong — render video"** → lưu `picks.json` → stage video tự chạy tiếp.

## Kỹ thuật
- Python thư viện chuẩn (`http.server`), không cài thêm gì; chỉ nghe trên máy (127.0.0.1).
- Trang HTML tĩnh + chút JavaScript; ảnh đọc từ `build/images/`.
- Chọn qua chat với tôi vẫn dùng được song song (ghi cùng `picks.json`).

## Tiêu chí xong
- Chọn 8 shot P001 trên trang → `picks.json` đúng → stage video bắt đầu.

## Bảo mật
- Chỉ bind 127.0.0.1; không đọc/ghi file ngoài thư mục project.
