# Code review — M5 idea-to-video agent (261010-0900)

Scope: video_project_config.py, make_video.py, new_video_project.py, validate_video_project.py,
desktop_notification.py, characters/fox-tieu-mao-v1.json, characters/explorer-v1.json, .claude/skills/video-idea/SKILL.md.

Checks run (read-only): `py_compile` on all 5 scripts passed. `validate_video_project.py P002`/`P003` printed "Hợp lệ" (rc 0).
`P001` gave rc 1 (finding 2). `make_video.py P003 status` was OK. A scratch regex test confirmed findings 6 and 8.

## Overall
Backward compatibility holds. P001–P003 all set `"voice"`, both characters have `narration`, and none has
`script_approved`, so the gate does not apply to them. The voice folder is still `slug("Thanh Bình")`. The approval
fingerprint is stable: `--approve` writes only `script_approved`, and the fingerprint reads only script.txt, the
`shots` list, `music` and `ambience`. No make_video stage writes project.json or shots.json (stages write only build/*
and picks.json), so the pipeline does not invalidate its own approval. "Trúc Ly" is a valid VieNeu preset. The
desktop notification is not open to injection: title and message go in through environment variables, the command
is passed as a list (no shell), the script has no double quotes, and CreateTextNode escapes XML.

## Findings (ranked)

1. **[Medium] The approval gate can leave the user stuck, and `--redo` deletes files before the gate runs.**
   validate_video_project.py:105-108,128-135; make_video.py:214-229 vs :54.
   - Re-approving requires the validator to report zero errors. After an edit, any unrelated error blocks
     re-approval: a LoRA file that was renamed, or the 25–33 s range check. That range check always uses the
     *estimated* syllable time, even when `timing.csv` has measured times. Example: the estimate says 24.8 s and the
     measured total is 26 s, so the validator errors, `--approve` is refused, and make_video stops at TTS for good.
     The only way out is editing project.json by hand.
   - `make_video P00N --redo SH04 video` (or `images`) deletes the clip, the upscaled clip, the images and the pick
     *before* `stage_tts` → `check_approved` stops the run. Tweaking `motion` and then redoing is a common step,
     so the user loses files and then gets a "DỪNG" message.
   - Fix: when timing.csv exists, use the measured time (`measured.get(no, estimate)`). Call `check_approved(p)` in
     `main()` right after `VideoProject(...)`, before the `--redo` handling (this also covers `--only`, see finding 5).
     Optionally, let `--approve` go through when the only error is the length check, but print it.

2. **[Medium] Music given by `tag` is wrongly reported as an error.** validate_video_project.py:49.
   P001 has `"music": {"tag": "music-inspiring"}` and gets "LỖI: music.prompt phải có 'instrumental'" (rc 1, observed).
   Library and tag music never has a prompt. Fix: apply the check only when there is a prompt:
   `if (m := cfg.get("music")) and m.get("prompt") is not None and "instrumental" not in m["prompt"]`.
   Keep a separate error for an empty prompt when there is no file or tag.

3. **[Medium] Crash with a raw KeyError when no voice is defined.** video_project_config.py:82.
   A character with no `narration.voice` plus a project with no `"voice"` raises `KeyError: 'voice'` inside the
   constructor. That breaks `status`, the validator and the picker, not only TTS. The order of precedence is also
   surprising: the old top-level `"voice"` overrides `project.narration.voice`.
   Fix: `self.voice = self.config.get("narration", {}).get("voice") or self.config.get("voice") or self.narration.get("voice")`.
   If it is still empty, `raise SystemExit("... thiếu 'voice' ...")`.

4. **[Medium] Missing `ipa_weight` is not caught for projects without LoRA.** video_project_config.py:85; validator
   loop at :76-91. For a character without LoRA (or `use_lora` false), a shot without `ipa_weight` raises a KeyError
   in `stage_images` or `status`, after TTS and audio have already run. Fix: in `check()`, when `not p.lora` and
   `"ipa_weight" not in shot`, add an error.

5. **[Low-Med] The gate can be bypassed, and the fingerprint misses some approved fields.** make_video.py:54,231.
   `--only images|videos|audio|plan` never calls `check_approved`, so a `motion` or `scene` edited after approval
   gets rendered. The fingerprint (validate:24-28) also leaves out `voice`, `narration`, `use_lora` and `character`.
   A voice change after approval is not detected, even though the user approved how it sounds.
   Fix: move the call into `main()` (as in finding 1) and add those config keys to the fingerprint data.

6. **[Low] Text in NFD form gives wrong syllable counts and a false error.** validate:39-40,70.
   Confirmed: for NFD text, `\w+` counts 16 tokens instead of 10, and `\btớ\b` does not match. A script saved in NFD
   by some editors, or pasted from macOS, therefore gets "phải xưng 'tớ'" as an error and a total that is too high.
   Fix: apply `unicodedata.normalize("NFC", ...)` in `parse_shots` (it is shared with TTS). Also use
   `re.escape(p.narration['self'])`.

7. **[Low] The third-person check is noisy and incomplete.** validate:21,72.
   In NFC text, `\b` works correctly with Vietnamese diacritics (verified). `nó` will fire on ordinary sentences about
   objects ("nó đẹp quá"), which is fine because it is only a warning. The check misses the most likely slip: the
   narrator using his own name ("Tiểu Mão ...") instead of "tớ". Fix: add the character's display name, for example
   a `narration.name` field. Keep `nó` as a warning.

8. **[Low] Folder name for an empty or very long slug.** new_video_project.py:40.
   A title made only of symbols or emoji gives `slug == ""`, so the folder is `P005_`. It still loads, but it is
   unclear. Long titles are not truncated, and `build/images-lora/SH01_w0.00_s111111.png` is nested deep, so the
   path can approach MAX_PATH. Fix: `(slug(title)[:40].strip('-') or 'untitled').replace('-', '_')`.

9. **[Low] SKILL.md does not fully match how the scripts behave.**
   - Section 6.2: `Get-Process python` always lists the ComfyUI server's python, so the check cannot tell whether
     the GPU is busy. Suggest
     `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? CommandLine -match 'make_video|train|render_video_queue'`.
   - Section 3: `"summary"` exists in the scaffold only when `--series` was passed.
   - The skill never says that any edit to script.txt, shots.json, music or ambience after `--approve` stops
     make_video until it is re-approved. It should say to re-run `--approve` after the user approves an edit.
   - Section 4: "max 3 rounds" with no instruction for what to do with errors that are still there afterwards
     (report them to the user).
   - The CLI flags it uses (`--title/--character/--series`, `--list-series`, `--approve`, the ps1 `ProjectId`) do
     match the scripts.

10. **[Low] Misleading "done" notification.** make_video.py:237-239.
    The full run (or `--only assemble`) sends "video đã xong" even when assemble skipped ("không có gì thay đổi").
    That notification shows the old output path, which looks like a new render. Fix: make `stage_assemble` return a
    flag and notify only when a new file was written, or word the message differently.

11. **[Low] One bad project.json breaks scaffolding.** new_video_project.py:26-31.
    `series_episodes` calls `read_json` on every `P*/project.json`. One malformed file makes both `create` and
    `--list-series` fail with a JSON traceback. Also, abandoned episodes still take an episode number (probably
    intended). Fix: wrap the read in try/except and skip the file with a warning.

## Not issues (checked)
- `next_project_id` counts `P004_voice_tests` (no project.json), so the next id is P005 and ids are never reused, as
  intended. The `P001` vs `P0010` matching is correct.
- `RISKY_MOTION` with `\b` and an `re.I` str pattern works. P002 now shows the expected flicker/shimmer warnings.
- The final `\b` after `paws?`/`fingers?` means "fingertips" is not flagged. That is minor, so I left it out.
- `check_approved` runs before the mtime-based TTS skip, so finished projects re-run cleanly.

## Unresolved questions
- Is the gate meant to block `--redo` after a motion tweak (strict), or only block TTS and narration changes? The
  answer decides whether `shots[].motion` belongs in the fingerprint.
