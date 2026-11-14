# State

**Job:** Queryable, persistent **Current State** so molecules and Hands branch on truth — not vibes.  
**Decisions:** [decisions.md](decisions.md)

## Current

- Scroll memory per tab; panel/tab helpers; object-map context for LCO.
- **Persistent state** atom via `tool_export` (Tower dump) — numbers without HUD OCR.
- Molecule Lab conditions can author gates, but runtime does not yet enforce against a shared state object (C5/C7 pending).
- Layered model described in [VISION.md §5](../../VISION.md); field tables in [knowledge/TOWER-PERCEPTION.md](../../knowledge/TOWER-PERCEPTION.md) / [TOWER-TOOL-EXPORT.md](../../knowledge/TOWER-TOOL-EXPORT.md).

## Proposed

- First-class **Current State** structure: named layers, discriminators, persistence across ticks.
- Sense ladder fills fields (export → native → pixels); unknown/abstain allowed.
- Molecules query state; Hands/UI can show it.
- Tower layers (surface, overlay, dock/tab, scroll, HUD mode, combat phase) as the first concrete schema.
- **Phase map atoms** (Atom Create kind) author the transition graph by hand: key groups → named phases → which automation atoms apply. Current State is the runtime memory those maps write into; sense cues verify/repair it.

## Fit to vision

Remember + decide. Without state, every tick rediscovers the UI.
