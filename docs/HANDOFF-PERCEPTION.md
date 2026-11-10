# Handoff — image → data (perception) — ACTIVE

**Status:** **paused** (2026-11-06) — feature work stopped; bad-data watch via [knowledge/ocr-trust.json](knowledge/ocr-trust.json). Resume only if watching fields keep failing or Eric asks.  
**North star:** [VISION.md](VISION.md) §§4–5 (cue stack + layered state; preference order §4.3)  
**Living field table:** [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md)  
**Old Tesseract-tweak thread (archived):** [archive/docs/HANDOFF-OCR.md](../archive/docs/HANDOFF-OCR.md)

---

## Plain-language picture

Idle Lab does **not** read the game’s memory. It takes a **picture** of a small box on the screen (an ROI), asks an OCR engine (Tesseract) “what characters are these?”, then runs that text through **rules** so we get a clean value like `11.28K` or we **leave it blank**.

| Idea | Meaning |
| --- | --- |
| **ROI** | A rectangle we defined for one HUD line (coins, diamonds, wave, …) |
| **Observation** | Raw OCR gibberish (`©)148K/min`, `1178K.`) |
| **Inference** | What we store after rules (`1.48K`, `11.28K`) |
| **Abstain** | Inference empty on purpose — better than writing `21.42m` |
| **Field contract** | Each HUD line has its own rules (gems ≠ coin rates ≠ balances) |
| **Agreement** | Multiple preps vote; threshold / majority / abstain on digit-confusion |

**Why it’s hard:** the game font is tiny, glowing, next to icons, over particles. Digits that look alike (**1/7**, **2/7**, **8/2**) get swapped. The unit `/min` leaves an `m` that used to be read as “million.”

---

## What already shipped (keep)

### Code / events / benches

| Piece | Path |
| --- | --- |
| OCR + contracts + attempt selection | `src/idle_lab/automations/ocr.py` |
| HUD balances-vs-rates PoC | `src/idle_lab/automations/hud_mode.py` |
| Stat collect atom | `automations/events/stat_collect.json` |
| ROIs | `automations/rois/{coins,diamonds,wave_tower,coins_per_min,cash_per_min,cash}_roi.json` |
| Unit parse tests | `tests/test_ocr_parse.py` |
| **Fixture regression bench** | `tests/test_ocr_fixtures.py` + `tests/fixtures/ocr/` |
| HUD mode PoC tests | `tests/test_hud_mode.py` |
| Probe script (gitignored runs/) | `runs/ocr_debug_probe.py` → `runs/ocr_debug/` |

### Typed `parse_as` (use these, not bare `currency`)

| `parse_as` | For | Contract sketch |
| --- | --- | --- |
| `currency_balance` | coins, cash | `11.28K`, `431`, … — with `KMBT`, max `999.99X` |
| `currency_rate` | \*/min | `1.68K` or plain `142`; **never** invent millions from `/min` |
| `currency_int` | diamonds | 2–4 digit ints only |
| `wave` | wave label | Prefer `Wave`/`Vave` + number |

### Selection rules landed 2026-11-06

1. **Collect all preps**, then select — no more “first equal score wins.”
2. **`currency_int`:** threshold-prep majority (fixes diamonds `816` vs `216`).
3. **`currency_rate`:** prefer threshold-backed decimal+K; cluster `2.3K`/`2.39K`; reject `M`/`B` magnitudes; recover `2390K` → `2.39K`.
4. **`currency_balance`:** prefer nostrip; reject OCR monsters like `270860K`; threshold breaks `11.28`↔`11.78` confusion.
5. **Sanitize:** `2390KM` → drop glued `M` after magnitude; rate-row trailing `M` after digits is `/min` residue.

### Fixture bench (source of truth) — run as a Mission

**Eric path (preferred):** Missions → Reload → **OCR fixture bench** → Start (no Anchor).  
Then tell the chat it ran. Artifacts: `ai-batches/ocr-fixture-bench/run_report.json` + `ocr_fixture_bench.json`.

Seeded from [`examples/ai-batches/ocr-fixture-bench/`](../examples/ai-batches/ocr-fixture-bench/). Step: `ocr_fixture_bench`. Flags: `offline` + `auto_rerun`.

Optional CI / agent check:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ocr_parse tests.test_ocr_fixtures tests.test_hud_mode -v
```

Hard cases that now pass on committed crops:

| Crop | Expect |
| --- | --- |
| `diamonds_816.png` | `816` |
| `cpm_2.39K.png` | `2.39K` (accepts `2.3K`) |
| `coins_11.28K.png` | `11.28K` |
| `coins_208.6K.png` | `208.6K` |
| `cpm_192.png` | `192` |

---

## Anticipated consumers (design for these)

| Consumer | Perception need |
| --- | --- |
| `stat_collect` CSV | Trustworthy wave/coins/diamonds/rates (once or every 30s when pooled) |
| Decide / branch actions | `if diamonds >= N`, `if coins_per_min < X` — blank must mean “don’t act” |
| Flight-deck stubs (`Screenshot + currencies`) | Fast multi-field read + mode check |
| Mission asserts | `ensure` OCR equals / HUD mode is rates |
| Currency toggle verification | `detect_hud_currency_mode` before/after preset |
| Layered screen state | `hud_currency_mode` as a first-class variable (PoC exists) |

---

## Still open (next perception work)

1. **Wire `detect_hud_currency_mode`** into runtime / schema as an action (currently PoC module + tests only).
2. **Speed:** multi-strip × many attempts is ~3–4s/field — prune never-winning preps once fixtures stay green for a week.
3. **Live CSV validation:** ask Eric to Restart → Refresh → Start `stat_collect` atom once (and/or Stat collecting molecule for interval) for ≥2 rows that match the live HUD.
4. **Icon instrument:** gem-box / tab templates (L6) — separate from numeric OCR.
5. **Engine ceiling:** if fixtures start needing ever-looser recoveries, spike EasyOCR / digit templates — don’t pretend regex fixes everything.

### Inputs needed from Eric

- **Restart** once (code under `src/` changed), then Missions → **OCR fixture bench** → Start. Say “ocr-fixture-bench ran.”
- Occasional **new ground-truth crops** when the HUD shifts — drop them in; the chat will add them to `tests/fixtures/ocr/` + manifest and you just Start the mission again.
- Live `stat_collect` CSV smoke only when we want to validate against the real HUD (still optional).

---

## Commands

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
.\.venv\Scripts\python.exe -m unittest tests.test_ocr_parse tests.test_ocr_fixtures tests.test_hud_mode -v
.\.venv\Scripts\python.exe runs/ocr_debug_probe.py
```

Use the venv — bare `python` is the Store alias on this machine.

**Chat contract:** data/ROI JSON edits → Eric hits **Refresh** (F5). Code edits under `src/` → **Restart**.
