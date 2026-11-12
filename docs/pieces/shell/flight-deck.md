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
| **M** | Accordion: Molecule Lab (float) · Atom Lab (library float) · Create Atom |
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

### B — Basic Gesture (example: click)

1. Press **B** → Flight Deck accordion expands → **1** Click / **2** Drag / **3** Key / **4** OCR.
2. Dedicated **Atom queue** window (separate from the Deck) lists the script; glyphs on the game.
3. For click: numbered circle — **mouse drag** to the target.

### P — Playbook rewrite

**P** replaces the Create menu with Tower playbook (**B/T/S/U** accordion). **Esc** returns to Create root (does not exit Create).

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

### Drag (ships)

1. **B→2** → queue `N: Drag` · handles `Na` / `Nb`.  
2. Drag each handle into place.  
3. Persists as `drag`. Speed / end-pause under **E** later.

### Keyboard (ships — press to capture)

1. **B→3** → prompt “press a key” · next physical key → queue `N: key:…`.  
2. Esc cancels capture.  
3. Persists as `key`.

### OCR (ships — region + needs_review)

1. **B→4** → ROI rectangle with **N**.  
2. Drag body to move; SE grip to resize.  
3. Inline `nx/ny/nw/nh` + `needs_review`; deeper fields under **E** later.

### Floating ML → Create Atom

Same Atom Create mode on Deck (no special case).

### Settings (**S**)

**For now:** boot preference (Idle Lab vs Flight Deck) only. More settings later.

---

## Soft leftovers (OK to park)

- Esc peel order when menus nested (implement-time)
- Post-run / post-observe “open OL” chrome on Deck (mentioned earlier; not blocking)
- Exact event-specific edit chords beyond the fields already listed
