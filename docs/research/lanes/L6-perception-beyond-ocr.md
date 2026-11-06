# L6 — Perception beyond OCR

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P3 (feeds C1, C6; gem-box / icon presence gap)  
**Split:** primarily engine  
**Product frame:** [VISION.md](../../VISION.md) §§4–5 — perception is typed cues + layered screen state for a human-translation workbench, not “Tesseract forever.”

## 1. Restatement

Tesseract OCR is strong for HUD numbers/text and weak for **icon-only** UI (gem box, tab colors, pictograms). Docs already note template-match for gem box and `presence` parse as a weak stand-in. This lane defines a **perception stack**: selectors when possible → template match for stable icons → OCR for text → (later) stronger readers / vision-assisted authoring. Numeric fields must **abstain** rather than invent magnitudes (see VISION §9 / live `142/min` → `m` failure).

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| OpenCV `matchTemplate` (Sikuli/OculiX/ADARE) | Fast icon locate with score threshold |
| Optics / Android visual testing guides | When to use OCR vs template vs golden screenshot |
| Idle Lab `presence` + `detect_panel` | Existing partial solutions |

## 3. Extracts

### Template matching

- `TM_CCOEFF_NORMED`; threshold often ~0.8+; **tight crops**, little background.
- **Scale-sensitive** — re-capture at target DPI/resolution; don’t only lower threshold (false positives).
- Search **ROI / Region**, not full screen — faster, fewer collisions.
- Verbs: wait-until-appears with timeout; save last scene on fail.
- Multi-template for states/themes.

Sources: [OculiX vision pipeline](https://oculix.org/guides/vision-pipeline/), [ADARE CV server](https://fkie-cad.github.io/adare/architecture/cv-server.html), [iEasyClick image recognition guide](https://ieasyclick.com/blog/en/android-image-recognition-guide/).

### Method selection matrix (visual testing)

| Need | Method |
| --- | --- |
| Readable text / quantities | OCR (small ROI) |
| Known icon/badge | Template match |
| Whole layout regression | Screenshot / golden (rare for live bot) |
| Class of object, varying pose | Detector (later; heavy) |

Prefer UI tree/accessibility when available — **Idle Lab targets arbitrary GUIs / emulators**, so vision is primary; still worth remembering for native Win32 later.

Source: [LaiCai — OCR vs image matching vs screenshots](https://www.laicaiapp.com/en/blog/android-visual-testing-ocr-image-matching-screenshots/).

## 4. Idle Lab translation

| Borrow | Engine | Authoring |
| --- | --- | --- |
| `match_template` action | Crop ROI → OpenCV match → set variable `PRESENT`/`ABSENT` + score + click point | Store templates under `automations/templates/` with id |
| Threshold + score logging | Parallel to OCR raw/parsed | Console: score vs threshold |
| Multi-template | `templates: ["gem_closed.png","gem_open.png"]` | Screen Map can harvest crops |
| Color / tab detect | Keep `detect_panel` as specialized matcher | Document as non-OCR perception |
| Failure evidence | Save scene + template overlay | L4 trace hook |

**Dependency:** optional `opencv-python` (or headless) — keep OCR path working if OpenCV missing.

## 5. Conflict check

- Template libraries are binary assets — git LFS or small PNGs only; don’t dump full Screen Map batches into templates.
- Lowering similarity to “make Tower work” will false-positive; prefer re-crop.
- Scheduler: match loops with long timeouts = another blocking critical section (L2/L3).

## 6. Candidate experiments

1. Spike `match_template` on click-logger glyph (controlled) before Tower gem box.
2. Harvest gem-box crop from a Screen Map batch → template file → presence event.
3. Compare OCR `presence` vs template score on same ROI for 50 ticks; log disagreement rate.
4. Schema doc table: parse_as / match_template decision guide.

## 7. Takeaways

OCR remains the text instrument; **template match is the icon instrument**. Don’t force one tool to do both. Screen Map is the natural **template mine**.
