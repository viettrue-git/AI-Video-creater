# Giai đoạn 2 — Tự động hoá: 1 lệnh cho 1 video

Trạng thái: **CHỜ DUYỆT** · Tạo 07/10/2026 · Nền tảng: MVP P001 v4 (đã làm tay từng bước)

## Mục tiêu
`make_video P002` → đi hết quy trình, chỉ dừng **1 lần** để bạn chọn ảnh, phần còn lại tự chạy (qua đêm được), có thể chạy lại từ chỗ dừng.

```
Bạn viết kịch bản (tiếng Việt)                    ← BẠN
  → [1] Prompt tiếng Anh cho từng shot             ← tôi (trong chat), bạn duyệt
  → [2] Giọng đọc + tự kiểm tra tiếng thừa         ← máy
  → [3] Tính độ dài shot / số frame                ← máy
  → [4] Ảnh 4 seed/shot                            ← máy (~10 phút)
  → [5] CHỌN ẢNH trên trang web cục bộ             ← BẠN (~5 phút)
  → [6] Video từng shot (restart ComfyUI mỗi clip) ← máy (~1.5–2 giờ / 30s)
  → [7] Upscale AI                                  ← máy (~12 phút)
  → [8] Ghép: giọng + nhạc + tiếng môi trường      ← máy
  → MP4 → bạn xem → góp ý → chạy lại đúng shot cần sửa
```

## Các phase
| # | Phase | Nội dung | Trạng thái |
|---|---|---|---|
| 1 | [Cấu trúc project](phase-01-project-structure-and-config.md) | 1 thư mục/video, `project.json` + `script.txt` + `shots.json`; chuyển P001 sang chuẩn mới | ✅ 07/10 (P001 dựng lại từ cấu hình) |
| 2 | [Bộ điều phối](phase-02-orchestrator-stages-and-resume.md) | `make_video.py`: các stage, bỏ qua phần đã xong, lệnh `status` | ✅ 07/10 (tts/plan/assemble đã chạy thật; images/videos chạy ở P002) |
| 3 | [Trang chọn ảnh](phase-03-local-image-picker-web-page.md) | trang web cục bộ: bấm chọn ảnh từng shot → máy chạy tiếp | ✅ 07/10 (smoke test + chặn truy cập file ngoài) |
| 4 | [Thư viện âm thanh](phase-04-shared-sound-library.md) | danh mục SFX/nhạc dùng chung, tự chọn theo cảnh | ✅ 08/10 — **đổi hướng: AI tạo là chính** (Stable Audio 3 Small-SFX + ACE-Step 1.5; stage `audio` trong make_video, `"prompt"` trong project.json, ~40 giây/video, bạn đã duyệt chất lượng). Thư viện tải tay (`audio_library.py`, `"tag"`) giữ làm dự phòng — ~1/3 file tải tay bị sai loại (nhạc thay vì tiếng môi trường). |
| 5 | [Kiểm chứng P002](phase-05-validate-with-second-video-p002.md) | làm video thứ 2 bằng quy trình mới, đo thời gian công sức | 🔄 07/10: `P002-v1.mp4` (28.4s) ra trong 1 lần chạy 16:15→18:27, bạn chỉ duyệt kịch bản + chọn ảnh (~10 phút); chờ bạn xem & góp ý |

Ước lượng: phase 1–3 ~1 buổi làm việc; phase 4 ~nửa buổi (+1 giờ bạn tải âm thanh); phase 5 = 1 lần chạy qua đêm.

## Nguyên tắc
- **Dùng lại code đã chạy ổn** (runner ảnh, video, upscale, TTS, ghép) — không viết lại.
- Mỗi stage ghi kết quả ra file → dừng/chạy lại bất kỳ lúc nào, không mất việc đã xong.
- Sửa 1 shot = chạy lại đúng shot đó (không render lại cả video).
- Không thêm phần mềm/model mới trong giai đoạn này (Stable Audio để sau, cần bạn đồng ý).

## Câu hỏi cần bạn trả lời (trước khi code)
1. **Ai viết prompt tiếng Anh?** Đề xuất: bạn viết mô tả shot bằng tiếng Việt, **tôi chuyển thành prompt trong chat** (không tốn tiền API). Sau này có thể nối API Claude (~vài trăm đồng/video) để tự động hẳn.
2. **Chọn ảnh** bằng trang web cục bộ (đề xuất) hay chọn qua chat với tôi như hiện tại?
3. **Ý tưởng video P002** (để kiểm chứng ở phase 5): cùng nhân vật, bối cảnh khác? Gợi ý: "chàng trai cắm trại bên hồ lúc hoàng hôn" hoặc "leo núi đón bình minh".
4. Giữ **nhân vật hiện tại** cho P002 (đề xuất — chưa có LoRA, đổi nhân vật = làm lại character sheet)?
