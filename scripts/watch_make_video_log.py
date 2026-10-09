"""Print new important lines of a project's make_video log (stage starts, picker, errors) until it finishes.
Used as a live monitor: python scripts/watch_make_video_log.py P002
"""
import re
import sys
import time

from video_project_config import VideoProject

KEY = re.compile(r"^== |Trang chọn ảnh|DỪNG|^Xong\.|FAILED|Traceback|Error")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
project = VideoProject(sys.argv[1])
logs = [project.build / "make_video.log", project.build / "make_video.err.log"]
seen = {str(p): 0 for p in logs}
while True:
    finished = False
    for path in logs:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) < seen[str(path)]:  # log was recreated by a new run: start reading from the top
            seen[str(path)] = 0
        for line in lines[seen[str(path)]:]:
            if KEY.search(line):
                print(("[err] " if path.name.endswith("err.log") else "") + line[:200], flush=True)
            finished = finished or line.startswith("Xong.") or "DỪNG" in line
        seen[str(path)] = len(lines)
    if finished:
        break
    time.sleep(15)
