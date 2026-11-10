# Implementation notes

**Living product inventory:** [FEATURES.md](FEATURES.md)  
**Tree map:** [LAYOUT.md](LAYOUT.md)  
**Purpose:** [VISION.md](VISION.md)

This file is **historical**, not the status source of truth. Early fork milestones below are kept so old chats still resolve; do not add new “ships today” claims here — put them in FEATURES.

## Fork baseline

Copied from `tower-autoclicker`, rebranded to Errriiiccc's Idle Lab / `idle_lab`. Original project left untouched.

## Early automations milestones (pre flight-deck / Missions rename)

1. Tab shell + JSON store + Reload — done.
2. Capture / OCR / logging — done (Tesseract + mss).
3. Scheduler priority (clip > A/B) — done.
4. A/B via click-logger SIGNAL + presets — done.
5. Clips + CSV — done (ffmpeg required on PATH).
6. Humanize layer (`humanize.py`) on Player / Loops presets / Missions — done (**default Off** today; early POC used Medium).
7. POC event `humanize_upgrade_loop` + preset `humanize atk def loop` — done.

Unit tests: `python -m unittest discover -s tests`.  
Harness: [HARNESS.md](HARNESS.md). Manual checks: [SMOKE-TESTS.md](SMOKE-TESTS.md).
