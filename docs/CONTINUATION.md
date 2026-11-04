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
- **Screen Map tab:** Start batch → Space title dialog → anchored PNG → Esc ends; `screen-maps/<batch>/` + `manifest.json` (review placeholders).
- Unit tests for schema, decide, scheduler priority, CSV, branch resolve, naming, coords/presets, Screen Map sanitize/manifest/mode.

## Stubbed / incomplete

- Collection **execution** (Main Gameplay Loop, phase switching, stop_when) — schema + UI only.
- Tower-tuned ROIs — placeholders; click-logger ROIs are the proven path.
- Inline editing of automations in the UI (files are source of truth).
- Barrier/yield mid-sequence for mouse actions (POC actions are short/atomic).
- Rich presence/template matching beyond OCR parse helpers.
- In-app auto-classification of Screen Map shots (use review chat + [SCREEN-MAP-REVIEW-PROMPT.md](SCREEN-MAP-REVIEW-PROMPT.md)).

## Where things live

| Concern | Path |
| --- | --- |
| Schema docs | `docs/automation-schema.md` |
| Sample events | `automations/events/ocr_ab_tick.json`, `minute_clip.json` |
| Sample collection | `automations/collections/demo_poc.json` (+ phase stubs) |
| Runtime knobs | `automations/runtime.json` |
| Engine | `src/idle_lab/automations/` |
| Screen Map | `src/idle_lab/screen_map/` |
| Batch output | `screen-maps/` (gitignored) |
| App shell / tabs | `src/idle_lab/app.py`, `automations/ui.py`, `screen_map/ui.py` |
| Vision (do not edit unless asked) | workspace `idle-lab/docs/` |

## Merge path — Automations + Screen Map → one Idle Lab window

Both PoCs already share one process and one `CTkTabview` in `app.py` (Clicker / Automations / Screen Map). Later merge work should stay **additive**:

1. Keep a single shared `Anchor` (already true).
2. Keep Screen Map batch I/O file-based (`manifest.json`) so review chats never depend on tab layout.
3. Optional later: nest Screen Map under a “Lab” or “Capture” area, or a mode toggle next to Automations — without rewriting capture/manifest.
4. Do not fold Screen Map into the Automations scheduler; they stay separate concerns (manual mapping vs runtime OCR/clips).
5. Deep-dive strategy (loops/phases/CSV schemas) consumes review output + Automations data contracts; it is not owned by either tab.

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless Eric overrides in-message.

**Deferred push (business hours):** leave commits local; after 17:00 Eastern:

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
git push -u origin main
```

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab

## Suggested next tasks

1. Manual Screen Map smoke: [SCREEN-MAP-SMOKE-TESTS.md](SCREEN-MAP-SMOKE-TESTS.md); then review chat with [SCREEN-MAP-REVIEW-PROMPT.md](SCREEN-MAP-REVIEW-PROMPT.md).
2. Tune Tower `wave_roi` from a real screenshot; keep click-logger samples as regression harness.
3. Implement collection runner: ordered children, branch resolution, loop/stop_when.
4. Optional CSV rows on A/B ticks; extend columns backward-compatibly.
5. Safer yield points when mouse sequences grow longer than one preset.
6. Presence checks (template match) for menu/state without OCR.
7. If remote was prepared but not pushed mid-day: push after 17:00 Eastern.
