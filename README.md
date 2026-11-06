# Errriiiccc's Idle Lab

Personal Windows **human-translation workbench**: you show a screen and say what you want in plain language; AI helps turn that into file-backed automations; Idle Lab runs them with ordinary mouse input and pixel observation. No process injection, no memory dumps — the same cues a human could see.

Workspaces: window-anchored presets (**Bench**), timed automations (**Loops**), titled screenshot batches (**Observe**), and AI gather/verify runs (**Missions**), under one chrome with **Refresh / Restart / Stop all**.

Check the target app's rules before leaving a run going. North star: [docs/VISION.md](docs/VISION.md).

## Run

`python` on this PC is often the Microsoft Store alias. Use `py -3` for the venv, and `pythonw` to launch without a console behind the app.

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\pythonw.exe -m idle_lab
```

**System deps for Automations:** [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and `ffmpeg` on `PATH`.

## Workspaces

- **Bench** — presets, playback, hotkeys, click logger (the hands).
- **Observe** — Screen Map: Space → title → PNG; browse batches/shots; comments.
- **Missions** — AI gather/verify batches with `steps[]`, linked Observe, run reports.
- **Loops** — file-driven events/collections scheduler (OCR, A/B, clips, CSV).

Top chrome: compact **Anchor**, **Flight deck** / expand remap, **Refresh** (F5, data), **Restart** (code), **Stop all**, Activity. See [docs/REFRESH-RESTART.md](docs/REFRESH-RESTART.md). Flight deck + Loops folders share [automations/taxonomy.json](automations/taxonomy.json) (expand `` ` `` by default).

## Hotkeys (Bench)

- **Anchor**, then left-click the target window. Esc cancels.
- **Space** adds a point while recording. **Esc** saves.
- **F5** refreshes all file-backed stores.
- **F6** starts/stops playback. **F7** pauses. **Esc** stops a run.

## Loops POC demo

1. Open **Click logger**, set Anchor on it.
2. Loops → **Reload** → **Start** (or global Refresh first if files changed).
3. Every **10s**: screenshot → OCR `SIGNAL A/B` → play `ab choice a` or `ab choice b`.
4. Every **60s**: OCR wave → record a **10s** clip (`runs/clips/run_1_wave_xx.mp4`) → CSV row. Recording **blocks** the 10s tick.
5. Click the SIGNAL band in the click logger to toggle A ↔ B; click WAVE to bump the number.

Details: [docs/USAGE.md](docs/USAGE.md), [docs/SMOKE-TESTS.md](docs/SMOKE-TESTS.md), [docs/automation-schema.md](docs/automation-schema.md).  
Observe: [docs/SCREEN-MAP-USAGE.md](docs/SCREEN-MAP-USAGE.md). Missions: [docs/AI-BATCH-USAGE.md](docs/AI-BATCH-USAGE.md).  
Next chat: [docs/CONTINUATION.md](docs/CONTINUATION.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Repo

https://github.com/Errrriiiicccc/errriiicccs-idle-lab

If you finish work during business hours (Mon–Fri 09:00–17:00 Eastern), leave commits local and push after 17:00.

## Origin

Forked from `tower-autoclicker` (left untouched). Vision notes for the wider Idle Lab idea live separately under the workspace `idle-lab/` docs tree.
