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
| **Expanded** | Left **Labs tree** (roots + leaves) · hotkey pocket · **one** middle pane |
| **Collapsed** | LOL live or Observation running (also Preview collapsed) |

`` ` `` = **Deactivate = Stop all**. Atom Create runs **in expanded Lab** (Molecule Lab → Atom → Create Atom). **No lab tabs in the middle** — Atom / Molecule / Trial and Observation User / AI mission live on the left rail. Middle desk lazy-mounts the active leaf. Peer `FlightDeckWindow` stays withdrawn for keymap helpers only.

### Smoke (Restart)

1. No separate Flight Deck window; tray has **Open Lab** only (no Show Flight Deck).
2. Window **X** hides to tray (no zombie taskbar button); tray → **Open Lab** restores; tray → **Quit** exits.
3. Cold boot should not sit ~5s on tray before first paint (tray starts after paint). Resize/move the windowed Lab → Restart keeps size/position (maximized vs restored too). Drag-resize parks the heavy desk until the drag settles (CTk layout cost).
4. Left rail opens Molecule Lab → Atom / Molecule / Trial leaves; middle shows that leaf only (no inner tab strip).
5. Observation Lab → User / AI mission on the left; middle follows.
6. Molecule Lab · Atom → **Create Atom** — stays expanded; pocket shows 1/2 kind gate; Esc returns to Atom pane.
7. LOL **Start live** → Lab **collapses**; Esc → **expanded**.
8. Observation start → collapsed; stop → expanded.
9. Skin menu paints Type → Bracket across shell **and** middle lab panes / collapsed face.

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
