# Quy trình 1 tập — kênh "Nghe chuyện cổ đại" (lịch sử & thần thoại, video dài 16:9)

Tập mẫu: `projects/P006_cuu_vi_ho_tu_diem_lanh_thanh_yeu_nu` (Cửu Vĩ Hồ, 14 phút).
Người dùng làm 5 việc (★); còn lại Claude + máy làm. Tổng thời gian máy ≈ 30 phút.

```
★1 Chủ đề ─► 2 Nghiên cứu + dàn ý ─► ★3 Duyệt dàn ý ─► 4 Viết lời kể ─► ★5 Duyệt kịch bản
   ─► 6 Giọng kể (TTS) ─► 7 Tự kiểm (Whisper) ─► ★8 Nghe thử, duyệt giọng
   ─► 9 Nhạc + âm nền + chiêng ─► 10 Gói ảnh Muse ─► ★11 Dán vào Muse, tải zip
   ─► 12 Dựng video + thumbnail + phụ đề + reel ─► ★ Xem & đăng
```

| # | Bước | Ai | Đầu ra | Thời gian |
|---|---|---|---|---|
| 1 | Chọn chủ đề | ★ | 1 câu | — |
| 2 | Nghiên cứu nguồn (sách cổ, sử liệu), chọn **góc kể riêng**, dàn ý 5 chương + mở/kết | Claude | dàn ý trong chat | 5 phút |
| 3 | Duyệt dàn ý, độ dài, giọng điệu | ★ | — | — |
| 4 | Viết lời kể: hook mở đầu, lời mời tương tác (đầu/giữa/cuối), mỏ neo ngữ cảnh (thời gian, nhân vật), tách bạch sử ↔ truyền thuyết, ~3.000 âm tiết | Claude | `script.txt` (khối `[SHOT n — mô tả]`; tiêu đề chương ghi "Chương n: tiêu đề") | 15 phút |
| 5 | Duyệt kịch bản | ★ | — | — |
| 6 | Tạo giọng Thiện Minh từng đoạn, tự lọc tiếng thừa; ghép có nhịp nghỉ (dài quanh tiêu đề chương) | máy | `build/audio/story-narration.wav`, `story-timing.json` | ~8 phút |
| 7 | Whisper nghe lại từng đoạn, so với kịch bản (đọc sai/sót) | máy | `build/audio/asr-check.json` | ~3 phút |
| 8 | Nghe bản thử mp3, báo đoạn cần đọc lại | ★ | `nghe-thu/*.mp3` | 14 phút nghe |
| 9 | Nhạc theo chương (ACE-Step), âm nền (Stable Audio), tiếng chiêng chuyển chương | máy | `build/audio/story-layers.json` | ~5 phút |
| 10 | Bản đồ tranh (`illustrations.json`: tranh ↔ đoạn, thẻ tên) + gói ảnh Muse tiếng Việt (~23 tranh 16:9 + THUMB) | Claude | `muse-image-pack.txt` | 10 phút |
| 11 | Dán gói vào Muse **1 lần**, tải zip, bỏ vào `illustration-inbox/` | ★ | 24 ảnh | ~15 phút |
| 12 | Dựng video (Ken Burns, tiêu đề chương, thẻ tên, trộn âm), thumbnail có chữ, phụ đề .srt, reel nhá hàng 9:16 | máy | `final/` | ~6 phút |

## Lệnh (chạy từ C:\AIVideoManager)
```
python scripts/new_video_project.py --title "<tên tập>" --character narrator-co-dai-thien-minh --series nghe-chuyen-co-dai
tools\vieneu-tts-venv\Scripts\python.exe scripts/vietnamese_narration_tts_generator.py --script projects/<P>/script.txt --voices "Thiện Minh" --out projects/<P>/build/audio
#   đọc lại 1 đoạn: thêm --only-shot N
python scripts/audio_story_narration_joiner.py <P>
tools\asr-venv\Scripts\python.exe scripts/narration_asr_quality_check.py <P>
python scripts/audio_story_sound_layers.py <P>          # cần ComfyUI đang chạy
python scripts/audio_story_video_assembler.py <P>       # --placeholders --preview 20 để thử nhanh
python scripts/audio_story_thumbnail_maker.py <P> "TIÊU ĐỀ" "dòng phụ"
python scripts/audio_story_teaser_reel.py <P>
```
(`python` = `ComfyUI\venv\Scripts\python.exe`)

## Cấu hình trong project.json
- `story_audio.music` / `ambience`: prompt + khoảng đoạn `shots: [từ, đến]`; `chapter_sting`.
- `story_audio.sfx`: hiệu ứng điểm nhấn `{prompt, shot, offset | at (0–1 trong đoạn), seconds}` — 5–6 lần/tập, không bị nhỏ dưới giọng.
- `story_audio.silences`: `{shot, before, after}` — nhạc/âm nền tắt dần trước câu nói lịch sử, để câu đứng một mình.
- Nguyên tắc âm thanh (kênh lịch sử): nhạc nền luôn có, đổi theo chương, không lời; âm bối cảnh chỉ 8–10 cảnh; hiệu ứng tiết chế; 2–3 khoảnh khắc lặng.
- `teaser`: `hook_text`, `segments` (đoạn + tranh + `focus` 0–1 để khung dọc lấy đúng chủ thể), `end_card`.

## Quy tắc nội dung
- Hook trong 30 giây đầu; mời bình luận/góp ý/dị bản ở đầu, giữa, cuối.
- U huyền khi kể, điềm tĩnh khi bình luận; mỗi nhân vật/sách/địa danh có "mỏ neo" 5–15 chữ.
- Ghi rõ nguồn; tách sử thật ↔ tiểu thuyết/truyền thuyết; tránh máu me; tránh hình giống phim/game nổi tiếng;
  tránh lịch sử hiện đại & chính trị nhạy cảm.
- Số thứ tự đoạn có thể đổi khi sửa kịch bản → kiểm lại `illustrations.json`, `story_audio`, `teaser` sau mỗi lần sửa.
