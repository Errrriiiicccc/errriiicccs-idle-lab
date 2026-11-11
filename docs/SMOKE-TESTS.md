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

1. Open Idle Lab → **Molecule Lab**.
2. Atoms list shows live events (CUT demos are under `archive/`, not Refresh).
3. Molecules shows packs such as Health then Damage / Stat collecting / Endgame Phase Loop.
4. Edit a title in JSON → **Refresh** → list updates.

## 3. Capture (Observation Lab)

1. Idle Lab → **Observation Lab** → **User**.
2. Anchor a window → **Start observation** → move/click → **Deactivate** (`` ` ``) to stop.
3. Catalog groups Today / Yesterday / Last 7 Days / The Past; Mark is cut.

## 4. Live Overlay Lab

1. Anchor → Idle Lab → **Live Overlay Lab** → **Start live** (or Deck **L**).
2. Hold **D** describes; Esc exits live; Deactivate stops all.

## 5. Chrome honesty

1. Edit a preset or atom on disk → Activity shows **Files changed — Refresh**.
2. **Refresh** (F5) reloads without killing the process.
3. **Stop all** / **Deactivate** halt runners (Molecules, Observation, Live Overlay, AI mission).
4. **Deactivate** on the flight deck also stops everything, then idles the deck.

Details: [USAGE.md](USAGE.md), [REFRESH-RESTART.md](REFRESH-RESTART.md).
