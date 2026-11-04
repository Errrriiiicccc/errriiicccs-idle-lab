# Features

## Clicker tab

- Shared top **ANCHOR** bar on every tab: Set / Clear, live window title + size. Left-click a window after Set; Esc cancels.
- Click-through cyan frame follows that window (including negative monitor coords).
- Create presets (instantaneous / one second / realtime); Space/Esc recording.
- Foreground and background clicks; focus; cursor restore; countdown.
- Loop forever or N times; F6 / F7 / Esc run control.
- Rename, duplicate, delete, import, export, reload JSON presets.
- Click logger with upper/middle/lower targets plus WAVE/SIGNAL bands for OCR demos.

## Automations tab

- Browse Events or Collections from JSON; selection details; Reload.
- Live queue (running / waiting / deferred by priority).
- Console: OCR raw + parsed, branches, preemption, errors.
- Interval scheduler with priorities (recording blocks A/B tick).
- Screenshot, OCR ROIs, A/B decide, play preset, record clip (ffmpeg), CSV append.

## Screen Map tab

- Start a named batch under `screen-maps/`; screenshot mode ON.
- Space → title dialog → PNG of the anchored window; Esc cancels dialog first, else ends batch.
- `manifest.json` with titles, filenames, timestamps, anchor hints, and null review fields.
- Open batch folder in Explorer; Space/Esc only special while mode is active (pass-through during title dialog).

## Not in this POC

Full Tower buy-priority playbooks, perfect HUD OCR, process injection, humanization, cloud agents. Collection branching is representable in data/UI but not fully executed. Screen Map does not auto-classify shots or invent strategy loops.
