# Usage — Errriiiccc's Idle Lab

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

## Clicker (unchanged workflows)

1. Use the top **ANCHOR** bar (visible on every tab) → **Set anchor** → left-click BlueStacks or the click logger.
2. Load or create a preset under **Presets**.
3. Choose Foreground/Background, **Humanize** (default Medium), countdown, loops.
4. **Start** or **F6**. Use the click logger to verify hits before trusting the game.

Humanize only affects playback/execution (jitter + timing). Preset JSON stays exact.

Preset JSON format: [preset-format.md](preset-format.md).

## Automations

### Files

| Path | Role |
| --- | --- |
| `automations/runtime.json` | `run_number` (default 1) |
| `automations/rois/` | Named OCR/crop regions |
| `automations/events/` | Interval events + actions |
| `automations/collections/` | Ordered/branching graphs |
| `runs/` | Screenshots, clips, CSV (gitignored) |

Schema: [automation-schema.md](automation-schema.md).

### UI

1. Open the **Automations** tab.
2. Toggle **Events** / **Collections**. Each list row shows a short caption.
3. In **Details**, switch **Basic** (plain language + branch contention) vs **Detailed** (exact paths, outputs, nested steps).
4. **Reload** after editing JSON files. Optional `description` fields on events/collections/actions feed the Basic view.
5. **Start** begins the scheduler; **Stop** ends it.
6. **Walkthrough** (select a Collection first): guided on-screen tour with drawings.
   - **Space** — next linear step
   - **A / B / C…** — choose a branch to preview
   - **Esc** or **End tour** — exit
7. **Queue** shows running / waiting / deferred (e.g. A/B deferred while recording).
8. **Console** shows OCR observations/inferences, branches, preemption, errors.

### Recommended first demo — humanize upgrade loop

1. Anchor BlueStacks / The Tower (upgrade panel closed).
2. Clicker: method **Foreground**, **Humanize → Medium**.
3. Automations → select **Humanize upgrade loop** → **Reload** → **Start**.
4. Every ~10s the console should log Attack → Damage → Defense → Health → Attack, with slightly uneven timing/aim.
5. If Damage/Health miss, open preset `humanize atk def loop` in the Clicker tab and nudge those points, then Reload.

### Older OCR A/B demo

Re-enable `automations/events/ocr_ab_tick.json` and `minute_clip.json` (`"enabled": true`), Reload, then:

1. **Click logger**, then top bar **Set anchor** on that window.
2. Countdown **0**, method **Foreground**.
3. Automations → **Reload** → **Start**.
4. Watch console for 10s A/B ticks; toggle SIGNAL A/B on the logger.
   - SIGNAL **A** → UPPER (`ab choice a`); otherwise LOWER (`ab choice b`).
5. Inspect `runs/screenshots/`, `runs/clips/`, `runs/run_log.csv` when minute_clip is enabled.

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

## AI Batches

Named information-gathering passes for review chats. See [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md) and [examples/ai-batch-spec.json](../examples/ai-batch-spec.json).

## Scrolling

Wheel or middle-drag long lists. Leaving a tab keeps its scroll until you return or restart.
