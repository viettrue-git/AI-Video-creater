# Phase 04 — Thư viện âm thanh dùng chung

**Ưu tiên:** trung bình · **Trạng thái:** chờ duyệt

## Ý tưởng
`library/audio/` + `library/audio/catalog.csv`: mỗi file 1 dòng (tag, mood, độ dài, độ to LUFS, nguồn, license, ảnh bằng chứng).
`project.json` chỉ ghi **tag** (`forest`, `meadow-wind`, `rain`, `night`…) → stage assemble tự lấy file, tự tính gain (đo LUFS, như đã làm thủ công hôm nay).

## Việc cần làm
1. Chuyển 2 SFX + 1 nhạc của P001 vào thư viện (mục đầu tiên).
2. Script `catalog` tự đo độ dài + LUFS khi thêm file mới.
3. Danh sách ~30 âm thanh nên có + từ khoá Pixabay → **bạn tải 1 lần** (~1 giờ, có ảnh license).
4. Nhạc: thêm tag mood (`inspiring`, `calm`, `mysterious`…), ưu tiên bài **không** Content ID.

## Để sau (cần bạn đồng ý)
- Stable Audio Open tạo SFX còn thiếu (model vài GB, GPU).

## Tiêu chí xong
- `project.json` P001 dùng tag thay đường dẫn → build ra âm thanh giống v4.
