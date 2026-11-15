# Continuation handoff

**Errriiiccc's Idle Lab** — `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`

**North star:** [VISION.md](VISION.md)  
**Cascade:** [README.md](README.md) · [../AGENTS.md](../AGENTS.md)  
**Redesign:** [pieces/README.md](pieces/README.md) · shell [pieces/shell/](pieces/shell/README.md) · feel [pieces/shell/FEEL.md](pieces/shell/FEEL.md) · [archive/README.md](../archive/README.md)  
**Target vs code:** [FEATURES.md](FEATURES.md)

## Active focus (2026-11-15)

**Idle Lab only** — expanded desk + collapsed takeover. Peer Flight Deck is **not** a user surface.

| Costume | When |
| --- | --- |
| **Expanded** | Normal desk — left Labs tree + hotkey pocket + action pane |
| **Collapsed** | LOL live or Observation running (also Preview collapsed) |

`` ` `` = **Deactivate = Stop all**. Atom Create runs **in expanded Lab** (Molecule Lab · Atom → Create Atom); pocket shows kind/create leaves. Peer `FlightDeckWindow` stays withdrawn for keymap helpers only.

### Smoke (Restart)

1. No separate Flight Deck window; tray has **Open Lab** only (no Show Flight Deck).
2. Tree → Labs work in the action pane; pocket tracks focus.
3. Molecule Lab · Atom → **Create Atom** — stays expanded; pocket shows 1/2 kind gate; Esc returns to Atom pane.
4. LOL **Start live** → Lab **collapses**; Esc → **expanded**.
5. Observation start → collapsed; stop → expanded.
6. Skin menu still paints Type → Bracket (etc.).

### Soft hold (next)

- LOL Esc confirm overlay on anchored glass  
- Live pocket maps beyond Create stubs  
- Keep `flight_deck/` as withdrawn keymap host for now (do **not** delete the package yet); sticky-seal so chrome/geometry cannot rematerialize the peer window  
- Later: move keymap ownership out of `FlightDeckWindow`, then delete the peer Toplevel  
- Deep pane widgets fully skinned  

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data → Refresh; code → Restart.  
**Test:** [HARNESS.md](HARNESS.md) · [`lab-context.json`](../lab-context.json).

## What landed recently

- Peer Deck removed from UX — expanded/collapsed Idle Lab only; Atom Create in-Lab  
- Costume skeleton + Type → Bracket skins  
- Phase map Atom Create + Cards sample  

## Soft parked

- Current State + C5 · package rename · in-app AI dispatch  

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless overridden.

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab
