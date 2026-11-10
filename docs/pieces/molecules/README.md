# Molecules

**Job:** Compose and run gated policies — Molecule Lab authoring + atom/molecule runtime.  
**Decisions:** [decisions.md](decisions.md) · feature board [MOLECULE-LAB-CONDITIONALS.md](../../MOLECULE-LAB-CONDITIONALS.md)

## Current

- **Atoms** = `automations/events/*.json`; **Molecules** = `automations/collections/*.json`.
- Loops UI: browse, Start selected (atom once / molecule once|interval), Run pack, queue, console, Validate / Dry-run.
- **Molecule Lab** (`composer/`): drafts, selection-gated conditions (C1–C4 + C10), expand to disk; **runtime skip (C5) not done**.
- LCO/Hands marks can be placed from Molecule Lab.
- Schema: [automation-schema.md](../../automation-schema.md).

## Proposed

- Shell plan: [../shell/molecule-lab.md](../shell/molecule-lab.md) — **Atom tab** (visual create on Deck) + Molecule compose/Trial; Loops dissolves; elevated queue; Walkthrough + Notes; Stop → Deactivate.
- Autoclicker Lab not a separate top-level tab.

## Fit to vision

Translate → habits. Molecules are the durable policy language.
