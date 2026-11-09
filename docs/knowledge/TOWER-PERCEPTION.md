# The Tower — perception & screen state

**Status:** living knowledge (start 2026-11-05); **perception paused 2026-11-06** (bad-data watch only)  
**Trust / auto-review watchlist:** [ocr-trust.json](ocr-trust.json)  
**Resume / ownership handoff:** [HANDOFF-PERCEPTION.md](../HANDOFF-PERCEPTION.md)  
**Product frame:** [VISION.md](../VISION.md) §§4–5 / §9  
**Code:** `src/idle_lab/automations/ocr.py`, `hud_mode.py`, `automations/rois/`, `tests/fixtures/ocr/`

This document is what later chats should **inherit** instead of rediscovering. Update it when calibrations change.

---

## 1. Field contracts (HUD text)

Idle Lab treats each OCR target as a **typed field**. Inference must pass a contract or the variable is left **blank (abstain)**. Blank is better than `21.42m`.

| Field | ROI | `parse_as` | Accepts | Rejects / notes |
| --- | --- | --- | --- | --- |
| Wave | `wave_tower_roi` | `wave` | Digits after `Wave`/`Vave` | Prefer labeled match |
| Coins (balance) | `coins_roi` | `currency_balance` | `11.28K`, `208.6K`, plain ints | With `KMBT`, max `999.99X`; prefer nostrip+threshold |
| Cash (balance) | `cash_roi` | `currency_balance` | `8.61K`, `431` | Leading `$` OK |
| Diamonds | `diamonds_roi` | `currency_int` | `488`, `546`, `816` | Threshold majority; no K/M/B/T |
| Coins/min | `coins_per_min_roi` | `currency_rate` | `1.68K`, **`142`**, `2.39K` | Threshold decimal preferred; `2390K`→`2.39K`; never `M`/`B` |
| Cash/min | `cash_per_min_roi` | `currency_rate` | `4.3K`, `1.24K`, `16.1K` | Same rate sanitizer |

### Known failure classes (handled)

| Failure | Fix |
| --- | --- |
| `142/min` → `21.42m` | Rate sanitizer; no lowercase `m` magnitude; abstain on suspicious plains |
| Diamonds `816` ↔ `216` | Threshold-prep majority for `currency_int` |
| Coins `11.28K` ↔ `11.78K` | Nostrip + threshold on digit-confusion pairs |
| Coins `208.6K` → `270860K` / `8.6K` | Reject >3 digits before `KMBT`; prefer nostrip |
| Coins/min `2.39K` unstable | `2390KM`→`2.39K`; threshold decimal cluster over `6.93K` |
| `192M` from `/min` | Strip trailing `M` on rate rows; never accept `M`/`B` rates |

### Ground-truth fixtures (committed crops)

See `tests/fixtures/ocr/manifest.json`. Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ocr_fixtures -v
```

Full-window shots (gitignored) still live under `runs/screenshots/` for the probe.

| Shot (window) | Expected |
| --- | --- |
| `stat_collect_20261105_101003_313915.png` | cash 8.61K, coins 11.28K, diamonds 488, Wave 38 |
| `stat_rates_20261105_101005_811073.png` | cash/min 4.3K, coins/min 1.68K, diamonds 488 |
| `stat_collect_20261105_100928_725283.png` | coins 9.77K, diamonds 488, Wave 34 |
| `stat_rates_20261105_100931_762325.png` | coins/min 1.48K, cash/min 3.61K |
| `stat_*_20261105_1153*.png` / `1154*.png` | coins ~7.7–7.9K, diamonds 546, coins/min **192**, Wave ~13 |
| `stat_collect_20261106_115956_918987.png` | cash 6.67K, coins 208.6K, diamonds **816**, Wave 87 |
| `stat_rates_20261106_120003_910068.png` | cash/min 16.1K, coins/min **2.39K**, diamonds 816 |

---

## 2. Layered screen state (data model)

```
surface: main_gameplay | …          (planned: route templates / title OCR)
└── overlay_options_rail: open|closed   (planned: icon row template)
└── dock_upgrades:
│     open: yes|no                      (today: detect_panel → panel_open)
│     tab: attack|defense|utility|none  (today: upgrade_tab)
│     catalog_offset: number|unknown    (LCO: known after seek-top / T; advances on R/F)
│     visible_buys[1..6]: label|?       (LCO identity; abstain beats false page-1 names)
│     scroll_px: number                 (planned: calibrated drag knowledge)
└── hud_currency_mode: balances|rates   (PoC: hud_mode.detect_hud_currency_mode)
└── run_phase: in_wave|game_over|…      (partial: game_over OCR)
```

### Today

- `detect_panel` → `panel_open`, `upgrade_tab`
- `detect_hud_currency_mode` PoC on a currency-row crop → `balances` | `rates` | `unknown`
- `stat_collect` still flips currency via preset (does not yet assert mode)

### Still to map

- Hamburger / options rail expanded vs collapsed  
- Scroll distance to each Utility upgrade row (~px calibrations)  
- Wire `hud_currency_mode` into runtime variables / schema  
- Enemy nameplate / loot list ROIs (VISION example policies)

---

## 3. Authoring rules for AI / humans

1. Pick the **narrowest** `parse_as` that fits the HUD shape.  
2. If a value is wrong, **tighten the contract or crop** — do not add a recovery that invents a different magnitude family.  
3. Leave blanks in CSV when abstaining; do not write placeholder junk.  
4. Add failing crops to `tests/fixtures/ocr/` + `manifest.json` before “fixing” OCR.  
5. When you calibrate a scroll or menu path, **append it here**.

---

## 4. Related artifacts

| Artifact | Path |
| --- | --- |
| Stat collect atom | `automations/events/stat_collect.json` |
| ROIs | `automations/rois/*_roi.json` |
| Fixture bench | `tests/fixtures/ocr/` |
| Currency toggle preset | `presets/` (name `currency toggle`) |
| Schema | `docs/automation-schema.md` |
| Vision | `docs/VISION.md` |
