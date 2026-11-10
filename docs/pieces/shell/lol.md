# Live Overlay Lab (LOL)

**Was:** Live Control Overlay (LCO).  
**Parent:** [README.md](README.md) · hands: [../hands/README.md](../hands/README.md) · shared overlay: [molecule-lab.md](molecule-lab.md) (Atom Create)

## Settled

| Topic | Decision |
| --- | --- |
| Name | **Live Overlay Lab (LOL)** |
| Idle Lab tab | Interactive **map** — tree/list + miniature that follows highlight |
| Hotkeys | Remap on map; conflict warnings |
| Marks | Molecule marks movable when reasonable; fixed region controls not |
| Start live | LOL tab or Flight Deck only; Anchor required |
| Keep from LCO | Hold D describe, stay-in-mode, fire modes, Esc exit, etc. |
| Live takeover | Idle Lab hides; Flight Deck up; Esc → entry surface |

## Shared overlay layer (settled)

LOL is **not** a one-off hard-coded overlay. It shares **primitives and principles** with **Atom Create/Edit** (distinct mode, same foundation):

- Queue / numbered marks  
- Hold **D** descriptions  
- Region / circle / arrow / keyboard-queue chrome  

Implementation must factor shared objects so LOL UX improvements (and Atom UX) don’t fork.

## Open

Soft: tree grouping; miniature = live shot vs drawn — implement-time OK.
