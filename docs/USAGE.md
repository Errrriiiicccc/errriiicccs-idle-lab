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

1. **Set anchor** → left-click BlueStacks or the click logger.
2. Load or create a preset under **Presets**.
3. Choose Foreground/Background, countdown, loops.
4. **Start** or **F6**. Use the click logger to verify hits before trusting the game.

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
2. Toggle **Events** / **Collections**, select an item to see details.
3. **Reload** after editing JSON files.
4. **Start** begins the scheduler; **Stop** ends it.
5. **Queue** shows running / waiting / deferred (e.g. A/B deferred while recording).
6. **Console** shows OCR observations/inferences, branches, preemption, errors.

### Recommended first demo

1. Clicker → **Click logger** → **Set anchor** on that window.
2. Countdown **0**, method **Foreground**.
3. Automations → **Reload** → **Start**.
4. Watch console for 10s A/B ticks; toggle SIGNAL A/B on the logger.

   **What A/B means (Demo POC):** OCR reads the yellow **SIGNAL** band on the click logger.
   - If parsed value **equals** `A` → **PATH A** → one click on the **UPPER** circle (`ab choice a`).
   - Otherwise → **PATH B** → one click on the **LOWER** circle (`ab choice b`).
   Console prints the OCR raw/parsed values, the rule, why A/B was chosen, and what that path does.
5. Wait for the 60s clip (or temporarily edit `minute_clip.json` `every_ms` to `20000` for a faster smoke, then Reload).
6. Inspect `runs/screenshots/`, `runs/clips/run_1_wave_*.mp4`, `runs/run_log.csv`.

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
