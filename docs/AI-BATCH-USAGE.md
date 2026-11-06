# Missions — AI Information Batch Gathering

Workspace: **Missions** (formerly AI Batches).

**Probe ownership:** AI authors the question + steps; you Start; AI iterates from evidence. Contract: [PROBE-MISSIONS.md](PROBE-MISSIONS.md).

## What you do

1. **Anchor** the emulator (top chrome) — **except** offline missions (e.g. **OCR fixture bench**).
2. If chat just edited `batch.json`, hit global **Refresh** (F5) — not Restart. (**Restart** if `src/` changed.)
3. Open **Missions** → select a mission → **Start**.
4. When it finishes, tell the AI chat: *“mission X ran”* / *“probe X ran”* with:
   - `ai-batches/<slug>/batch.json` + `run_report.json`
   - for probes: also `QUESTION.md` + `iterations/*/reflection.md` (AI fills)
   - linked `screen-maps/ai-run-<slug>/` when shots exist
   - for OCR bench: also `ocr_fixture_bench.json`
   - any **Note** comments on the mission / requests / shots

The AI analyzes success/fail from those files and updates playbooks if needed.

**Stop** / chrome **Stop all** aborts between steps.

### Perception regression (minimal work)

1. Missions → **Reload** once (seeds `ocr-fixture-bench` from `examples/ai-batches/` if missing).
2. Select **OCR fixture bench** → **Start** (no Anchor).
3. Tell the chat it ran. Failures are in `run_report.json` / `ocr_fixture_bench.json`.
4. Start again anytime — `auto_rerun` re-queues the request.

## What Start does

For each pending request with `steps[]`:

1. Creates a Screen Map folder `screen-maps/ai-run-<slug>/` (once per run) and links it on the AI batch.
2. Executes steps in order: `wait` / `click` / `scroll` / `scroll_map` / `ensure_upgrade_tab` / `screenshot` / `play_preset` / `ocr_fixture_bench`.
3. Screenshots go into that Observe batch via the same `add_shot` path as the Observe workspace.
4. Marks the request **done** (or **missed** on error) with what was taken. On failure, also tries a **FAIL** screenshot into the linked batch before marking missed (live steps only).
5. Writes `ai-batches/<slug>/run_report.json`.

Prefer **`ensure_upgrade_tab`** (and similar ensure/preflight steps) before blind clicks so the runner checks UI state first.

Requests with **no** `steps` (e.g. `note`) are **skipped** for the runner — documentation is for the post-run AI chat.

Batch flags in `batch.json`:

| Flag | Meaning |
| --- | --- |
| `"genre": "probe"` | Ownership probe — see [PROBE-MISSIONS.md](PROBE-MISSIONS.md); also `mission` / `bench` |
| `"offline": true` | No Anchor required (inferred if every step is offline-capable) |
| `"auto_rerun": true` | Start re-queues done/missed runnable requests |

### Seeded probes

Missions **Reload** copies missing folders from `examples/ai-batches/`:

| Slug | Question |
| --- | --- |
| `probe-currency-toggle` | Does one HUD tap flip balances ↔ /min? |
| `probe-upgrade-tabs` | Can ensure open Attack / Defense / Utility with evidence? |
| `probe-scroll-one-row` | Does one `drag_fraction≈0.10` move ~one tile row? |

## Step schema (in `batch.json`)

Coords are **normalized fractions of the anchored window** (`nx`/`ny` 0–1), same idea as clicker presets.

```json
{"action": "wait", "ms": 500}
{"action": "click", "nx": 0.15, "ny": 0.09, "hold_ms": 50}
{"action": "scroll", "nx": 0.45, "ny": 0.70, "direction": "down", "amount": 4}
{"action": "screenshot", "title": "currency-balances"}
{"action": "play_preset", "name": "ab choice a"}
{"action": "ensure_upgrade_tab", "tab": "attack", "nx": 0.2, "ny": 0.955, "title_prefix": "attack-ensure"}
{"action": "ocr_fixture_bench", "fixture_dir": "tests/fixtures/ocr", "manifest": "manifest.json"}
{"action": "scroll_map", "nx": 0.45, "ny": 0.72, "direction": "down", "method": "drag", "amount": 1, "drag_fraction": 0.10, "hold_end_ms": 450, "settle_ms": 800, "settle_confirm_ms": 400, "max_steps": 14, "max_seek_steps": 10, "seek_top_first": true, "unchanged_threshold": 0.015, "title_prefix": "attack", "include_before": true, "roi": {"nx": 0.04, "ny": 0.55, "nw": 0.92, "nh": 0.36}}
```

`ocr_fixture_bench` is **offline** (no Anchor). It runs committed crops under `tests/fixtures/ocr/` and fails the request if any case mismatches. Seeded mission: `examples/ai-batches/ocr-fixture-bench/` → copied to `ai-batches/ocr-fixture-bench/` on Reload.

### Upgrade-list mapping pattern (preferred)

1. **`screenshot` / observe** — know what is open before clicking.
2. **`ensure_upgrade_tab`** — color-detect Attack/Defense/Utility panel; **skip the click if that tab is already open** (retapping closes it).
3. **`scroll_map` with `seek_top_first: true` and `method: "drag"`** (default):
   - **Partial drag** (`drag_fraction≈0.10`) — finger moves opposite list direction.
   - **Hold still** (`hold_end_ms`) before release — kills BlueStacks/Android fling.
   - **Settle** (`settle_ms`) → **status screenshot** → optional `settle_confirm_ms` re-grab if still moving.
   - Compare status ROI to previous status; **exit** when unchanged (top/bottom).
   - Do **not** use mouse-wheel for these lists (fling overshoots entire sections).
4. Metrics: `result.payload.scroll_maps` + `result.payload.ensures`.

Active example batch: `ai-batches/upgrade-scroll-controlled/`  
(Confirmed: `drag_fraction: 0.10` ≈ one tile row; Attack ~5 downs, Defense ~3, Utility ~2 to bottom on the lab account — see [TOWER-NAV-PLAYBOOK.md](screen-maps/TOWER-NAV-PLAYBOOK.md).)
Examples: [examples/ai-batch-spec.json](../examples/ai-batch-spec.json), [examples/ai-batch-runnable-currency.json](../examples/ai-batch-runnable-currency.json).

## AI hook

Write `ai-batches/<slug>/batch.json` (or **New batch…** then edit). Include `steps` on anything that should auto-run. **Reload** in the UI.

## After a run (for the next chat)

1. Read `run_report.json` + linked Screen Map shots.
2. Confirm what changed (e.g. currency balance ↔ `/min`).
3. If clicks missed, adjust `nx`/`ny` in `batch.json`, reset those requests to `pending`, Start again.
4. Update [screen-maps/TOWER-NAV-PLAYBOOK.md](screen-maps/TOWER-NAV-PLAYBOOK.md) when findings stick.

## Screen Map tab

Still available for **manual** exploration. Runnable AI batches do not require you to press Start batch / Space there.
