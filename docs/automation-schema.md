# Automations schema (v1)

JSON files under `automations/`. Reload in the Automations tab picks up changes. Bad files are skipped and reported in the console.

## Layout

```
automations/
  runtime.json          # run_number, etc.
  taxonomy.json         # shared flight deck + Loops folder catalog
  rois/*.json
  events/*.json
  collections/*.json
```

**Taxonomy** (`taxonomy.json`): Lab Loops browse — virtual folders with `key` / `label` / optional `description`, leaves with `action` or `ref`. Browse **Atoms** (`loops.events`) / **Molecules** (`loops.collections`).

**Flight deck** (`flight_deck.json`): separate accordion catalog — letter menus, digit leaves, max two keys deep. Not the Lab taxonomy tree.

**Atoms vs molecules:** Events on disk are **atoms** (reusable procedures). Collections are **molecules** (compositions). Start selected on an atom runs it **once** (no interval wait). Molecule `run` chooses Start behavior (below).

## ROI

Normalized rectangle inside the anchored window (same philosophy as preset `nx`/`ny`).

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique |
| `version` | 1 | Required conceptually; default 1 |
| `nx`, `ny` | number | Top-left fraction |
| `nw`, `nh` | number | Size fractions; must stay in [0,1] |
| `notes` | string | Optional |

## Event (atom)

Reusable procedure. **Start selected** runs `actions` once. `timing` / `enabled` apply when the atom is in an **interval pool** (Start all enabled, or a molecule with `run: "interval"`).

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `title` | string | |
| `version` | 1 | |
| `enabled` | bool | default true — gates interval pool membership |
| `priority` | int | Higher wins; recording demo uses 100 vs A/B 10 |
| `timing` | object | POC: `{"type":"interval","every_ms":N}` (used when pooled) |
| `actions` | array | Non-empty ordered steps |
| `description` | string | Optional plain-language summary for Basic UI |
| `notes` | string | Optional author notes (shown in Detailed) |

### Action types

Each action may include optional `description` (plain sentence for Basic UI).

- `screenshot` — `{ "prefix": "ab" }`
- `ocr` — `{ "roi": "signal_roi", "variable": "signal", "parse_as": "…" }`
  - `parse_as` values (typed field contracts — empty inference = abstain):
    - `wave` | `signal` | `raw` | `game_over` | `presence`
    - `currency` — legacy general quantity (sanitizes `/min`→`m`; prefer typed forms)
    - `currency_balance` — coin/cash balances (`11.28K`, `431`)
    - `currency_rate` — per-minute rates (`1.68K`, `142`); never treat `/min` as million
    - `currency_int` — plain ints only (`488` diamonds); rejects K/M/B/T tokens
  - `game_over` — `GAME_OVER` or `RUNNING` from dialog keywords
  - `presence` — `PRESENT` if ROI OCR has non-trivial text, else `ABSENT` (gem-box piggyback)
  - See [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md) for HUD field contracts + layered state.
- `decide` — `{ "variable", "match_a", "mode", "explain_a", "explain_b", "on_a": [...], "on_b": [...] }`
- `play_preset` / `mouse` — `{ "preset": "ab choice a" }` (preset `name` from `presets/`). Playback uses the Clicker **Humanize** setting (default Medium).
- `record_clip` — `{ "duration_s": 10 }` → `runs/clips/run_{run}_wave_{wave}.mp4`
- `csv_append` — `{ "path": "run_log.csv", "fields": ["coins", …] }` under `runs/`
  - Always writes `datetime`, `run_number`, `wave_number`
  - Optional `fields` pulls extra columns from runtime variables (e.g. endgame stats)
- `log` — `{ "message": "…{wave_number}…", "level": "info" }`
- `set_variable` — `{ "name": "phase", "value": "begin" }`
- `wait` — `{ "ms": 400 }` (interruptible by Stop)
- `wait_until` — poll until ready: `{ "check": "variable"|"ocr"|"panel"|"template", "variable"?, "roi"?, "equals"?, "template"?, "timeout_ms": 5000, "poll_ms": 200 }`
- `match_template` — icon presence via OpenCV (optional dep): `{ "template": "gem_closed", "roi"?, "threshold": 0.85, "variable": "gem", "click": false }` — templates in `automations/templates/`
- `click` — `{ "target": "health"|"damage"|"attack"|"defense"|"utility" }` or `{ "nx", "ny" }`
- `detect_panel` — observe upgrade panel open/closed + tab color; sets `panel_open`, `upgrade_tab`, `panel_reason`
- `ensure_upgrade_tab` — `{ "tab": "attack"|"defense"|"utility" }` observe first; click only if needed (retap closes)
- `seek_list_top` — `{ "look_for": "Health"|"Damage" }` OCR first card; controlled drag up until match or unchanged
- `scroll_list` — `{ "direction": "up"|"down", "rows": N }` tab-agnostic playbook drag (~0.10 per row). Prefer shared scroll atoms over duplicating coords per tab.

### Event overdue_policy (optional)

`run_when_free` (default) | `skip` | `run_once_catchup` — what to do when a tick was due while the worker was busy.


UI **Basic** mode shows plain descriptions + branch contention. **Detailed** mode adds ids, output paths, and nested path steps.

## Collection (molecule)

Composition of atoms (and nested molecules).

| Field | Type | Notes |
| --- | --- | --- |
| `id`, `title` | string | |
| `children` | string[] | Event or collection ids in order |
| `run` | `"once"` \| `"interval"` | default `"interval"` if omitted. **once** = serial `_run_event` pass; **interval** = Start child atoms on the scheduler |
| `branch_variable` | string | default `phase` |
| `branches` | object | value → child id |
| `loop` | bool | honored for `run: "once"` serial runner |
| `stop_when` | string\|null | e.g. `game_over` (once runner) |
| `description` | string | Optional plain-language summary for Basic UI |
| `notes` | string | Optional |

`resolve_branch(collection, variables)` maps `variables[branch_variable]` onto `branches` (case-insensitive).

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
| `collections/endgame_phase_loop.json` | Interval molecule — buys + stats + b-roll |
| `events/endgame_status_buy.json` | Atom: detect_panel → gem → ensure/seek/buy → leave open |
| `events/stat_collect.json` | Atom: one CSV row (Start once) or every 30s when pooled |
| `events/stat_broll_5m.json` | Atom: 20s clip + CSV when pooled |
| `events/list_scroll_down_1.json` / `list_scroll_up_1.json` | Shared scroll atoms |
| `collections/scroll_probe_once.json` | Once molecule: ensure Attack → scroll down 1 |

## Sample molecule — Stat collecting

| File | Role |
| --- | --- |
| `collections/stat_collecting.json` | `run: "interval"` — pools `stat_collect` + `stat_broll_5m` |
| `events/stat_collect.json` | Start selected → one CSV row **now** |
| `events/stat_broll_5m.json` | B-roll atom (priority 100) |
| Stat columns | `datetime`, `run_number`, `wave_number`, `coins`, `coins_per_min`, `cash_per_min`, `diamonds`, `panel_open`, `upgrade_tab` |
| B-roll columns | `datetime`, `run_number`, `wave_number`, `clip_name`, `clip_duration_s`, `clip_kind`, `last_clip`, `panel_open`, `upgrade_tab` |

Does **not** click Attack/Defense/Utility. Currency toggle is top-HUD only. `record_clip` may set `kind` (e.g. `broll`) so filenames include a timestamp and do not overwrite.
