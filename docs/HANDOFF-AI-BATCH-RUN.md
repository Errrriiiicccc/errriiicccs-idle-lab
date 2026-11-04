# Handoff — AI batch runner + Tower nav lab

Paste this into a **new chat** (Agent). Eric will also paste feedback from the batch he just ran.

## Role

You are continuing **Errriiiccc's Idle Lab** at `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`.

Eric ran (or is running) an **AI Batches → Start** job. Your job:

1. Read his feedback + on-disk artifacts.
2. Judge success / fail / partial (clicks missed? wrong tab? scroll too little?).
3. Update the playbook and/or tweak `batch.json` steps (`nx`/`ny`, scroll amounts) so the next Start is better.
4. Do **not** take over his mouse/desktop unless he explicitly asks. He runs batches; you analyze and fix files.

## Repo facts

- Package: `idle_lab` under `src/idle_lab/`
- **AI Batches tab**: ledger + **Start/Stop runner** (`ai_batch/runner.py`, `ai_batch/ui.py`, wired in `app.py`)
- Runner `steps[]`: `wait` / `click` / `scroll` / `scroll_map` / `ensure_upgrade_tab` / `screenshot` / `play_preset`
- Screenshots: `screen-maps/ai-run-<batch-slug>/` · report: `ai-batches/<slug>/run_report.json` · def: `batch.json` (ai-batches gitignored)
- **Nav source of truth:** [screen-maps/TOWER-NAV-PLAYBOOK.md](screen-maps/TOWER-NAV-PLAYBOOK.md) · [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md)

### Scroll lab — completed (prior chat)

- `ai-batches/upgrade-scroll-controlled/` + `screen-maps/ai-run-upgrade-scroll-controlled/`
- Playbook has: currency toggle; `ensure_upgrade_tab`; drag `0.10` ≈ 1 row + hold_end (no wheel); Attack ~5 / Defense ~3 / Utility ~2 downs to bottom
- Do not re-run for calibration unless coords drift

### Next / other local batches

- If present: `damage-buy-calibrate` (or create new buy/UW/collection batches from the playbook)

## How Eric runs a batch

1. Restart Idle Lab if code changed: `.\.venv\Scripts\pythonw.exe -m idle_lab`
2. ANCHOR → BlueStacks
3. AI Batches → Reload → select batch → **Start**
4. When idle: tell you it ran + paste feedback + paths if needed

## What you should read first

```
docs/screen-maps/TOWER-NAV-PLAYBOOK.md
docs/AI-BATCH-USAGE.md
ai-batches/upgrade-scroll-controlled/batch.json
ai-batches/upgrade-scroll-controlled/run_report.json
screen-maps/ai-run-upgrade-scroll-controlled/
```

Then whatever new batch Eric is running (its `batch.json` + `run_report.json` + linked Screen Map).

## Expected workflow this chat

1. Ingest Eric’s feedback (what he saw vs what the batch intended).
2. Open the PNGs + `run_report.json`; mark each request mentally: done correctly / missed click / wrong UI / incomplete scroll.
3. Patch `batch.json` steps if needed; reset failed requests to `"status": "pending"` (clear bad `result` if re-running).
4. Update `TOWER-NAV-PLAYBOOK.md` with confirmed facts only.
5. Tell Eric exactly what to Start next (same batch vs new batch).

## Rules

- Prefer editing batch JSON + docs over asking Eric to hand-capture.
- No computer-use / screen control unless he asks.
- Local commits OK if he asks; **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless he overrides.
- Do not edit workspace `idle-lab/docs/` vision tree unless asked.

## Push (after hours)

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
git push -u origin main
```

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab
