# Automations schema (v1)

JSON files under `automations/`. Reload in the Automations tab picks up changes. Bad files are skipped and reported in the console.

## Layout

```
automations/
  runtime.json          # run_number, etc.
  rois/*.json
  events/*.json
  collections/*.json
```

## ROI

Normalized rectangle inside the anchored window (same philosophy as preset `nx`/`ny`).

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique |
| `version` | 1 | Required conceptually; default 1 |
| `nx`, `ny` | number | Top-left fraction |
| `nw`, `nh` | number | Size fractions; must stay in [0,1] |
| `notes` | string | Optional |

## Event

Schedulable unit.

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `title` | string | |
| `version` | 1 | |
| `enabled` | bool | default true |
| `priority` | int | Higher wins; recording demo uses 100 vs A/B 10 |
| `timing` | object | POC: `{"type":"interval","every_ms":N}` |
| `actions` | array | Non-empty ordered steps |
| `description` | string | Optional plain-language summary for Basic UI |
| `notes` | string | Optional author notes (shown in Detailed) |

### Action types

Each action may include optional `description` (plain sentence for Basic UI).

- `screenshot` — `{ "prefix": "ab" }`
- `ocr` — `{ "roi": "signal_roi", "variable": "signal", "parse_as": "signal"|"wave"|"raw"|"currency"|"game_over"|"presence" }`
  - `currency` — first Tower-ish quantity (`12.5B`, `1.2e9`, …)
  - `game_over` — `GAME_OVER` or `RUNNING` from dialog keywords
  - `presence` — `PRESENT` if ROI OCR has non-trivial text, else `ABSENT` (gem-box piggyback)
- `decide` — `{ "variable", "match_a", "mode", "explain_a", "explain_b", "on_a": [...], "on_b": [...] }`
- `play_preset` / `mouse` — `{ "preset": "ab choice a" }` (preset `name` from `presets/`). Playback uses the Clicker **Humanize** setting (default Medium).
- `record_clip` — `{ "duration_s": 10 }` → `runs/clips/run_{run}_wave_{wave}.mp4`
- `csv_append` — `{ "path": "run_log.csv", "fields": ["coins", …] }` under `runs/`
  - Always writes `datetime`, `run_number`, `wave_number`
  - Optional `fields` pulls extra columns from runtime variables (e.g. endgame stats)
- `log` — `{ "message": "…{wave_number}…", "level": "info" }`
- `set_variable` — `{ "name": "phase", "value": "begin" }`
- `wait` — `{ "ms": 400 }`
- `click` — `{ "target": "health"|"damage"|"attack"|"defense"|"utility" }` or `{ "nx", "ny" }`
- `detect_panel` — observe upgrade panel open/closed + tab color; sets `panel_open`, `upgrade_tab`, `panel_reason`
- `ensure_upgrade_tab` — `{ "tab": "attack"|"defense"|"utility" }` observe first; click only if needed (retap closes)
- `seek_list_top` — `{ "look_for": "Health"|"Damage" }` OCR first card; controlled drag up until match or unchanged

UI **Basic** mode shows plain descriptions + branch contention. **Detailed** mode adds ids, output paths, and nested path steps.

## Collection

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `title` | string | |
| `children` | string[] | Event or collection ids in order |
| `branch_variable` | string | default `phase` |
| `branches` | object | value → child id |
| `loop` | bool | |
| `stop_when` | string\|null | Stub for later (e.g. `game_over`) |
| `description` | string | Optional plain-language summary for Basic UI |
| `notes` | string | Optional |

`resolve_branch(collection, variables)` maps `variables[branch_variable]` onto `branches` (case-insensitive). Full Main Gameplay Loop execution is out of POC scope; the UI and schema express it.

## Runtime

`automations/runtime.json`:

```json
{ "version": 1, "run_number": 1 }
```

## CSV

`runs/run_log.csv` columns: `datetime`, `run_number`, `wave_number`.

`runs/endgame_stats.csv` (Endgame Tier 1): base columns plus `coins`, `coins_per_min`, `cash_per_min`, `diamonds`, `game_over`.

## Sample collection — Endgame Phase Loop (combined)

| File | Role |
| --- | --- |
| `collections/endgame_phase_loop.json` | **Start this pack** — buys + 30s stats + 5-min b-roll |
| `events/endgame_status_buy.json` | ~15s: detect_panel → game-over/gem → ensure/seek/buy → **leave open** |
| `events/stat_collect_30s.json` | Every 30s → `runs/stat_collect.csv` |
| `events/stat_broll_5m.json` | Every 5 min → 20s clip + `runs/stat_broll.csv` |

`collections/endgame_tier1.json` and `collections/stat_collecting.json` remain as narrower packs. Runtime still keys off each event’s `enabled` flag (not which collection is selected).

## Sample collection — Stat collecting

| File | Role |
| --- | --- |
| `collections/stat_collecting.json` | Title **Stat collecting** |
| `events/stat_collect_30s.json` | Every 30s → `runs/stat_collect.csv` |
| `events/stat_broll_5m.json` | Every 5 min → 20s clip + `runs/stat_broll.csv` (priority 100) |
| Stat columns | `datetime`, `run_number`, `wave_number`, `coins`, `coins_per_min`, `cash_per_min`, `diamonds`, `panel_open`, `upgrade_tab` |
| B-roll columns | `datetime`, `run_number`, `wave_number`, `clip_name`, `clip_duration_s`, `clip_kind`, `last_clip`, `panel_open`, `upgrade_tab` |

Does **not** click Attack/Defense/Utility. Currency toggle is top-HUD only. `record_clip` may set `kind` (e.g. `broll`) so filenames include a timestamp and do not overwrite.
