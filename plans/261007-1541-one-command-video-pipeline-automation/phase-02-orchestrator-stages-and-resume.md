# Phase 02 — Bộ điều phối `make_video.py`

**Ưu tiên:** cao · **Trạng thái:** chờ duyệt · Phụ thuộc: phase 01

## Lệnh
```
make_video.py P002              # chạy tiếp từ stage còn dở tới khi cần người (chọn ảnh) hoặc xong
make_video.py P002 status       # bảng: stage nào xong, shot nào thiếu, ước tính thời gian còn lại
make_video.py P002 --redo SH04  # làm lại 1 shot (ảnh hoặc video) rồi ghép lại
make_video.py P002 --only assemble
```
Kèm file bấm đúp `make-video.bat` cho người không quen dòng lệnh.

## Stage (mỗi stage = 1 hàm, dùng lại script có sẵn)
| Stage | Dùng lại | Đầu ra (trong `build/`) | Bỏ qua khi |
|---|---|---|---|
| tts | `vietnamese_narration_tts_generator.py` (+ auto-QC) | `audio/shot_NN.wav`, `timing.csv` | wav đã có & script không đổi |
| plan | mới (nhỏ) | `plan.json`: duration, frames 4n+1 | — luôn tính lại (nhanh) |
| images | `character_consistency_test_runner.py` | `images/SHxx_s<seed>.png` | ảnh đã có |
| pick | phase 03 | `picks.json` | đã chọn đủ |
| videos | `render_video_queue.py` (tự sinh queue) | `clips/SHxx.mp4` | clip đã có & input không đổi |
| upscale | `upscale_video_clips_batch.py` | `upscaled/SHxx.mp4` | đã có |
| assemble | `assemble_vertical_video_with_narration.py` | `final/<P>-vN.mp4` | — luôn chạy (6 giây) |

- **Phát hiện thay đổi:** lưu "dấu vân tay" (hash) của prompt/seed/ảnh cho mỗi clip → đổi prompt shot nào thì chỉ shot đó render lại.
- Restart ComfyUI trước stage images và trước mỗi clip video (đã kiểm chứng ổn định).
- Ghi log từng stage vào `build/log.txt`; công cụ tiến độ đọc queue tự sinh.

## Tiêu chí xong
- P001: xoá `build/clips/SH04.mp4` → `make_video.py P001` chỉ render lại SH04 rồi ghép ra v4 giống hệt.
- Dừng giữa chừng (tắt cửa sổ) → chạy lại tiếp tục đúng chỗ.

## Rủi ro
- Lỗi RAM giữa đêm → mỗi clip đã có cơ chế bỏ qua clip xong; thêm thử lại 1 lần khi lỗi CUDA/RAM.
