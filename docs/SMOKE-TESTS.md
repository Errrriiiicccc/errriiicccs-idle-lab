# Smoke tests (10–15 minutes)

Run after install against the **current POC** UI (mega tabs). Target shell: [FEATURES.md](FEATURES.md). Prefer harness: [HARNESS.md](HARNESS.md).

## 0. Automated

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m idle_lab.harness story schema-validate-all
```

Expect unit OK and harness story green.

## 1. Bench still works

1. Launch `pythonw -m idle_lab` (deck-first: Activate, then **I** for Lab if needed).
2. Open **Click logger**. Top chrome → **Anchor** on it.
3. Load **sample three points**. Foreground, countdown 0, loops 1, Humanize Off → **Start**.
4. Logger reports hits on upper/middle/lower.
5. Confirm cyan frame follows move/resize; hides when minimized.

## 2. Loops shell

1. Open **Loops** workspace.
2. Atoms list shows known events (enable OCR A/B tick / Minute clip in JSON if you want the classic demo).
3. Molecules shows packs such as Health then Damage / Stat collecting.
4. Edit a title in JSON → **Reload** → list updates.

## 3. Capture + OCR + A/B

1. Anchor the click logger. Enable `ocr_ab_tick` if disabled → Loops → **Start**.
2. Within ~10s, console shows screenshot path and OCR for `signal_roi`.
3. Toggle SIGNAL on the logger between A and B.
4. Confirm console shows branch A vs B and the matching preset click (upper vs lower).

## 4. Priority: recording blocks A/B

1. Keep loops running (or set `minute_clip` `every_ms` to `15000`, Reload, Start).
2. When recording starts, queue shows minute clip **running** and A/B **deferred**.
3. Console notes priority preemption.

## 5. Chrome honesty

1. Edit a preset or atom on disk → Activity shows **Files changed — Refresh**.
2. **Refresh** (F5) reloads without killing the process.
3. **Stop all** halts Bench / Loops / Missions / Observe / LCO.
4. **Deactivate** on the flight deck also stops everything, then idles the deck.

Details: [USAGE.md](USAGE.md), [REFRESH-RESTART.md](REFRESH-RESTART.md).
