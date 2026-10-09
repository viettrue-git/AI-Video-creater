"""Local web page to pick one image per shot (or ask for more seeds), writing projects/<id>/picks.json.

Opens http://127.0.0.1:8190 in the browser and blocks until the user presses "Xong".
Exit code 0 = all shots picked, 3 = some shots asked for new images (pipeline renders them and reopens).
  python scripts/image_picker_web_server.py P002
Security: binds 127.0.0.1 only; serves images only from the project's build/images folder.
"""
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from video_project_config import ROOT, VideoProject, parse_shots, read_json, write_json

PORT = 8190
PAGE = Path(__file__).with_name("image-picker-page.html")


def page_data(project):
    script = {f"SH{no:02d}": (desc, text) for no, desc, text in parse_shots(project.dir / "script.txt")}
    picks = project.picks()
    shots = []
    for shot in project.shots:
        candidates = [project.rel(project.image_path(shot, s)) for s in project.seeds_for(shot)
                      if project.image_path(shot, s).exists()]
        desc, text = script.get(shot["id"], ("", ""))
        picked = picks.get(shot["id"], {}).get("image")
        if picked and picked not in candidates and (ROOT / picked).exists():
            candidates.insert(0, picked)  # earlier pick (e.g. from before LoRA mode) stays visible
        shots.append({"id": shot["id"], "description": desc, "narration": text, "candidates": candidates,
                      "picked": picked})
    return {"project": project.id, "title": project.config.get("title", ""),
            "ref": project.character["ref_image"], "shots": shots}


def make_handler(project, state):
    images_dir = project.build.resolve()
    allowed_files = {(ROOT / project.character["ref_image"]).resolve()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                # escape '<' so script text can never close the <script> tag (e.g. "</script>")
                data = json.dumps(page_data(project), ensure_ascii=False).replace("<", "\\u003c")
                html = PAGE.read_text(encoding="utf-8").replace("__DATA__", data)
                return self._send(200, html, "text/html; charset=utf-8")
            if url.path == "/img":
                path = (ROOT / parse_qs(url.query).get("p", [""])[0]).resolve()
                if (images_dir in path.parents or path in allowed_files) and path.suffix == ".png" and path.exists():
                    return self._send(200, path.read_bytes(), "image/png")
            self._send(404, '{"error": "not found"}')

        def do_POST(self):
            # only our own page may change picks (blocks cross-site requests from other open tabs)
            if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PORT}"):
                return self._send(403, '{"error": "forbidden origin"}')
            try:
                length = max(0, min(int(self.headers.get("Content-Length", 0)), 10000))
                body = json.loads(self.rfile.read(length) or b"{}")
                shot = next((s for s in page_data(project)["shots"] if s["id"] == body.get("shot")), None)
                if self.path in ("/pick", "/reroll") and shot is None:
                    raise ValueError("unknown shot")
                if self.path == "/pick" and body.get("image") not in shot["candidates"]:
                    raise ValueError("image is not a candidate of this shot")
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, json.dumps({"error": str(e)}))
            picks = project.picks()
            if self.path == "/pick":
                seed = int(Path(body["image"]).stem.rsplit("_s", 1)[1])
                picks[body["shot"]] = {"image": body["image"], "seed": seed}
                write_json(project.dir / "picks.json", picks)
            elif self.path == "/reroll":
                rerolls = read_json(project.build / "rerolls.json", {})
                rerolls[body["shot"]] = rerolls.get(body["shot"], 0) + 4
                write_json(project.build / "rerolls.json", rerolls)
                picks.pop(body["shot"], None)
                write_json(project.dir / "picks.json", picks)
                state["rerolled"] = True
            elif self.path == "/done":
                self._send(200, '{"ok": true}')
                threading.Thread(target=state["server"].shutdown, daemon=True).start()
                return
            self._send(200, '{"ok": true}')

    return Handler


def run_picker(project_id, open_browser=True):
    project = VideoProject(project_id)
    state = {"rerolled": False}
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(project, state))
    except OSError:
        raise SystemExit(f"Cổng {PORT} đang bận — có thể trang chọn ảnh cũ vẫn mở. Đóng cửa sổ đó rồi chạy lại.")
    state["server"] = server
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Trang chọn ảnh: {url}  (bấm 'Xong' trên trang khi chọn xong)")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()
    server.server_close()
    missing = [s["id"] for s in project.shots if s["id"] not in project.picks()]
    return 3 if state["rerolled"] or missing else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run_picker(sys.argv[1], open_browser="--no-browser" not in sys.argv))
