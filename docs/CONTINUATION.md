# Continuation handoff

For the next chat working on **Errriiiccc's Idle Lab** (`c:\DEV\Projects\Cursor\errriiicccs-idle-lab`).

## What works

- Fork of tower-autoclicker as package `idle_lab`; original tree untouched.
- Clicker tab: anchor, presets, playback, hotkeys, click logger (with WAVE/SIGNAL OCR harness).
- Automations tab: Events/Collections lists, details, live queue, console, Reload/Start/Stop.
- File-driven ROIs, events, collections, `runtime.json` (`run_number`).
- Screenshot → disk; OCR (Tesseract) with observation + inference logging.
- A/B decide (pure function + sample event playing `ab choice a` / `ab choice b`).
- Priority scheduler: `minute_clip` (prio 100) hard-blocks `ocr_ab_tick` (prio 10) while recording.
- ffmpeg clips → `runs/clips/run_{n}_wave_{w}.mp4`; CSV → `runs/run_log.csv`.
- Unit tests for schema, decide, scheduler priority, CSV, branch resolve, naming, coords/presets.

## Stubbed / incomplete

- Collection **execution** (Main Gameplay Loop, phase switching, stop_when) — schema + UI only.
- Tower-tuned ROIs — placeholders; click-logger ROIs are the proven path.
- Inline editing of automations in the UI (files are source of truth).
- Barrier/yield mid-sequence for mouse actions (POC actions are short/atomic).
- Rich presence/template matching beyond OCR parse helpers.

## Where things live

| Concern | Path |
| --- | --- |
| Schema docs | `docs/automation-schema.md` |
| Sample events | `automations/events/ocr_ab_tick.json`, `minute_clip.json` |
| Sample collection | `automations/collections/demo_poc.json` (+ phase stubs) |
| Runtime knobs | `automations/runtime.json` |
| Engine | `src/idle_lab/automations/` |
| App shell / tabs | `src/idle_lab/app.py`, `automations/ui.py` |
| Vision (do not edit unless asked) | workspace `idle-lab/docs/` |

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless Eric overrides in-message.

**Ready to push after 17:00 Eastern (2026-11-04):** public empty remote exists; local `main` has commit `b1ce5a0`.

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
git push -u origin main
```

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab

## Suggested next tasks

1. Tune Tower `wave_roi` from a real screenshot; keep click-logger samples as regression harness.
2. Implement collection runner: ordered children, branch resolution, loop/stop_when.
3. Optional CSV rows on A/B ticks; extend columns backward-compatibly.
4. Safer yield points when mouse sequences grow longer than one preset.
5. Presence checks (template match) for menu/state without OCR.
6. If remote was prepared but not pushed mid-day: push after 17:00 Eastern.
