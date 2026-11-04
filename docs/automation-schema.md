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
- `ocr` — `{ "roi": "signal_roi", "variable": "signal", "parse_as": "signal"|"wave"|"raw" }`
- `decide` — `{ "variable", "match_a", "mode", "explain_a", "explain_b", "on_a": [...], "on_b": [...] }`
- `play_preset` / `mouse` — `{ "preset": "ab choice a" }` (preset `name` from `presets/`)
- `record_clip` — `{ "duration_s": 10 }` → `runs/clips/run_{run}_wave_{wave}.mp4`
- `csv_append` — `{ "path": "run_log.csv" }` under `runs/`
- `log` — `{ "message": "…{wave_number}…", "level": "info" }`
- `set_variable` — `{ "name": "phase", "value": "begin" }`

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
