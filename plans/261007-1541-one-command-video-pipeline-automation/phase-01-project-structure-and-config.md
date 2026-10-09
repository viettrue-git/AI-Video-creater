# Phase 01 — Cấu trúc project & cấu hình

**Ưu tiên:** cao · **Trạng thái:** chờ duyệt · Liên quan: [plan.md](plan.md), `projects/P001_rung_co/*`

## Vấn đề hiện tại
Cấu hình P001 rải ở nhiều file (`shot-prompts.json`, `mvp-v*-manifest.json`, `render-queue.json`, tham số dòng lệnh trong chat). Video mới phải ghép tay → dễ sai, khó tự động.

## Chuẩn thư mục mới
```
projects/P002_<ten>/
  project.json     # cấu hình chung (giọng, nhạc, ambience, ảnh ref, spec, mặc định IPA)
  script.txt       # kịch bản [SHOT n — mô tả] + lời narrator (format đang dùng)
  shots.json       # prompt ảnh/chuyển động từng shot + IPA weight + character override
  picks.json       # ảnh/seed đã chọn cho từng shot (do trang chọn ảnh ghi)
  build/           # sinh tự động: audio/, images/, clips/, upscaled/, manifest.json (gitignore)
  final/           # MP4 thành phẩm
```
`project.json` (ví dụ):
```json
{"voice": "Thanh Bình", "ref_image": "refs/char_main_front.png", "character": "explorer-v1",
 "music": {"file": "...mp3", "start": 0.5, "volume": 0.35},
 "ambience": [{"tag": "forest", "until_shot": 6}, {"tag": "meadow-wind", "from_shot": 7}],
 "pad_seconds": 0.9, "tail_seconds": 2.0, "seeds_per_shot": 4, "fade_out": 1.5}
```
Mặc định nhân vật (khối mô tả, negative, style) chuyển vào `characters/explorer-v1.json` để P002, P003 dùng lại.

## Việc cần làm
1. Định nghĩa `project.json`, `shots.json` (mở rộng từ `shot-prompts.json`: thêm `ipa_weight`, `seeds`).
2. Tách nhân vật ra `characters/explorer-v1.json` (+ ảnh ref).
3. Chuyển P001 sang chuẩn mới; **kiểm chứng**: build lại v4 chỉ từ cấu hình mới → so khớp file cũ (độ dài, số shot).
4. `.gitignore` thêm `projects/*/build/`.

## Tiêu chí xong
- P001 dựng lại được từ `project.json` + `shots.json` + `picks.json`, không tham số tay.

## Rủi ro
- Đổi cấu trúc làm hỏng đường dẫn cũ → giữ nguyên file P001 cũ, chỉ thêm file mới.
