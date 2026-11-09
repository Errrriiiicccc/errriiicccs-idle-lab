# Continuation handoff

For the next chat working on **Errriiiccc's Idle Lab** (`c:\DEV\Projects\Cursor\errriiicccs-idle-lab`).

**North star:** [VISION.md](VISION.md) — human-translation workbench (demonstrate + describe → AI authors → Idle Lab runs via pixels + ordinary input; no injection/memory dumps).

**Active focus (2026-11-08):** **Live Control Overlay** now loads Tower **object map** (`automations/maps/tower_main_gameplay.objects.json`) — typed tabs/panels/lists/buys. Humanize defaults **Off**. Next: fill visual-state colors from Observe crops; refined observation ROI crops. Molecules/`run_event` shipped. Perception **paused** (watch bad data only).

**Perception (paused):** no new OCR wiring unless bad data shows up. Bad-data watchlist → [knowledge/ocr-trust.json](knowledge/ocr-trust.json). Field table → [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md). Handoff (history / resume) → [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md).

Shell: **Refresh / Restart / Stop all**, **Flight deck** + expand remap beside Anchor, workspaces **Bench · Observe · Missions · Loops**. Taxonomy: `automations/taxonomy.json`. Visual critique canvas:

`C:\Users\alexa\.cursor\projects\c-DEV-Projects-Cursor-errriiicccs-idle-lab\canvases\idle-lab-shell.canvas.tsx`

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data edits → Eric hits **Refresh** (F5); code edits → **Restart**.

**Test without Computer Use:** [HARNESS.md](HARNESS.md) — tiered `python -m idle_lab.harness …` (story/fixture/unit first; `doctor` + `live` only when Tower pixels are required). Context: [`lab-context.json`](../lab-context.json) (active target = Tower / BlueStacks).

Secondary: [HANDOFF-AI-BATCH-RUN.md](HANDOFF-AI-BATCH-RUN.md) — Missions Start → analyze `run_report.json` + Observe shots + comments.  
Probes: [PROBE-MISSIONS.md](PROBE-MISSIONS.md). Legacy OCR tweak prompt: [HANDOFF-OCR.md](HANDOFF-OCR.md) (history only).

## What works

- Fork of tower-autoclicker as package `idle_lab`; original tree untouched.
- **Chrome:** compact **Anchor** (+ red × clear), **Flight deck** + expand remap, **Refresh**, **Restart**, **Stop all**, Activity pulse, files-changed badge.
- **Flight deck:** movable topmost HUD; **deck-first boot** (Enter/Esc/A/I); system tray icon (Open Lab / Show Deck / Quit); accordion from `flight_deck.json` (U/O/C/N/A/M → digits); Esc peels menus then quit-confirms when Lab is hidden; Pause/Stop while running.
- **Live Control Overlay:** object-map hit-targets (`automations/maps/tower_main_gameplay.objects.json`); Esc exits; Stay-in-mode; deck shows LCO-active surface.
- **Bench:** presets, playback, hotkeys, click logger, per-preset Note comments.
- **Loops:** Atoms / Molecules browse (taxonomy), Start selected atom = once, molecule interval|once, scroll atoms, queue, console, Note comments.
- **Observe:** Observation sessions (pointer timeline + dual-write Screen Map shots) + catalog; Note on batch or shot.
- **Missions:** AI batches with `steps[]` + optional `genre` (`probe` / `mission` / `bench`); Start/Stop; iterations + QUESTION/ACCEPTANCE for probes; Open linked Observe; screenshot-on-fail; Note on mission/request; seeds from `examples/ai-batches/`.
- **Harness:** `python -m idle_lab.harness` — classify / unit / story / fixture / doctor / live; reports under `runs/harness/`.
- File-driven ROIs, events, collections, `runtime.json` (`run_number`).
- OCR (Tesseract), A/B decide, priority scheduler, ffmpeg clips, CSV.
- Scroll memory; unit tests including comments + AI batch runner.

## Stubbed / incomplete

- Richer molecule branching / nested interval packs — basic once + interval Start works; `run_event` composes atoms inside an orchestrator.
- Tower-tuned ROIs — placeholders; click-logger ROIs are the proven path.
- Inline JSON editors (files stay source of truth).
- Richer mission asserts beyond `ensure_*` + fail screenshots.
- In-app auto-classification of Observe shots.
- Collection runner / endgame loop automation.
- Perception: `detect_hud_currency_mode` still PoC-only (paused).

## Where things live

| Concern | Path |
| --- | --- |
| Refresh/Restart contract | `docs/REFRESH-RESTART.md` |
| AI / Missions usage | `docs/AI-BATCH-USAGE.md` |
| Probe ownership | `docs/PROBE-MISSIONS.md` |
| Tower nav playbook | `docs/screen-maps/TOWER-NAV-PLAYBOOK.md` |
| Live Control Overlay | `docs/LIVE-CONTROL-OVERLAY.md` |
| Object map (templates) | `docs/OBJECT-MAP.md` |
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

**Deck-first:** Lab starts hidden → boot prompt on deck → Enter re-anchors (if last title live) or **A** click-anchor → **I** opens Lab. Esc peel: section → collapse → quit confirm when Lab hidden.

**Flight deck accordion:** Expand → **U→1** Live Control Overlay (Q/W/E tabs, 1–6 buys, R/F one-row scroll, V stat, B refresh; Esc exits Live Control). **O→1** observation; **C** currency/gem; **A** → **1** stat collect, **2** status+buy, **3/4** buy Health/Damage; **N** → **2** scroll down; **M** → **4** Health then Damage once.

**Loops (Lab):** Atoms → Buy Health / Buy Damage / Status + buy; Molecules → Health then Damage (once) or Stat collecting / Endgame phase (interval).

## Bad-data / OCR trust (automatic)

On any CSV, observation digest, OCR bench, or `run_report.json` that touches HUD reads: open [knowledge/ocr-trust.json](knowledge/ocr-trust.json) and review **watching** fields only. Promote to `trusted` (and stop auto-reviewing) when fixtures stay green **and** a live `stat_collect` row matches. Demote trusted → watching on a miss. Do **not** resume perception feature work unless Eric asks or watching fields keep failing.

## Suggested next tasks

1. Smoke Live Control: Restart → anchor → **U→1** → clicks show keys, non-clicks show icons; bold deck line **HOLD D = DESCRIBE**; hold D for hotkeys + HV descriptors; Esc exit.
2. Optional: taxonomy / flight-deck leaf to Start a named mission by slug.
3. Perception resume (only if bad data): Missions → OCR fixture bench; wire `detect_hud_currency_mode` — [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md).
