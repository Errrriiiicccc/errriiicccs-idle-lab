# Implementation

Unit tests cover coordinates, presets, automation schema, A/B decide, scheduler priority, CSV shape, OCR parse helpers, and clip naming.

Manual checks: [SMOKE-TESTS.md](SMOKE-TESTS.md).

## Fork baseline

Copied from `tower-autoclicker`, rebranded to Errriiiccc's Idle Lab / `idle_lab`. Original project left untouched.

## Automations milestones

1. Tab shell + JSON store + Reload — done.
2. Capture / OCR / logging — done (Tesseract + mss).
3. Scheduler priority (clip > A/B) — done.
4. A/B via click-logger SIGNAL + presets — done.
5. Clips + CSV — done (ffmpeg required on PATH).
6. Humanize layer (`humanize.py`, default Medium) on Player / Automations presets / AI Batch — done.
7. POC event `humanize_upgrade_loop` + preset `humanize atk def loop` — done.
