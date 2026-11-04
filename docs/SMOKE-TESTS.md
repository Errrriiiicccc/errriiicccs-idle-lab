# Smoke tests (10–15 minutes)

Run after install. Prefer the click logger over The Tower for OCR/A/B.

## 0. Automated

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expect OK (33+ tests).

## 1. Clicker still works

1. Launch `pythonw -m idle_lab`.
2. Open **Click logger**. **Set anchor** on it.
3. Load **sample three points**. Foreground, countdown 0, loops 1 → **Start**.
4. Logger reports hits on upper/middle/lower.
5. Confirm cyan frame follows move/resize; hides when minimized.

## 2. Automations shell

1. Open **Automations** tab.
2. Events list shows **OCR A/B tick** and **Minute clip**.
3. Collections shows **Demo POC** with children + phase branches in details.
4. Edit a title in JSON → **Reload** → list updates.

## 3. Capture + OCR + A/B

1. Anchor the click logger. Automations → **Start**.
2. Within ~10s, console shows screenshot path and OCR for `signal_roi`.
3. Toggle SIGNAL on the logger between A and B.
4. Confirm console shows branch A vs B and the matching preset click (upper vs lower).

## 4. Priority: recording blocks A/B

1. Keep automations running (or set `minute_clip` `every_ms` to `15000`, Reload, Start).
2. When recording starts, queue shows minute clip **running** and A/B **deferred**.
3. Console notes priority preemption.
4. After ~10s, clip appears under `runs/clips/`; A/B resumes.

## 5. CSV

1. After a clip, open `runs/run_log.csv`.
2. Header: `datetime,run_number,wave_number`.
3. Row matches run number from `automations/runtime.json` and OCR wave (or `xx`).

## 6. Failure visibility

1. Stop automations. Clear anchor. Start → console shows anchor/capture errors (no silent success).
2. Rename `ffmpeg` off PATH temporarily if you want to confirm a clear video error (optional).
