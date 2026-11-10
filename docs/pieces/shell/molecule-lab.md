# Molecule Lab

**Parent:** [README.md](README.md) · piece: [../molecules/README.md](../molecules/README.md)

## Settled (high level)

| Topic | Decision |
| --- | --- |
| Idle Lab | Full Lab with flowing focus; embedded wrap |
| Flight Deck | Lightweight full Lab; Esc → Deck |
| Tabs inside ML | At least **Atom** + **Molecule** (compose/test) — Autoclicker Lab **dissolves into Atom authoring** |
| Persist | Write atoms/molecules to disk; global Refresh |
| Loops tab | Dissolves into ML (prior disposition table still holds) |
| Console | Shared object; docked bottom when ML open; floating on Deck |
| Shape-first | UI skeleton before full wiring |
| Library org / mode names | Parked for in-app later |

## Why Atom tab (settled direction)

Creating a basic atomic loop is too hard today. Observation alone shouldn’t be the only path. Users need **agency** to build simple loops visually — same energy as old Autoclicker / LOL marks — then compose those atoms into molecules.

**Autoclicker Lab** as a separate Idle Lab tab is **withdrawn** for now: record/play of clicks becomes **Atom creation** inside Molecule Lab (name: **Autoclicker Lab** may remain as flavor copy inside Atom tab, but not a sibling top-level Lab).

---

## Atom authoring — Flight Deck + on-screen queue (settled direction)

### Enter

From Molecule Lab (Idle Lab or floating from Deck **M**) → Atom create/edit → **Atom Create mode** on Deck (no accordion). Esc exit **entry-dependent** (like LOL). Save on exit.

### C — Create (click path locked; others parallel)

1. **C** → queue UI (e.g. `1: Single Click`) + centered **#** click indicator on game.  
2. **Mouse drag** indicator to target.

| Key path | Event | Glyph |
| --- | --- | --- |
| Click | Circle + queue # |
| Drag | Two circles, same #, arrow |
| Keyboard | Keyboard queue box + `N: Key` rows |
| OCR | Region + #; needs-review warn |

Exact C→digit map still fine; primary click UX is drag-place, not digit-arm.

### E — Edit

- **E** → queue **focus** (highlight starts at first event); marks show selection.  
- **R** / **F** — move event up / down in queue.  
- **W** / **S** — previous / next event.  
- Event-specific chords (single/spam, …).  
- **Esc** — leave edit mode (still in creator until outer Esc/exit).

#### Click edits

- Single / Spam  
- If Spam: Interval (e.g. 10ms); Timing **or** Click #; then Time to hold-spam **or** # of clicks  

#### Keyboard edits

- Key  
- Single / Spam (same spam timing model as click)  

#### Drag edits

- Mouse speed: Slow / Medium / Fast  
- Pause on end: Yes/No → if Yes, duration  

#### OCR edits (hardest UX — expect iteration)

- Type: Text / Color / Shape / (TBD)  
- **Text:** guided constraints toward regex (length, decimal, symbols before/after, multiline?, known set vs dynamic) so AI/runtime can interpret results and attach functions  
- **Color:** color-picker; map colors → states (e.g. buy box maxed / can’t afford / can afford)  
- **Shape:** richer regions/pieces inside the OCR area (more complex than flat color)  

On create, prompt for enough OCR info; unfinished OCR → **needs review** flag on the atom.

### Relationship to agency

Goal: **simple loops first**, then molecules from those atoms — not “only Observation → hope the AI invents clicks.”

---

## Molecule side (unchanged from prior settle)

- Flowing full composer; Draft↔Trial names parked  
- Queue elevated (conditionals visible → queued/skipped)  
- Walkthrough + Notes kept; Start-all cut; Stop → Deactivate  
- LOL marks for molecule placement still valid; Atom overlay is the **authoring** path for building atoms themselves  

---

## Overlay architecture (settled)

- **Atom Create/Edit** is a **distinct mode** from **LOL** (not the same mode switch).
- Both share the **same principles and shared overlay objects** — not hard-coded one-off UIs.
  - Queue visibility while testing atoms  
  - Hold **D** → descriptions (single vs autoclick/spam, intervals, drag speed, OCR definitions, …)  
  - Marks, numbers, regions, keyboard queue chrome as reusable primitives  
- Any future game overlay (LOL, Atom stage, …) builds on that shared layer.

## Save / edit (settled)

- Creator **≡** editor — reopen any atom later in the same flow.
- **Save on exit** from creator/editor (leaving the mode persists the atom).

## OCR needs-review (settled)

- **Warn only.** User decides when to clear needs-review; not a hard block.

## Compatibility (settled direction)

- **Every atom** we already have (and new ones) should be **representable** in this Atom creator structure — visual queue + event types (click/drag/key/OCR/…). No forever “JSON-only ghosts” that the creator can’t show.

## Legacy Bench presets (plain English)

Old **Bench** saved **click macros** as `presets/*.json` (timed click lists) — parallel to atoms, not the same files. Open whether we **migrate** those presets into atoms later, or leave them until a rename pass. Not blocking Atom Create design.

## Trial + creators (parked — revisit later)

Trialing atoms/molecules belongs **inside Molecule Lab**, cohesive with Atom creator and Molecule creator — easy to understand as one Lab. Exact IA (tabs/modes/labels) **revisit later**; don’t block Flight Deck.

## Still open / parked

| ID | Status |
| --- | --- |
| A3/A6 | Parked — Trial + creator cohesion later |
| A4 | Parked — Bench presets migrate not important now |

## Prior Loops disposition

See git history / earlier sections if needed; summary: library in ML, Trial run/dry-run/walkthrough, console shared, Validate on save, Deck leaves → FD dive.
