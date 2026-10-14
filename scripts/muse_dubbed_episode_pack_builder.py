"""Build a dubbed Muse episode (drama line) from one scene list: muse-pack.txt + shots.json + script.txt.

  python scripts/muse_dubbed_episode_pack_builder.py P012            # needs projects/P012_*/muse-scenes.json
  python scripts/muse_dubbed_episode_pack_builder.py P012 --force    # rebuild after approval (drops clip tuning)
muse-scenes.json:
  {"intro": "tập 3 phim ngắn hoạt hình 3D của tôi",
   "cast_block": ["- THANH LONG: ...", "- ANH DỪA: ..."],          # this episode's looks/outfits (Vietnamese)
   "new_refs": [{"name": "Bà Mít", "file": "muse-fruit-ba-mit.png", "prompt": "..."}],   # optional
   "scenes": [{"title": "...", "action": "...", "lines": [{"who": "BA MIT", "emotion": "...", "text": "..."}]}]}
Muse renders picture + sound only (no voices); each scene's action and 1–2 speakers fit in the first 6 s
(fast pacing), then shots.json gets "at" per line and trim_end 4.0. Speaker names/voices: character "cast".
"""
import argparse
import json
import sys

from video_project_config import ROOT, VideoProject, read_json

KEEP = 6  # seconds of each 10 s Muse clip kept on screen
SLOTS = {1: [(0, KEEP, 0.4)], 2: [(0, 3, 0.3), (3, KEEP, 3.2)]}  # (from, to, dub 'at') by number of lines
RULES = f"""- Video dọc 9:16, 10 giây, phong cách hoạt hình 3D kiểu Pixar, ánh sáng điện ảnh, biểu cảm khuôn mặt rõ ràng, nhịp NHANH: hành động chính xảy ra ngay từ giây 0, không mở đầu chậm.
- KHÔNG CÓ GIỌNG NÓI NÀO: không thoại, không người dẫn chuyện, không tiếng hát (tôi sẽ tự lồng tiếng sau). Khi mốc thời gian ghi "đang nói", nhân vật đó mấp máy môi như đang nói nhưng KHÔNG phát ra tiếng.
- Làm đúng MỐC THỜI GIAN: toàn bộ hành động chính và lời nói nằm trong {KEEP} giây đầu; trong mỗi khoảng máy quay hướng rõ vào nhân vật đang nói (cận hoặc trung cảnh). Giây {KEEP}–10: giữ nguyên khung cảnh, chuyển động nhẹ.
- Chỉ có tiếng động và âm thanh môi trường tự nhiên, KHÔNG nhạc nền. Không chữ, không phụ đề, không chữ trên màn hình điện thoại/máy tính."""


def timeline(lines, names):
    rows = "".join(f"- {a}–{b} giây: {names[l['who']]} đang nói ({l['emotion']}), máy quay hướng vào {names[l['who']]}.\n"
                   for (a, b, _), l in zip(SLOTS[len(lines)], lines))
    if not lines:
        rows = f"- 0–{KEEP} giây: không ai nói, chỉ hành động và tiếng động.\n"
    return f"MỐC THỜI GIAN:\n{rows}- {KEEP}–10 giây: giữ khung cảnh, chuyển động nhẹ, không ai nói.\n"


def scene_text(i, scene, names):
    return f"SC{i:02d} — {scene['title']}\n{scene['action']}\n{timeline(scene.get('lines', []), names)}"


def block(title, body):
    return f"\n\n========================= {title} =========================\n>>>>> COPY TỪ ĐÂY\n{body}<<<<< ĐẾN ĐÂY\n"


def build_pack(p, spec, names):
    scenes, n = spec["scenes"], len(spec["scenes"])
    cast = "NHÂN VẬT (người mang đầu trái cây, thân người bình thường, khuôn mặt/đầu giữ ĐÚNG như ảnh mẫu đính kèm; trang phục theo mô tả dưới đây trong cả tập):\n" + "\n".join(spec["cast_block"])
    refs = spec.get("new_refs", [])
    head = (f"HƯỚNG DẪN (đừng copy phần này)\nMuse CHỈ làm hình + tiếng động; máy tự lồng tiếng và chèn phụ đề. Mỗi cảnh chỉ giữ ~{KEEP} giây đầu.\n"
            + "".join(f"BƯỚC 0: tạo ảnh mẫu {r['name']} (khối bên dưới), lưu characters/refs/{r['file']}.\n" for r in refs)
            + f"Mở 1 cuộc trò chuyện Muse MỚI, đính kèm ảnh mẫu (characters/refs/muse-fruit-*.png), dán khối \"CẢ TẬP\" → tải zip\n"
            f"→ bỏ nguyên file zip vào {p.rel(p.dir)}/muse-inbox/. Máy nhận clip, làm tờ soát, rồi chờ Claude soát trước khi dựng.\n"
            "Muse chỉ làm 1 cảnh mỗi lần → dùng CÁCH TỪNG CẢNH. Cảnh Muse từ chối → mở chat mới thử lại; vẫn từ chối → xin 2 ảnh tĩnh, lưu SCnn-1.png, SCnn-2.png vào muse-inbox.\n")
    parts = [head]
    for r in refs:
        parts.append(block(f"BƯỚC 0 — ẢNH MẪU {r['name'].upper()}",
                           "Tạo 1 ảnh mẫu nhân vật, dọc 9:16, hoạt hình 3D kiểu Pixar, toàn thân, nhìn thẳng, đứng, nền xám nhạt trơn, "
                           f"ánh sáng dịu, không chữ, cùng phong cách với các ảnh mẫu đính kèm:\n{r['prompt']}\n"))
    all_scenes = "\n".join(scene_text(i, s, names) for i, s in enumerate(scenes, 1))
    parts.append(block("CẢ TẬP (1 lần dán)",
                       f"Bạn hãy làm {spec['intro']}. Tạo ĐỦ {n} cảnh dưới đây, mỗi cảnh là MỘT video riêng, làm lần lượt từng cảnh, "
                       "không cần chờ tôi xác nhận. Làm xong, gom tất cả vào MỘT file .zip và gửi link tải. Đặt tên file đúng mã cảnh: "
                       f"SC01.mp4, SC02.mp4, ... SC{n:02d}.mp4.\n\nQUY TẮC CHO MỌI CẢNH:\n{RULES}\n\n{cast}\n\n{all_scenes}"))
    parts.append("\n\nCÁCH TỪNG CẢNH (dự phòng): mỗi khối là 1 lần dán, chỉ copy phần giữa hai dấu mốc.\n")
    for i, s in enumerate(scenes, 1):
        parts.append(block(f"SC{i:02d} — {s['title']}",
                           f"Tạo một video duy nhất, đặt tên SC{i:02d}.mp4.\n{RULES}\n\n{cast}\n\n{scene_text(i, s, names)}"))
    return "".join(parts)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--force", action="store_true", help="rebuild an approved project (loses at/trim/clip_audio tuning)")
    args = ap.parse_args()
    p = VideoProject(args.project)
    if p.config.get("script_approved") and not args.force:
        raise SystemExit("Project đã duyệt: build lại sẽ xóa chỉnh sửa hậu kỳ trong shots.json — dùng --force nếu chắc chắn")
    spec = read_json(p.dir / "muse-scenes.json")
    cast = p.character.get("cast", {})
    names = {k: v.get("name", k) for k, v in cast.items()}
    for i, s in enumerate(spec["scenes"], 1):  # fail early on typos in speaker keys / too many lines
        lines = s.get("lines", [])
        if len(lines) > 2 or any(l["who"] not in cast for l in lines):
            raise SystemExit(f"SC{i:02d}: tối đa 2 câu và 'who' phải là một trong {list(cast)}")
    (p.dir / "muse-pack.txt").write_text(build_pack(p, spec, names), encoding="utf-8")
    shots = [{"id": f"SH{i:02d}", "scene": s["title"], "trim_end": 10.0 - KEEP,
              "dialogue": [{"who": l["who"], "text": l["text"], "at": at} for l, (_, _, at) in zip(s.get("lines", []), SLOTS.get(len(s.get("lines", [])), []))]}
             for i, s in enumerate(spec["scenes"], 1)]
    note = ("Built by muse_dubbed_episode_pack_builder.py from muse-scenes.json. SCnn = SHnn. Dialogue {who, text, at} is "
            "dubbed with the cast's VieNeu voices; after clip review adjust at / trim_start / trim_end / clip_audio here.")
    (p.dir / "shots.json").write_text(json.dumps({"_note": note, "shots": shots}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    script = "".join(f"[SHOT {i} — {s['title']}]\n" + " / ".join(f"{names[l['who']]}: {l['text']}" for l in s.get("lines", [])) + "\n\n"
                     for i, s in enumerate(spec["scenes"], 1))
    (p.dir / "script.txt").write_text(script + "---\n", encoding="utf-8")
    print(f"{p.id}: {len(shots)} cảnh -> muse-pack.txt, shots.json, script.txt")


if __name__ == "__main__":
    main()
