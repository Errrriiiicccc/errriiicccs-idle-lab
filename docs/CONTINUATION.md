# Continuation handoff

For the next chat working on **Errriiiccc's Idle Lab** (`c:\DEV\Projects\Cursor\errriiicccs-idle-lab`).

**North star:** [VISION.md](VISION.md) — human-translation workbench (demonstrate + describe → AI authors → Idle Lab runs via pixels + ordinary input; no injection/memory dumps).

**Active focus (2026-11-06):** Flight deck accordion ([`automations/flight_deck.json`](../automations/flight_deck.json)) — letter menus, digit leaves, two keys max. Lab Loops taxonomy stays separate. Next: perception `detect_hud_currency_mode`.

**Perception (parallel, active):** owned separately → [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md). Field table → [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md). Run regressions via Missions → **OCR fixture bench** (offline, auto-seeded from `examples/ai-batches/ocr-fixture-bench/`).

Shell: **Refresh / Restart / Stop all**, **Flight deck** + expand remap beside Anchor, workspaces **Bench · Observe · Missions · Loops**. Taxonomy: `automations/taxonomy.json`. Visual critique canvas:

`C:\Users\alexa\.cursor\projects\c-DEV-Projects-Cursor-errriiicccs-idle-lab\canvases\idle-lab-shell.canvas.tsx`

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data edits → Eric hits **Refresh** (F5); code edits → **Restart**.

Secondary: [HANDOFF-AI-BATCH-RUN.md](HANDOFF-AI-BATCH-RUN.md) — Missions Start → analyze `run_report.json` + Observe shots + comments.  
Probes: [PROBE-MISSIONS.md](PROBE-MISSIONS.md). Legacy OCR tweak prompt: [HANDOFF-OCR.md](HANDOFF-OCR.md) (history only).

## What works

- Fork of tower-autoclicker as package `idle_lab`; original tree untouched.
- **Chrome:** compact **Anchor** (+ red × clear), **Flight deck** + expand remap, **Refresh**, **Restart**, **Stop all**, Activity pulse, files-changed badge.
- **Flight deck:** movable topmost HUD; accordion from `flight_deck.json` (O/C/N/A/M → digits); Pause/Stop while running.
- **Bench:** presets, playback, hotkeys, click logger, per-preset Note comments.
- **Loops:** Atoms / Molecules browse (taxonomy), Start selected atom = once, molecule interval|once, scroll atoms, queue, console, Note comments.
- **Observe:** Screen Map capture + catalog; Note on batch or individual shot (also syncs `manifest.json` notes).
- **Missions:** AI batches with `steps[]` + optional `genre` (`probe` / `mission` / `bench`); Start/Stop; iterations + QUESTION/ACCEPTANCE for probes; Open linked Observe; screenshot-on-fail; Note on mission/request; seeds from `examples/ai-batches/`.
- File-driven ROIs, events, collections, `runtime.json` (`run_number`).
- OCR (Tesseract), A/B decide, priority scheduler, ffmpeg clips, CSV.
- Scroll memory; unit tests including comments + AI batch runner.

## Stubbed / incomplete

- Richer molecule branching / nested interval packs — basic once + interval Start works.
- Tower-tuned ROIs — placeholders; click-logger ROIs are the proven path.
- Inline JSON editors (files stay source of truth).
- Richer mission asserts beyond `ensure_*` + fail screenshots.
- In-app auto-classification of Observe shots.
- Collection runner / endgame loop automation.

## Where things live

| Concern | Path |
| --- | --- |
| Refresh/Restart contract | `docs/REFRESH-RESTART.md` |
| AI / Missions usage | `docs/AI-BATCH-USAGE.md` |
| Probe ownership | `docs/PROBE-MISSIONS.md` |
| Tower nav playbook | `docs/screen-maps/TOWER-NAV-PLAYBOOK.md` |
| Comments store | `lab-comments.json` (gitignored) + `src/idle_lab/comments.py` |
| App shell | `src/idle_lab/app.py` |
| Vision (do not edit unless asked) | workspace `idle-lab/docs/` |

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless Eric overrides in-message.

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
git push -u origin main
```

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab

## Smoke — after Restart

**Flight deck accordion:** Expand → **O** (Observe opens) → **2** shot; **C** switches menus; **A** → **1** stat collect once; **N** → **2** scroll down.

**Loops (Lab):** Atoms → Stat collect → Start once; Molecules → Stat collecting → interval pool.

## Suggested next tasks

1. Perception (parallel): Missions → OCR fixture bench; then wire `detect_hud_currency_mode` — [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md).
2. Split large atoms (e.g. status+buy) into smaller composed molecules.
3. Optional: taxonomy / flight-deck leaf to Start a named mission by slug.
