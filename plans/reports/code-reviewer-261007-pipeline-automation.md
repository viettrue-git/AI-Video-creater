# Code Review: one-command video pipeline (make_video.py + picker)

Date: 2026-10-07 · Scope: scripts/make_video.py, video_project_config.py, image_picker_web_server.py,
image-picker-page.html, modified runners (character_consistency_test_runner, video_spike_runner,
render_video_queue, vietnamese_narration_tts_generator). Read-only review, nothing executed.

## Summary
Structure is clean and the happy path is right (paths are all ROOT-relative with cwd=ROOT, the correct
venv runs each child, `.2f` weight formatting matches between image_path and the runner, 4n+1 math is
correct, /img traversal is blocked). The main gaps are **failure propagation** (every stage carries on after
a child fails, and the process exits 0), **one resume rule that can destroy upscaled clips**, a **reroll
dead end after 8 seeds**, and **missing narration only showing up at assemble time**, after hours of rendering.

## Findings

### High
1. **make_video.py:25-28, 158; render_video_queue.py:47; upscale_video_clips_batch.py:34; character runner:121-125; video_spike_runner.py:138** - `run()` returns the child's exit code but no caller checks it. Most children also exit 0 when a job fails (they print FAILED or "N failed"). So if TTS fails, `plan` crashes with a FileNotFoundError traceback. If ComfyUI is down, the picker opens with no images. If a render fails, `upscale` and `assemble` still run, and `make_video` itself exits 0.
   Fix: have children `sys.exit(1)` when failures > 0. In `run()`, raise `SystemExit(f"stage failed ({rc})")` when rc != 0. Return a non-zero exit code from `main()`.

2. **make_video.py:88-91** - Resume treats a missing `build/clips/SHxx.mp4` as stale even when the fingerprint matches and the upscaled clip exists. Deleting the raw clips to save disk space (or losing them) makes the next run delete the good `upscaled/SHxx.mp4` and re-render the clip (hours of work).
   Fix: `done = state fp == fp and (clip.exists() or upscaled.exists())`. Unlink files only when the fingerprint differs.

### Medium
3. **video_project_config.py:96-98** - `DEFAULT_SEEDS[: n + extra]` caps out at 8 seeds. After the first reroll (4+4), every later "tạo thêm 4 ảnh" adds no new seed. `stage_images` prints "ảnh đã đủ" and the picker reopens with the same images: a silent loop with no way forward.
   Fix: derive seeds beyond the list, e.g. `[DEFAULT_SEEDS[i] if i < len(DEFAULT_SEEDS) else 111111 * (i + 1) for i in range(n)]`, or a base + step.

4. **video_project_config.py:104-111, 144** - Shot ids and narration are matched only by `SH%02d` == `[SHOT n]`. A shot with no timing row (number mismatch, an id that isn't `SHnn`, or one TTS shot failing at tts_generator.py:95-97 while timing.csv is still written) silently gets narration 0.0, duration = pad, 49 frames. The missing `shot_NN.wav` is only caught by the assembler, after all renders. Also, a partially failed TTS run still writes a timing.csv newer than script.txt, so `stage_tts` skips it forever (make_video.py:45).
   Fix: in `stage_plan`, abort when any shot has no timing row or no wav. Don't write timing.csv when any shot failed (or have it exit non-zero).

5. **video_project_config.py:60 / plan** - `frames_for` clamps to 117 frames (4.875 s), but `duration` is not clamped. The assembler then pads with tpad clone, so the clip freezes on its last frame. This is already happening: the last shot of P001 (5.70 s) and of P002 (5.94 s) each freeze for about 1 s. Narration over 3.97 s would also freeze.
   Fix: print a warning in `stage_plan` when `frames/24 < duration`. Optionally slow the clip (setpts) instead of freezing.

6. **image_picker_web_server.py:61-74** - POST has no Origin/Host or Content-Type check, and `body["image"]` is never validated. Any web page open in the browser can send a simple-request CSRF to 127.0.0.1:8190 (`/pick`, `/reroll`, `/done`). It can write an arbitrary path into picks.json, which is later read and uploaded to ComfyUI as `start_image`. Bad input (`_s` missing, bad JSON, unknown shot) raises in the handler, so the connection drops and the page's `await post` rejects with no UI feedback.
   Fix: reject requests whose `Origin` is not `http://127.0.0.1:8190`. Require that `image` is in that shot's candidate list and that `shot` is a known id. Wrap the handler in try/except and return 400.

7. **image_picker_web_server.py:53 + image-picker-page.html:51** - `json.dumps` output goes into `<script>` without escaping `</script>` or `<!--`. `description` and `narration` from script.txt are inserted with `innerHTML`. Any `<` or `&` in the script text breaks or injects markup. This is self-XSS, but a real correctness bug.
   Fix: `json.dumps(...).replace("<", "\\u003c")`. Build the meta div with `textContent`.

8. **make_video.py:146-155** - `--redo SHxx video` deletes the clip but keeps the same fingerprint, seed and pick. Wan is deterministic, so it re-renders an identical clip. Separately, an unknown shot id raises a bare `StopIteration`, and any second argument other than `images` is treated as `video`.
   Fix: bump the seed (store `video_seed` in state) on a video redo. Validate the shot id and use `choices`.

9. **make_video.py:114-120** - `stage_assemble` always writes a new `final/<id>-vN.mp4`. Every plain re-run ("resume until done") creates another version even when nothing changed, which contradicts "every stage skips work already done".
   Fix: skip when the newest final is newer than manifest.json and all its inputs, or when the manifest is unchanged.

### Low
10. **make_video.py:87** - `picks[shot["id"]]` raises KeyError on `--only videos` when a pick is missing. `stage_pick` checks that a key exists, not that the picked image file exists (for example after a manual delete). P001's placeholder picks (`"(v4 clip staged directly)"`) become a broken `start_image` after `--redo SHxx video` on P001.
11. **video_project_config.py:65-69** - The `glob(f"{id}*")` prefix match is ambiguous: `P00` resolves to P001, and `P001` would also match a future `P0010_*`. `self.id` keeps the user's casing, so `p002` produces `p002-v1.mp4` and the version regex misses existing `P002-v*` files. Fix: match `f"{id}_*"` exactly and take the id from project.json.
12. **video_project_config.py:84** - A string `ipa_weight` in shots.json (`"0.5"`) crashes the `:.2f` format. Use `float(...)`.
13. **image_picker_web_server.py:93** - Closing the tab without pressing "Xong" blocks `serve_forever` indefinitely, and a busy port 8190 raises an uncaught OSError. Acceptable for a local tool; consider a timeout or a clear message.
14. **image_picker_web_server.py:62** - A negative `Content-Length` makes `rfile.read(-1)` read until EOF, so the request hangs. Clamp it to at least 0.
15. **make_video.py:100** - The global `experiments/render-queue.json` is shared by all projects, so two projects running at once overwrite each other's queue.

## Verified OK
- Every child runs with cwd=ROOT and gets ROOT-relative paths, and each script resolves `ROOT / arg`. TTS `--out` is relative to the cwd (= ROOT). Correct.
- COMFY_PY runs the runners, TTS_PY runs TTS, and the upscale batch uses `sys.executable` (= COMFY_PY). Correct.
- `--log-file ""` and `"ease in"` survive `list2cmdline` quoting.
- Weight filenames: `str(0.2)` -> `float` -> `0.20` in the runner, which matches `image_path`'s `:.2f`, including for int 0.
- `/img`: `resolve()` plus an "under build/ and .png" check blocks `..` and absolute-path traversal. Note that it serves any PNG under build/, not only images/.
- An empty `character_override` correctly drops the character block.

## Unresolved questions
- Is the frozen tail on the last shot (from tail_seconds) intended, or should the last clip be slowed or extended?
- Should `--redo video` mean "new seed" or "re-render as is"?
