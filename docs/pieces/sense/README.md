# Sense

**Job:** Turn the target into typed data — preferring truth over guesswork.  
**Decisions:** [decisions.md](decisions.md) · ladder in [VISION.md §4.3](../../VISION.md)

## Current

- ROI capture, Tesseract OCR, template match (optional OpenCV), panel/color cues.
- HUD OCR **paused** for Tower numbers; **tool_export** preferred.
- Bad-data watch: [knowledge/ocr-trust.json](../../knowledge/ocr-trust.json).
- LCO buy-detect / nameplate OCR still used for some live cues.

## Proposed

- Enforce the ladder everywhere: **structured source → title-native hooks → pixels/OCR/atoms**.
- Expand export coverage; research native hooks per title (Tower macros N/A; browsers/DOM later).
- Keep OCR as abstaining fallback for on-screen-only cues and discriminators exports cannot see.
- Feed Current State ([../state/](../state/README.md)); stop inventing magnitudes.

## Fit to vision

Push every application to its legitimate limits. Inefficient to OCR a number the game already wrote to disk.
