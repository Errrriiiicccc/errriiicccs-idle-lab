# Molecules

**Job:** Compose and run gated policies — Molecule Lab authoring + atom/molecule runtime.  
**Decisions:** [decisions.md](decisions.md) · feature board [MOLECULE-LAB-CONDITIONALS.md](../../MOLECULE-LAB-CONDITIONALS.md)

## Current

- **Atoms** = `automations/events/*.json`; **Molecules** = `automations/collections/*.json`.
- Atom Create kind gate: **Automation** (clicks / drags / keys / OCR) or **Phase map** (key groups, phases, targets, scrolls, regions; expand-on-save → child automation atoms). Sample: `phase_map_cards`.
- Loops UI: browse, Start selected (atom once / molecule once|interval), Run pack, queue, console, Validate / Dry-run.
- **Molecule Lab** (`composer/`): drafts, selection-gated conditions (C1–C4 + C10), expand to disk; **runtime skip (C5) not done** (soft-hold vs shell reshape).
- LCO/Hands marks can be placed from Molecule Lab.
- Schema: [automation-schema.md](../../automation-schema.md).

## Proposed

- Shell direction: authoring in **expanded** Idle Lab with hotkey pocket (not peer Deck Create) — [../shell/README.md](../shell/README.md), [../shell/molecule-lab.md](../shell/molecule-lab.md) (needs rewrite pass).
- Autoclicker Lab not a separate top-level tab.
- Molecules compose Automation + Phase map atoms; gates should eventually read **Current State** (soft-hold).

## Fit to vision

Translate → habits. Molecules are the durable policy language.
