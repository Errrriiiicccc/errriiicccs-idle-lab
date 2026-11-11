# Flight Deck

**Parent:** [README.md](README.md) · Atom Create detail also in [molecule-lab.md](molecule-lab.md)

## Settled

### Activation

- Starts **deactivated**; only `` ` `` listened → Activate.
- When activated: clear affordance of which hotkeys are live (Deck and/or overlay).

### Navigation

- Accordion **redesigned from scratch**; **X** collapses; **hold D** = descriptions for non-obvious hotkeys (e.g. click interval → “How much time passes between each click”). Hold D is always available in modes that use the shared overlay layer.
- Reaching a **mode** abandons prior menu hotkeys.

| Mode | Deck listens |
| --- | --- |
| Menu (no mode) | Accordion, X, hold D, `` ` ``, Esc peel |
| **LOL** | Esc + `` ` `` (+ overlay needs) |
| **Molecule Lab** floating window | Esc + `` ` `` |
| **Observation Lab** floating window | Esc + `` ` `` (assumed same pattern) |
| **Atom Create/Edit** | Accordion create keymap (same grammar); Esc save/exit |
| Generic run | Deactivate + queue/status + console + mode-unique keys |

### Lightweight / floating Labs

**Keep.** Experienced users open ML / OL (etc.) as floating windows from Deck without Idle Lab click overhead. Esc → Deck.

### Top-level letter map (settled direction — deepen accordion)

| Key | Action |
| --- | --- |
| **L** | Accordion: Start · Toggle Console · Console Verbosity |
| **M** | Accordion: Molecule Lab (float) · Atom Lab (Atom Create) |
| **O** | Observation Lab (floating) — accordion depth later |
| **I** | Accordion: Start (closes Flight Deck → Idle Lab) |
| **S** | Accordion: Open Settings · Set Deactivate Key · Boot Preferences |
| **X** | Collapse menu |
| hold **D** | Describe |
| `` ` `` | Deactivate |

Idle Lab ↔ Flight Deck are exclusive. Idle Lab chrome always shows **Open Flight Deck** `(closes Idle Lab)`.

Menu letters are abandoned when a Lab mode owns the surface. **Atom Create** swaps in a create keymap but keeps accordion navigation.

---

## Atom Create / Edit on Deck (settled direction)

Entry-dependent exit like LOL (Esc → Idle Lab Atom path if entered from Idle Lab; → Deck menu if entered from Deck). Save on exit. Creator ≡ editor.

### C — Create (example: click)

1. Press **C** → visual **queue** appears (e.g. shows `1: Single Click`).
2. On the game, a **click indicator** appears (center initially) with **1** inside.
3. User **mouse drag** moves the indicator to the click target (not “arm then click to place” as the primary story).

Same spirit for drag/key/OCR create flows (queue line + on-screen glyph); detail as we go.

### E — Edit

1. Press **E** → **queue takes focus** (indicator highlights an event; starts at **first**).
2. Deck shows edit chords, including:
   - **W** — select previous event  
   - **S** — select next event  
   - **R** — move event **up** in queue  
   - **F** — move event **down** in queue  
   - Event-specific actions (single/spam, intervals, drag speed, OCR fields, …)  
   - **Esc** — exit edit mode  
3. On-screen marks reflect selection (orange / focus from earlier plan).

### Hold D

Always present in these modes: describes hotkeys / fields that aren’t self-explanatory (intervals, spam modes, OCR params, …).

---

## Create gestures by type (continuing)

### Click (settled)

**C** (→ click type) → queue shows `N: Single Click` → centered **#** circle → **drag** to target.

### Drag (settled)

1. **C** → drag type → queue `N: Drag`.  
2. Two handles appear (start + end), same **N**, arrow between.  
3. Drag each handle into place (start then end, or either order).  
4. Default speed Medium; refine under **E**.

### Keyboard (settled)

1. **C** → keyboard type → keyboard queue box appears (if first key event).  
2. Next physical keypress on the real keyboard becomes `N: <Key>` in the box (capture one key).  
3. Optional: click/drag the queue box position on screen so it doesn’t cover the game.  
4. Spam/single under **E**.

### OCR (settled)

1. **C** → OCR type → a **region rectangle** appears with **N**, starting as a default mid-screen box.  
2. User **drags edges/corners** (or move+resize) to the ROI.  
3. Deck prompts / form for Text vs Color vs Shape enough to proceed; else atom **needs review** (warn only).  
4. Deeper OCR fields under **E**.

### Floating ML → Create Atom

Same Atom Create mode on Deck (no special case).

### Settings (**S**)

**For now:** boot preference (Idle Lab vs Flight Deck) only. More settings later.

---

## Soft leftovers (OK to park)

- Esc peel order when menus nested (implement-time)
- Post-run / post-observe “open OL” chrome on Deck (mentioned earlier; not blocking)
- Exact event-specific edit chords beyond the fields already listed
