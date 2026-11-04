# Errriiiccc's Idle Lab

Personal Windows toolkit forked from the Tower Autoclicker: keep window-anchored click presets, and add a file-driven **Automations** tab for capture, OCR, A/B decisions, priorities, short clips, and CSV logging.

It sends ordinary mouse input and reads pixels from the screen. It does not inject into games or hide itself. Check the game's rules before leaving a run going.

## Run

`python` on this PC is often the Microsoft Store alias. Use `py -3` for the venv, and `pythonw` to launch without a console behind the app.

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\pythonw.exe -m idle_lab
```

**System deps for Automations:** [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and `ffmpeg` on `PATH`.

## Tabs

- **Clicker** — same workflows as the autoclicker: anchor, record presets, playback, hotkeys, click methods, click logger.
- **Automations** — load events/collections from `automations/`, run a priority scheduler, watch the queue and console.

## Hotkeys (Clicker)

- **Set anchor**, then left-click the target window. Esc cancels.
- **Space** adds a point while recording. **Esc** saves.
- **F6** starts/stops playback. **F7** pauses. **Esc** stops a run.
- F6 and F7 are captured while the app is open.

## Automations POC demo

1. Open **Click logger**, set anchor on it.
2. Automations → **Reload** → **Start**.
3. Every **10s**: screenshot → OCR `SIGNAL A/B` → play `ab choice a` or `ab choice b`.
4. Every **60s**: OCR wave → record a **10s** clip (`runs/clips/run_1_wave_xx.mp4`) → CSV row. Recording **blocks** the 10s tick.
5. Click the SIGNAL band in the click logger to toggle A ↔ B; click WAVE to bump the number.

Details: [docs/USAGE.md](docs/USAGE.md), [docs/SMOKE-TESTS.md](docs/SMOKE-TESTS.md), [docs/automation-schema.md](docs/automation-schema.md).  
Next chat: [docs/CONTINUATION.md](docs/CONTINUATION.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Origin

Forked from `tower-autoclicker` (left untouched). Vision notes for the wider Idle Lab idea live separately under the workspace `idle-lab/` docs tree.
