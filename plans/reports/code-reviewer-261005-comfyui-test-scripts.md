# Code Review: ComfyUI test scripts (2026-10-05)

Scope: scripts/comfyui_api_client.py, workflow_template_utils.py, experiment_contact_sheet_builder.py,
character_consistency_test_runner.py, workflows/api/character-scene-ipadapter-v1.json, start-comfyui-server-low-ram.bat.
Verified against ComfyUI 0.37.0 server.py / execution.py / main.py. No requests sent to the server.

## Verified correct (no change needed)
- /history semantics: an entry is written only in `PromptQueue.task_done` (execution.py:1321), after execution ends,
  with `status={status_str: success|error, completed: e.success, messages}` (main.py:370-374). Presence = finished;
  interrupt also yields `status_str='error'`, so it is raised. Cached SaveImage outputs are re-emitted into history
  (execution.py:448, 823), so re-queued identical prompts still yield downloadable images.
- Multipart upload: matches `image_upload` (server.py:397); `overwrite` accepts "true"; `subfolder/name` return is valid for LoadImage.
- CSV BOM: `utf-8-sig` only on create, plain `utf-8` on append is correct (avoids a mid-file BOM).
- /free body, /prompt 400 handling (HTTPError body surfaced), bat flags exist in cli_args.py:180/205.

## Findings

| Sev | Location | Issue | Fix |
|---|---|---|---|
| High | runner:99-116 | `download_images` return value ignored. If history has no `output`-type image (e.g. OUT_Image swapped for PreviewImage, or outputs empty), run prints success and logs a CSV row for a file that doesn't exist. | `if not client.download_images(...): raise ComfyUIError("no output image")` (or check `image_path.exists()`). |
| High | runner:50-58,109 | `append_log_row` not guarded. log.csv is scored manually in Excel; Excel locks the file -> `PermissionError` kills the run *after* the PNG was saved. On re-run the image is skipped, so that log row is lost permanently. | Catch `OSError` on append, retry/wait or write to a fallback `log.pending.csv`; or log skipped images that have no row. |
| Med | runner:96,107 | `render_seconds` measured from queue time, includes waiting behind other jobs (e.g. the currently running test job) -> wrong timing data. | Use `execution_start`/`execution_success` `timestamp` from `entry["status"]["messages"]` (execution.py:680). |
| Med | contact_sheet:22-23 | Thumb aspect taken from first existing cell = REF image (likely square/other ratio), not the 768x1344 renders -> renders shrunk into small cells. | Derive height from the first non-REF image, or from max aspect over all cells. |
| Med | runner:63, template_utils:12 | `encoding="utf-8"` on JSON: a scenes file saved by Notepad/Excel with BOM fails `json.loads` ("Unexpected UTF-8 BOM"). | Read with `encoding="utf-8-sig"` (handles both). |
| Low | runner:102 | Printing ComfyUI error text (may contain non-ASCII paths/Vietnamese) raises `UnicodeEncodeError` when stdout is redirected (cp1252), crashing the run. | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at start, or set `PYTHONIOENCODING=utf-8`. |
| Low | runner:52-58 | `is_new` false for a 0-byte existing log.csv -> rows with no header. | `is_new = not log_path.exists() or log_path.stat().st_size == 0`. |
| Low | client:67-69 | HTTP 200 with non-empty `node_errors` means the prompt WAS queued (server.py:1135, partial outputs); raising orphans a running job while the runner queues the next. Not hit with this single-output workflow. | Only raise if `"prompt_id"` absent; otherwise warn. |
| Low | client:100-104 | `wait_for_result` on server crash: each later item fails fast with "Cannot reach" and is logged as FAILED; loop keeps going. | In runner, `sys.exit` on "Cannot reach" like the CUDA case. |
| Low | runner:74 | Sampler lookup bypasses `find_node_id_by_title`; `v["_meta"]` KeyError on any node without `_meta`. | Use `find_node_id_by_title(template, "IN_Sampler")`. |
| Low | runner:82,118 | `{weight:.2f}` in filename: weights like 0.855 and 0.85 collide -> second one silently "skipped". | Use `{weight:g}` or validate uniqueness. |

## Unresolved questions
- Is weight=0 intended as a true "no-IPA baseline"? IPAdapter still runs (CLIP vision + patching) at weight 0; output should match but timing/VRAM won't. A bypass workflow would be a cleaner baseline.
