# Hygiene

**Job:** Cut what doesn’t fit; plan the full rename; salvage useful archive docs.  
**Decisions:** [decisions.md](decisions.md)

## Current problems

- Mega Lab window + flight deck + LCO + Molecule Lab = overlapping IA.
- Disk/package names lag operator language (`events`, `collections`, `ai_batch`, `flight_deck`, `live_control`).
- FEATURES / smoke / research still carry leftover demo surface (OCR A/B, humanize loop, etc.).
- External `idle-lab/docs/` mixes gold and rot; in-repo research lanes L1–L10 are dated snapshots.
- `app.py` is a large god-shell (code smell for later waterfall — not a doc rewrite alone).

## Proposed workstreams

1. **Cut / Refine / Keep** — [CUT-REFINE-KEEP.md](CUT-REFINE-KEEP.md) **agreed**.
2. **In-repo archive** — [archive/README.md](../../../archive/README.md): deprecated docs/demos move here; app never loads them; **observations are deleted**, not attic’d.
3. **Rename plan** — settled (D11): with/after shape-first.
4. **External `idle-lab/docs`** — settled (D12): ignore by default.
5. **Doc cascade** — FEATURES/LAYOUT/USAGE sync next good chore.

## Working cut candidates (open — not settled)

| Candidate | Why it might go | Why it might stay |
| --- | --- | --- |
| Mega tabbed Lab as default home | Fights companion-first / Labs idea | Rich review still needed somewhere |
| Click-logger OCR A/B as flagship demo | Old POC energy | Still a good no-Tower harness |
| HUD `stat_collect` OCR path | Replaced by tool_export | Fallback for on-screen-only fields |
| Humanize upgrade loop as recommended demo | Not core story | Good Hands/Humanize smoke |
| Walkthrough mode | Niche | Teaching molecules |
| Inline “Add feedback” legacy | Redundant with Notes | Mild compat |
| Research “landed features” as status | Lies vs FEATURES | Historical checkpoint OK if labeled |
| Deep nested orchestration promises | Out of POC | Later |

## Fit to vision

A solid product with less surface beats a museum of every experiment.
