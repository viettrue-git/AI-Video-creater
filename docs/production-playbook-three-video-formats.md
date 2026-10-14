# Sổ tay sản xuất — các dòng video (chuẩn hóa 14/10/2026)

Tài liệu gốc để **bạn và Claude nói chung một ngôn ngữ** khi sản xuất hàng loạt. Chi tiết kỹ thuật kênh truyện audio:
[audio-story-channel-episode-workflow.md](audio-story-channel-episode-workflow.md).

**Đang sản xuất: dòng B (truyện audio dài) và dòng C (drama trái cây).** Dòng A (hoạt hình Tiểu Mão) **ngừng sản xuất từ 14/10/2026**
(không khả thi); giữ lại bảng bên dưới và P004–P005 làm tư liệu.
Tài liệu cũ [ai-video-factory-project-overview-v3.md](ai-video-factory-project-overview-v3.md) mô tả giai đoạn ComfyUI (P001–P004) — nay chỉ còn là phương án dự phòng.

---

## 1. Ba dòng sản phẩm

| | **A. Hoạt hình Tiểu Mão (NGỪNG)** | **B. Truyện audio dài** | **C. Drama trái cây** |
|---|---|---|---|
| Series (mã) | `khu-rung-hai-dua` | `nghe-chuyen-co-dai` · `hao-khi-su-viet` | `drama-trai-cay` |
| Tập mẫu | P005 | P006, P007, P009 (kỳ bí) · P008 (sử Việt) | P010, P011 |
| Khổ / độ dài | 9:16 · 60–70 s | 16:9 · 11–35 phút (+ reel 9:16 ~60 s) | 9:16 · ~90 s |
| Hình | Clip Muse 10 s | Tranh tĩnh Muse + Ken Burns | Clip Muse 10 s, cắt còn 5–7 s |
| Giọng | **Muse tự nói** (2 nhân vật nhí) | VieNeu người kể (Thiện Minh / Thiền Tâm Đức / giọng trộn Hào Khí) | **Máy lồng tiếng** VieNeu, 1 giọng cố định/nhân vật |
| Phụ đề | Đúng chữ kịch bản, Whisper canh giờ | .srt + chữ in trên hình | Đúng chữ kịch bản, giờ lấy từ lồng tiếng |
| Nhạc | AI nhạc nền, tự hạ dưới thoại | AI nhạc theo chương + âm nền + hiệu ứng | AI nhạc kịch tính + 1–2 hiệu ứng |
| Việc của bạn | duyệt kịch bản · dán Muse · tải zip · xem | duyệt dàn ý · duyệt kịch bản · nghe thử giọng · dán Muse · xem | duyệt kịch bản · dán Muse · tải zip · xem |
| Thời gian máy | ~35 phút | ~30 phút (+ đọc giọng) | ~70 phút (upscale ~4 phút/cảnh) |
| Đặc thù `project.json` | `"video_source": "muse"` | `"video_source": "audio-story"` | `"video_source": "muse"` + thoại dạng `{who, text, at}` |

Mọi tập: `projects/Pxxx_<tên>/`, kết quả trong `final/` (`Pxxx-vN.mp4`, kèm `publish-notes.txt`).

---

## 2. Từ vựng chung (dùng khi nhắn cho nhau)

| Từ | Nghĩa |
|---|---|
| **P010, P011…** | Mã tập (project). Luôn tăng, không dùng lại. |
| **Cảnh SC03 / shot SH03** | Cùng một cảnh: SC = tên clip trong Muse, SH = tên trong máy. |
| **Gói Muse** (`muse-pack.txt`) | File lệnh để dán vào Muse. Khối **"CẢ TẬP"** = dán 1 lần cho cả tập; khối **SCnn** = dán từng cảnh. |
| **Ảnh mẫu** | Ảnh nhân vật chuẩn `characters/refs/muse-*.png`, luôn đính kèm khi dán gói. |
| **Hộp nhận** (`muse-inbox/`) | Thư mục bỏ zip/clip từ Muse. Trình theo dõi tự nhận. |
| **Duyệt** | Bạn chốt kịch bản → máy khóa lại; sửa sau khi duyệt thì Claude báo và duyệt lại. |
| **Lồng tiếng / giọng nhân vật** | Câu thoại do máy đọc, đặt ở giây `at` trong clip. |
| **Điểm cắt** (`trim_start` / `trim_end`) | Bỏ bớt đầu/cuối clip 10 s để nhịp nhanh. |
| **Tắt tiếng clip** (`clip_audio: 0`) | Khi Muse lỡ tự nói trong clip. |
| **Ảnh tĩnh thay cảnh** (Ken Burns) | Cảnh Muse từ chối: lưu `SCnn-1.png`, `SCnn-2.png` vào hộp nhận → máy tự làm clip. |
| **v1, v2…** | Phiên bản video; bản mới không ghi đè bản cũ. |

---

## 3. Quy trình chung (★ = việc của bạn)

```
★ Ý tưởng 1 câu ─► Claude: kịch bản + gói Muse + nhạc + tiêu đề đăng ─► ★ Duyệt
   ─► ★ Dán gói vào Muse (chat MỚI, kèm ảnh mẫu) ─► ★ Tải zip vào muse-inbox + nhắn "đã tải"
   ─► Claude: xem từng clip (thứ tự, Muse tự nói?, điểm cắt, giờ thoại) ─► máy dựng
   ─► Claude: kiểm tra bản cuối (nghe lại toàn bộ, soi khung hình, âm lượng) ─► ★ Xem & đăng
```
Dòng B có thêm 2 bước ★ **trước** kịch bản: duyệt **dàn ý**, và **nghe thử giọng đọc** trước khi làm tranh.

### A. Hoạt hình Tiểu Mão (Muse tự nói) — NGỪNG SẢN XUẤT 14/10/2026
1. Bạn nhắn ý tưởng → Claude viết ~7 cảnh × 10 s, mỗi cảnh ≤ ~30 âm tiết thoại, thân thiện trẻ em.
2. Gói Muse ghi thoại trong ngoặc kép → Muse nói + khớp môi. Hợp khi **1–2 nhân vật, giọng trẻ con**.
3. Máy: nhận clip → nhạc → upscale → phụ đề (Whisper canh giờ) → ghép (+ thẻ "Còn tiếp...").

### B. Truyện audio dài
Theo [audio-story-channel-episode-workflow.md](audio-story-channel-episode-workflow.md): chủ đề → dàn ý ★ → kịch bản ★ →
giọng đọc + Whisper tự kiểm → nghe thử ★ → nhạc/âm nền → gói **ảnh** Muse ★ → dựng + thumbnail + .srt + reel nhá hàng.

### C. Drama trái cây (máy lồng tiếng, nhịp nhanh)
1. Claude viết `muse-scenes.json` (~15 cảnh, mỗi cảnh 1 cảm xúc, 1–2 câu thoại kiểu nói chuyện ≤ ~15 âm tiết, có "trời ơi",
   "hả", "đâu"…; câu xung đột trong 2 giây đầu; kết nhân quả + có hậu) → `scripts/muse_dubbed_episode_pack_builder.py Pxxx`
   tạo gói Muse + `shots.json` + `script.txt` (mỗi cảnh giữ 6 giây đầu). Gói Muse: **không giọng nói**, có **mốc thời gian** ai nói lúc nào.
2. ★ Duyệt → Claude bật trình theo dõi hộp nhận.
3. ★ Dán Muse, bỏ zip vào hộp nhận. Máy **tự dừng ở bước soát**: tạo tờ soát `build/review/sheet-*.jpg` (10 khung/clip),
   kiểm tra tiếng clip → tự tắt tiếng clip Muse lỡ nói; thông báo "chờ soát".
4. Claude soi tờ soát → chỉnh `at` / `trim_start` / `trim_end` trong `shots.json` (chỉnh hậu kỳ **không** cần duyệt lại) → chạy
   `scripts/start-make-video-detached.ps1 Pxxx`: lồng tiếng → nhạc → upscale → phụ đề → ghép.
5. Dàn nhân vật + giọng: `characters/fruit-drama-cast-v1.json`
   (Thanh Long = Trúc Ly · Sầu Riêng = Hải Đăng · Chôm Chôm = Đoan Trang · Anh Dừa = Quốc Tuấn · Bà Mít = Ngọc Linh).

---

## 4. Mẫu câu nhắn (để trao đổi nhanh)

| Bạn muốn | Nhắn |
|---|---|
| Tập mới | "tập mới drama: <ý tưởng>" · "tập mới kỳ bí: <chủ đề>" · "tập mới sử Việt: <chủ đề>" |
| Không có ý tưởng | "đề xuất 3 cốt truyện drama tập 3" |
| Sửa thoại | "P011 cảnh 5: đổi câu Chôm Chôm thành '…'" |
| Sửa nhịp | "P011 cảnh 7 cắt ngắn hơn" · "câu cảnh 1 vào sớm hơn" |
| Đổi giọng | "Bà Mít đổi giọng già hơn" (Claude gửi file nghe thử để chọn) |
| Muse từ chối | "Muse từ chối SC03" (dán lời Muse) → Claude viết lại cảnh hoặc chuyển ảnh tĩnh |
| Muse sai | "SC06 nhân vật bị đổi trang phục" → Claude viết lại khối SC06 để làm lại riêng |
| Chỉ góp ý | "góp ý thôi, chưa sửa" → Claude chẩn đoán + đề xuất, chưa đụng vào |
| Tiến độ | "P011 xong chưa" |

---

## 5. Luật nội dung & kiểm duyệt (đã học được)

**Muse**
- Từ chối hành động thô bạo (ném, đẩy, đóng sầm cửa vào người, khóc co ro, ép buộc, tự hại, rút gươm…). Viết **hành động lạnh lùng
  bằng ánh mắt/cử chỉ**; ý nghĩa nặng để trong lời thoại (máy lồng tiếng, Muse không thấy).
- Đã từ chối 1 lần trong 1 cuộc trò chuyện thì hay từ chối tiếp → **mở chat mới**.
- Mỗi clip Muse chỉ dùng **1 giọng** cho mọi câu và hay đổi giọng giữa các clip → nhiều nhân vật thì **phải lồng tiếng**.
- Dù dặn "không giọng nói", ~1/4 clip vẫn có tiếng lầm bầm → luôn kiểm tra. Whisper "nghe" ra câu "Hãy subscribe…" trên tiếng mưa là ảo giác.
- Tranh lịch sử: mô tả thuần hình ảnh, không tên người thật, không động từ bạo lực; luôn kèm khối dấu hiệu Việt (áo nâu, mái đình, cây đa…).
- Muse hay thêm vật thể không yêu cầu (hổ, chữ) → ghi rõ "KHÔNG có … trong hình".

**Kênh**
- Dòng A cho trẻ em: không lãng mạn, không bạo lực. Dòng C là drama người lớn nhẹ: không máu, không đánh nhau, kết có hậu.
- Dòng B: tách bạch chính sử ↔ giai thoại; không lịch sử hiện đại/chính trị nhạy cảm; Hào Khí Sử Việt chỉ trước 1858.
- Mọi video: bật nhãn **"Nội dung do AI tạo"** khi đăng; không tên thương hiệu; không gây hiểu lầm.

---

## 6. Kiểm tra trước khi giao (Claude tự làm, báo bằng số liệu)
- [ ] Thứ tự cảnh đúng truyện (soi khung hình từng cảnh).
- [ ] Whisper nghe lại bản cuối: đủ câu, đúng người nói, không câu bị cắt.
- [ ] Phụ đề trùng lúc nhân vật lên hình; không chữ lạ trên hình.
- [ ] Âm lượng: trung bình ~-17 dB, đỉnh < -1 dB, nhạc không lấn thoại.
- [ ] Độ dài đúng mục tiêu dòng sản phẩm; `publish-notes.txt` có tiêu đề/mô tả/hashtag/nhãn AI.

---

## 7. Kiểm duyệt quy trình — điểm yếu trước khi làm hàng loạt

| # | Vấn đề | Ảnh hưởng | Đề xuất | Ưu tiên |
|---|---|---|---|---|
| 1 | ~~Gói Muse, kiểm tra Muse lỡ nói làm bằng script tạm~~ | — | **Xong 14/10**: `muse_dubbed_episode_pack_builder.py`, `muse_clip_review_sheet_and_speech_check.py` | ✅ |
| 2 | ~~Trình theo dõi dựng trước khi soát~~ | — | **Xong 14/10**: dòng C dừng ở tờ soát; chỉnh `at`/trim/tắt tiếng không cần duyệt lại | ✅ |
| 3 | **Upscale là nút cổ chai** (~4 phút/cảnh, 1 lần lên 1 giờ 45 phút) | 1 tập drama ≈ 1 giờ máy | Dựng hàng loạt ban đêm (xếp hàng nhiều tập); tìm nguyên nhân lần chậm bất thường | Trung bình |
| 4 | **Điều khoản thương mại của Muse chưa kiểm tra**; bản quyền VieNeu/nhạc AI cần ghi lại | Rủi ro khi bật kiếm tiền | Bạn kiểm tra ToS Muse; Claude cập nhật `models-license-register.csv` | Cao (trước khi bật kiếm tiền) |
| 5 | ~~Kênh trẻ em "made for kids"~~ | — | Không còn áp dụng (dòng A ngừng) | — |
| 6 | ~~Thay đổi chưa commit git~~ | — | **Xong 14/10**: commit + push (media, hộp nhận Muse, zip, .env bị loại khỏi git) | ✅ |
| 7 | Mỗi kênh/tập chưa có lịch đăng & bảng theo dõi | Khó đều tay khi làm hàng loạt | Bảng kế hoạch: tập — trạng thái — ngày đăng — nền tảng | Trung bình |
| 8 | Giọng VieNeu chưa đủ cảm xúc cho vai nam (đã thử Gemini/ElevenLabs: cần trả phí) | Chất lượng drama | Giữ VieNeu + viết thoại kiểu nói chuyện; xem lại khi kênh có doanh thu | Thấp |

---

## 8. Nhịp sản xuất đề xuất (khi vào hàng loạt)
- **Mỗi buổi**: Claude chuẩn bị 2–3 kịch bản (các dòng khác nhau) → bạn duyệt 1 lần → dán Muse lần lượt.
- **Ban đêm**: máy dựng các tập đã có clip (upscale chạy lâu).
- **Sáng hôm sau**: Claude báo cáo kiểm tra từng tập → bạn xem & đăng theo lịch.
