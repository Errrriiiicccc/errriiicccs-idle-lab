# Continuation handoff

For the next chat working on **Errriiiccc's Idle Lab** (`c:\DEV\Projects\Cursor\errriiicccs-idle-lab`).

**Active focus right now:** [HANDOFF-AI-BATCH-RUN.md](HANDOFF-AI-BATCH-RUN.md) — Eric runs AI Batches with **Start**; the next chat analyzes `run_report.json` + Screen Map shots from his feedback.

## What works

- Fork of tower-autoclicker as package `idle_lab`; original tree untouched.
- Clicker tab: anchor, presets, playback, hotkeys, click logger (with WAVE/SIGNAL OCR harness).
- Automations tab: Events/Collections lists, details, live queue, console, Reload/Start/Stop.
- File-driven ROIs, events, collections, `runtime.json` (`run_number`).
- Screenshot → disk; OCR (Tesseract) with observation + inference logging.
- A/B decide (pure function + sample event playing `ab choice a` / `ab choice b`).
- Priority scheduler: `minute_clip` (prio 100) hard-blocks `ocr_ab_tick` (prio 10) while recording.
- ffmpeg clips → `runs/clips/run_{n}_wave_{w}.mp4`; CSV → `runs/run_log.csv`.
- **Screen Map tab:** Start batch → Space title dialog → anchored PNG → Esc ends; browse past batches + screenshot viewer.
- **AI Batches tab:** file-backed batches with executable `steps[]`; **Start/Stop runner** clicks/scrolls/screenshots, auto-creates+links Screen Map (`ai-run-…`), writes `run_report.json`.
- Scroll: wheel + middle-drag; tab scroll positions persist until revisit/restart.
- Unit tests including AI batch runner happy path.

## Stubbed / incomplete

- Collection **execution** (Main Gameplay Loop, phase switching, stop_when) — schema + UI only.
- Tower-tuned ROIs — placeholders; click-logger ROIs are the proven path.
- Inline editing of automations / AI batch steps in the UI (files are source of truth).
- Barrier/yield mid-sequence for mouse actions (POC actions are short/atomic).
- Rich presence/template matching beyond OCR parse helpers.
- In-app auto-classification of Screen Map shots (use review chat + [SCREEN-MAP-REVIEW-PROMPT.md](SCREEN-MAP-REVIEW-PROMPT.md)).
- AI batch click coords for Tower are first-pass guesses — refine from Eric’s run feedback.

## Where things live

| Concern | Path |
| --- | --- |
| **This handoff** | `docs/HANDOFF-AI-BATCH-RUN.md` |
| AI batch usage | `docs/AI-BATCH-USAGE.md` |
| Tower nav playbook | `docs/screen-maps/TOWER-NAV-PLAYBOOK.md` |
| Active AI batch (local) | `ai-batches/menu-nav-currency-toggle-lab/` |
| Engine | `src/idle_lab/ai_batch/` (`runner.py`, `schema.py`, `store.py`, `ui.py`) |
| Screen Map | `src/idle_lab/screen_map/` |
| App shell | `src/idle_lab/app.py` |
| Vision (do not edit unless asked) | workspace `idle-lab/docs/` |

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless Eric overrides in-message.

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
git push -u origin main
```

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab

## Suggested next tasks

1. **Endgame Phase Loop:** Collections → **Endgame Phase Loop** → Walkthrough, then Automations **Start**. Children: `endgame_status_buy` + `stat_collect_30s` + `stat_broll_5m` (all enabled). Retune placeholder ROIs on a live run.
2. Narrower packs still exist: **Stat collecting** (stats/b-roll only), **Endgame Tier 1** (buys + old minute stats).
2. **Primary (AI batches):** Analyze Eric’s AI batch run feedback per [HANDOFF-AI-BATCH-RUN.md](HANDOFF-AI-BATCH-RUN.md); update playbook + `batch.json` steps.
3. Manual Screen Map smoke if needed: [SCREEN-MAP-SMOKE-TESTS.md](SCREEN-MAP-SMOKE-TESTS.md).
4. Implement collection runner: ordered children, branch resolution, loop/`stop_when: game_over`.
5. Template-match gem box (OCR presence is weak on icon-only UI).
6. Optional CSV rows on A/B ticks; extend columns backward-compatibly.
