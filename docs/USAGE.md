# Usage — Errriiiccc's Idle Lab

**Note:** This guide still uses **POC names** (Bench, Loops, Missions, Observe, LCO). The **agreed product** is Idle Lab ↔ Flight Deck + Labs — see [FEATURES.md](FEATURES.md) (Target shell) and [pieces/shell/](pieces/shell/README.md). Use this file to operate the app **as it runs today**.

## Install

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

**System deps** (one-time):

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
winget install --id Gyan.FFmpeg -e
```

Idle Lab also looks for Tesseract under `C:\Program Files\Tesseract-OCR\` even if PATH is stale — restart the app after installing. Launch:

```powershell
.\.venv\Scripts\pythonw.exe -m idle_lab
```

## Refresh vs Restart

See [REFRESH-RESTART.md](REFRESH-RESTART.md). Short version: chat edits JSON → **Refresh** (F5); chat edits `.py` → **Restart**.

## Bench (presets)

1. Top chrome → **Anchor** → left-click BlueStacks or the click logger. Red **×** clears.
2. Load or create a preset under **Presets**. Use **Note** for observations without leaving the app.
3. Choose Foreground/Background, **Humanize** (default **Off**), countdown, loops.
4. **Start** or **F6**. Use the click logger to verify hits before trusting the game.

Humanize only affects playback/execution (jitter + timing). Preset JSON stays exact.

Preset JSON format: [preset-format.md](preset-format.md).

## Loops

### Files

| Path | Role |
| --- | --- |
| `automations/runtime.json` | `run_number` (default 1) |
| `automations/rois/` | Named OCR/crop regions |
| `automations/events/` | **Atoms** — reusable procedures (+ interval timing when pooled) |
| `automations/collections/` | **Molecules** — compositions (`run: once` \| `interval`) |
| `runs/` | Screenshots, clips, CSV (gitignored) |

Schema: [automation-schema.md](automation-schema.md).

### UI

1. Open the **Loops** workspace.
2. Toggle **Atoms** / **Molecules**. Each list row shows a short caption.
3. In **Details**, switch **Basic** vs **Detailed**.
4. **Reload** after editing JSON. **Start selected**: atom → run once now; molecule → once chain or interval pool per `run`.
5. **Start all enabled** — interval scheduler for every `enabled: true` atom.
6. **Stop** / F8 ends jobs.
7. **Walkthrough** (select a molecule first): guided tour (Space / A/B / Esc).
8. **Queue** + **Console** as before.

### Recommended first demo — humanize upgrade loop

1. Anchor BlueStacks / The Tower (upgrade panel closed).
2. Bench: method **Foreground**, **Humanize → Medium** (experiment; default is Off).
3. Molecule Lab → pick a live atom or pack (e.g. Stat collecting) → **Start selected** / **Run pack**.
4. Humanize still applies via chrome / settings — the old `humanize_upgrade_loop` demo lives under [`archive/automations/2026-11-10-cut-demos/`](../archive/automations/2026-11-10-cut-demos/REASON.md).

### Archived OCR A/B / clip demos

Click-logger and minute-clip flagship demos were CUT from live Refresh (Phase 5). Restore from archive only if a harness story needs them — the live app never loads `archive/`.

### Adding a new automation (no Python)

1. Add `automations/events/my_event.json` (and ROIs if needed).
2. Optionally reference it from a collection.
3. Click **Reload**.
4. **Start** (or restart) and watch the queue.

### Clip naming + CSV

- Clip: `runs/clips/run_{run_number}_wave_{wave_number}.mp4`
- Wave comes from OCR on a screenshot **immediately before** recording.
- CSV columns: `datetime,run_number,wave_number`

If OCR misses the wave, the name uses `xx` and the CSV stores `xx`.

## Missions

Named gather/verify passes for review chats (on disk: `ai-batches/`). See [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md), [PROBE-MISSIONS.md](PROBE-MISSIONS.md), and [examples/ai-batch-spec.json](../examples/ai-batch-spec.json).

## Scrolling

Wheel or middle-drag long lists. Leaving a tab keeps its scroll until you return or restart.
