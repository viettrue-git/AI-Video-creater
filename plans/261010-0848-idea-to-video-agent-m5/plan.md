# M5 — Agent: idea → video (mascot series "Tiểu Mão")

Goal: user types an idea, then only (1) approves the script and (2) picks images. Everything else runs through the existing `make_video.py` pipeline.

Content writer decision: **Claude Code via a project skill** + deterministic Python scaffold/validator (no API key/cost; script approval needs a human anyway). Anthropic API kept as a later option (validator reusable).

| Phase | Content | Status |
|---|---|---|
| 1 | Character `characters/fox-tieu-mao-v1.json` + per-character narration (voice, person, syllables/s); `video_project_config` uses `p.voice`; shared `RISKY_MOTION` | done (P002/P003 status unchanged) |
| 2 | Story bible `docs/tieu-mao-story-bible.md` + `scripts/new_video_project.py` (next P id, skeleton files, `--list-series`) | done (tested P005/P006 allocation, test folders removed) |
| 3 | `scripts/validate_video_project.py` (fields, 5–8 shots, 25–33 s estimate, ASCII prompts, risky words, trigger, 1st person, audio) + `--approve` fingerprint gate in make_video `stage_tts` | done (estimate within ~10% of measured on P002/P003; broken test project → 6 errors caught) |
| 4 | Skill `.claude/skills/video-idea/SKILL.md` (flow: bible → scaffold → write → validate → Vietnamese approval table → approve → detached run) | done (git tracking pending user answer) |
| 5 | Optional: CLIP-ViT-H (already installed, MIT) similarity score → picker sorting/badge; back-test on P002/P003 picks | optional |
| 6 | First real episode E2E (P005), tune rules + syllables/s | todo |

Decided: voice Trúc Ly original pitch (user, 09/10); fox LoRA = v2 being trained (v1 too front-pose-biased).

## Key details
- Narration block in character JSON: `{"voice","person","self","audience","syllables_per_second"}`; project.json may override. P001–P003 unchanged (they keep `"voice"`).
- `P004_voice_tests` occupies P004 → allocator gives P005.
- `make_video.py` already > 200 lines: only 1–3 line hooks there; logic in modules.
- Validator length rule: per shot narration + pad ≤ 4.875 s (117 frames) warn; total 27–33 s else error.
- Picker scores are hints only, never auto-pick.

## Risks
- No lip-sync: narrator mascot keeps mouth closed/smiling; avoid talking-to-camera shots.
- LoRA weak at close-ups/unusual poses → rules prefer medium/full shots until v2 verified.
- Length estimate drift per voice → recalibrate from timing.csv after episode 1.

## User answers (10/10)
- Skill stays local (not in git). Voice tests moved to `experiments/tieu-mao-voice-tests` → next id P004.
- Yes: per-episode `publish-notes.txt` (YouTube Shorts + TikTok title/description/hashtags + AI label reminder) — in skill.

## Open questions
1. VieNeu preset voice commercial license — verify ("OK [VERIFY]" in register).
2. Recurring side characters? (each needs its own LoRA — out of M5 scope)
