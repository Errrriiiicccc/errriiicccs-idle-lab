# Handoff — Missions / probe runs

Paste this into a **new chat** (Agent). Eric will also paste feedback from the batch he just ran.

## Role

You are continuing **Errriiiccc's Idle Lab** at `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`.

Eric ran (or is running) a **Missions → Start** job. Your job:

1. Read his feedback + on-disk artifacts (`QUESTION.md` when `genre` is `probe`).
2. Judge success / fail / partial (clicks missed? wrong tab? scroll too little?).
3. Update the playbook and/or tweak `batch.json` steps (`nx`/`ny`, scroll amounts) so the next Start is better.
4. For probes: fill `iterations/*/reflection.md` (answered / partial / blocked + next probe).
5. Do **not** take over his mouse/desktop unless he explicitly asks. He runs batches; you analyze and fix files.

Ownership contract: [PROBE-MISSIONS.md](PROBE-MISSIONS.md).

## Repo facts

- Package: `idle_lab` under `src/idle_lab/`
- **Missions** workspace: ledger + **Start/Stop** (`ai_batch/runner.py`, `ai_batch/ui.py`)
- Runner `steps[]`: `wait` / `click` / `scroll` / `scroll_map` / `ensure_upgrade_tab` / `screenshot` / `play_preset` / `ocr_fixture_bench`
- Artifacts: `screen-maps/ai-run-<batch-slug>/` · `ai-batches/<slug>/run_report.json` · `batch.json` (ai-batches gitignored; seeds from `examples/ai-batches/`)
- **Nav source of truth:** [screen-maps/TOWER-NAV-PLAYBOOK.md](screen-maps/TOWER-NAV-PLAYBOOK.md) · [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md)

### Seeded probes (Reload copies if missing)

- `probe-currency-toggle` — HUD balances ↔ /min
- `probe-upgrade-tabs` — Attack / Defense / Utility ensure
- `probe-scroll-one-row` — one drag ≈ one tile row

### Scroll lab — completed (prior chat)

- `ai-batches/upgrade-scroll-controlled/` + `screen-maps/ai-run-upgrade-scroll-controlled/`
- Playbook has: currency toggle; `ensure_upgrade_tab`; drag `0.10` ≈ 1 row + hold_end (no wheel); Attack ~5 / Defense ~3 / Utility ~2 downs to bottom
- Do not re-run for calibration unless coords drift

## How Eric runs a batch

1. Restart Idle Lab if code changed: `.\.venv\Scripts\pythonw.exe -m idle_lab`
2. ANCHOR → BlueStacks (skip for offline benches)
3. Missions → Reload → select batch → **Start**
4. When idle: tell you it ran + paste feedback + paths if needed

## What you should read first

```
docs/PROBE-MISSIONS.md
docs/screen-maps/TOWER-NAV-PLAYBOOK.md
docs/AI-BATCH-USAGE.md
ai-batches/<slug>/QUESTION.md          # probes
ai-batches/<slug>/batch.json
ai-batches/<slug>/run_report.json
ai-batches/<slug>/iterations/*/
screen-maps/ai-run-<slug>/
```

## Expected workflow this chat

1. Ingest Eric’s feedback (what he saw vs what the batch intended).
2. Open the PNGs + `run_report.json`; mark each request: done correctly / missed click / wrong UI / incomplete scroll.
3. Patch `batch.json` steps if needed; reset failed requests to `"status": "pending"` (clear bad `result` if re-running) — or author the **next** probe.
4. Update `TOWER-NAV-PLAYBOOK.md` with confirmed facts only.
5. Tell Eric exactly what to Start next (same batch vs new probe).

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
