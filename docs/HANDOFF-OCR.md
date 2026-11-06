# Handoff — OCR tightening (Idle Lab)

> **Historical only.** Current pause/resume brain-dump: [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md).  
> Vision: [VISION.md](VISION.md). Field table: [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md).  
> Remember: `/min` → `m` million was fixed in contracts; diamonds `816`↔`216` and unstable coins/min remain.

Paste the prompt below only for archaeology of the old “tighten Tesseract recoveries” thread.

**Chat contract:** data/ROI JSON edits → Eric hits **Refresh** (F5). Code edits under `src/` → **Restart**.

---

## Prompt (copy from here)

```
You are continuing OCR refinement for Errriiiccc's Idle Lab at:
c:\DEV\Projects\Cursor\errriiicccs-idle-lab

## Goal
Make HUD OCR (wave, coins, diamonds, coins/min, cash/min) trustworthy enough for automation decisions. Do not redesign the app shell — OCR + ROI only unless a tiny debug hook is needed.

## Ground truth screenshots (593×1028)
- runs/screenshots/stat_collect_20261105_101003_313915.png  → cash $8.61K, coins 11.28K, diamonds 488, Wave 38
- runs/screenshots/stat_rates_20261105_101005_811073.png    → cash/min $4.3K/min, coins/min 1.68K/min, diamonds 488
- runs/screenshots/stat_collect_20261105_100928_725283.png  → coins 9.77K, diamonds 488, Wave 34
- runs/screenshots/stat_rates_20261105_100931_762325.png    → coins/min 1.48K/min, cash/min $3.61K/min

CSV: runs/stat_collect.csv
Probe: .\.venv\Scripts\python.exe runs/ocr_debug_probe.py  → writes runs/ocr_debug/
Tests: .\.venv\Scripts\python.exe -m unittest tests.test_ocr_parse -v
(Use the venv — bare `python` is the Store alias on this machine.)

Atom: automations/events/stat_collect.json
ROIs: automations/rois/{coins,diamonds,wave_tower,coins_per_min,cash_per_min,cash}_roi.json
Code: src/idle_lab/automations/ocr.py

## Latest probe results (after this session — start here, don't revert blindly)
| field | truth | probe |
|---|---|---|
| wave | 38 / 34 | 38 / 34 ✓ |
| diamonds | 488 | 488 ✓ |
| cash | 8.61K | 8.61K ✓ |
| cash/min | 4.3K / 3.61K | 4.3K / 3.61K ✓ |
| coins/min | 1.68K / 1.48K | 1.68K / 1.48K ✓ |
| coins (earlier) | 9.77K | 9.77K ✓ |
| coins (10:10) | 11.28K | 11.78K ✗ (2↔7 digit confusion) |

## What already works (keep)
1. Multi-strip search (0 / 0.15 / 0.22): diamonds need ~0.15; cash/coins usually win at 0. Single fixed strip was destroying leading digits (8.61→3.61, 11.28→128).
2. Scale 3 + scale 4 currency attempts (scale 3 recovers 9.77K).
3. Parser recoveries in parse_currency:
   - ".168K" / "168K/min" → 1.68K (leading-1 three-digit + /min only, so 294K/min stays)
   - "11 68K/min" → 1.68K (icon-duplicated leading 1)
   - balance "977K"/"1128K" → 9.77K/11.28K (suffix required so diamonds 488 untouched)
   - round >2 decimal places (11.278K → 11.28K)
4. Scoring: empty inference −100; prefer HUD `\d.\d{1,2}[KMBT]`; reward plain 3+ digit ints (diamonds); penalize 0.xxK.
5. Mild ROI left nudge on coins / coins_per_min (nx≈0.040) so leading digits aren't clipped.
6. Unit tests in tests/test_ocr_parse.py cover the recoveries above.

## Remaining job
1. Fix coins 11.28K reading as 11.78K on the 10:10 balances shot (Tesseract 2↔7). Prefer prep/threshold/sharpen/whitelist tweaks or attempt ranking — not looser regex that re-breaks diamonds/rates.
2. Re-run probe until BOTH balance shots hit coins correctly in the same pass.
3. Ask Eric to Restart, Refresh, Loops → Atoms → Stat collect → Start selected (once) or Molecules → Stat collecting for interval → confirm CSV rows match the live HUD.
4. Optional: speed up ocr_field (multi-strip × many attempts is ~3–4s/field); prune attempts that never win once accuracy is stable.
5. Optional: per-ROI strip hint in ROI JSON if multi-strip stays expensive.

## Constraints
- Screen OCR only (Tesseract). No game injection.
- Files are source of truth for ROIs.
- Optional OpenCV is for match_template, not required for HUD text.
- Local commits OK; git push only outside Mon–Fri 09:00–17:00 Eastern unless Eric overrides.

## Success bar
Probe: all ground-truth rows above match (coins 11.28K exact or clearly 11.2xK, not 11.7xK).
Live: ≥2 consecutive stat_collect CSV rows where wave/coins/diamonds/coins_per_min/cash_per_min match the screenshot within normal OCR tolerance. No order-of-magnitude hallucinations.
```
