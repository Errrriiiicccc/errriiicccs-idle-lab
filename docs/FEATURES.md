# Features

## Clicker tab

- Shared top **ANCHOR** bar on every tab: Set / Clear, live window title + size. Left-click a window after Set; Esc cancels.
- Click-through cyan frame follows that window (including negative monitor coords).
- Create presets (instantaneous / one second / realtime); Space/Esc recording.
- Foreground and background clicks; focus; cursor restore; countdown.
- **Humanize** (Off / Light / Medium / Heavy, default Medium): runtime aim jitter, delay/hold variance, and foreground cursor travel. Applied to Clicker playback, Automations presets, and AI Batch clicks/waits — not written into preset JSON.
- Loop forever or N times; F6 / F7 / Esc run control.
- Rename, duplicate, delete, import, export, reload JSON presets.
- Click logger with upper/middle/lower targets plus WAVE/SIGNAL bands for OCR demos.

## Automations tab

- Browse Events or Collections from JSON; selection details; Reload.
- Live queue (running / waiting / deferred by priority).
- Console: OCR raw + parsed, branches, preemption, errors.
- Interval scheduler with priorities (recording blocks A/B tick).
- Screenshot, OCR ROIs, A/B decide, play preset, record clip (ffmpeg), CSV append.
- POC event `humanize_upgrade_loop` (every 10s): Attack → Damage → Defense → Health → Attack via preset `humanize atk def loop` (other demo events ship disabled so this showcase is clean).

## Screen Map tab

- Start a named batch under `screen-maps/`; screenshot mode ON.
- Space → capture immediately (loading overlay) → autofocused title dialog → save; Esc cancels dialog first, else ends batch.
- Busy overlay while capturing/saving; Space ignored until Ready.
- `manifest.json` with titles, filenames, timestamps, anchor hints, and null review fields.
- Browse past batches; click a shot (or View all) to open the screenshot viewer.
- Open batch folder in Explorer; Space/Esc only special while mode is active (pass-through during title dialog).

## AI Batches tab

- File-backed **AI Information Batch Gathering**: named batches of requests with optional executable `steps[]`.
- **Start / Stop**: runs click / scroll / wait / screenshot / play_preset against the anchored window; auto-creates and links a Screen Map batch; writes `run_report.json`.
- Filter / sort by status; completed batches show as already ran; detail shows what was taken per request.
- Manual link / event snapshot / feedback still available. Docs: [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md).

## Scrolling

- Mouse wheel + middle-drag (and left-drag on empty chrome) on scrollable menus.
- Per-tab scroll position persists in memory until you revisit that tab or restart the app.

## Not in this POC

Full Tower buy-priority playbooks, perfect HUD OCR, process injection, stealth/anti-detect claims, cloud agents. Collection branching is representable in data/UI but not fully executed. Screen Map does not auto-classify shots or invent strategy loops. AI Batches do not call an LLM in-process — they are a file hook for review chats.
