# Continuation handoff

**Errriiiccc's Idle Lab** — `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`

**North star:** [VISION.md](VISION.md)  
**Cascade:** [README.md](README.md) · [../AGENTS.md](../AGENTS.md)  
**Redesign:** [pieces/README.md](pieces/README.md) · shell [pieces/shell/](pieces/shell/README.md) · hygiene [pieces/hygiene/CUT-REFINE-KEEP.md](pieces/hygiene/CUT-REFINE-KEEP.md) · [archive/README.md](../archive/README.md)  
**Target vs code:** [FEATURES.md](FEATURES.md)

## Active focus (2026-11-11)

**Phase map Atom Create** — kind gate + leaves (shape-first).

- Deck **M→3** → **1 Automation** | **2 Phase map**
- Phase map: **G** Keys · **H** Phases · **T** Targets · **S** Scroll (= Automation drag) · **R** Region · **A** Raw · **E** Edit · **X** Expand preview
- Save expands targets → child automation atoms (enter + scrolls + act). Sample: [`automations/events/phase_map_cards.json`](../automations/events/phase_map_cards.json)
- Docs: [pieces/shell/molecule-lab.md](pieces/shell/molecule-lab.md)

→ **Restart** Idle Lab · Create Atom · Phase map · author Cards scroll+equip · **X** preview · Esc save.

### Soft hold: Feel Lab

Primary: **Type → Bracket**. Accordion sub-tabs in the middle — siblings stay visible; expand under selection (Colour: 1–4 families, looks nest with A/S/D…). Restart Feel Lab.

### Soft hold: Automation Atom Create smoke

Atom Create IA checkpoint committed (`090db3f`). Smoke notes below still valid when you return.

### Smoke Atom Create

1. Deck **M→3** Create Atom. Queue must **not** cover the Deck.
2. **B** expands / **B** again collapses · no empty **X Collapse menu**.
3. **B→3** Key: FD says “Creating Key Event…” · queue shows `key:?` · press key → confirms.
4. **D** → detail arrows under steps (position / mode / drag fields…).
5. **E** on click/key: **Mode:** toggle · when Spam: **Spam: Clicks|Timed** · Amount/Duration + Interval (press → type). Esc snaps timed duration.
6. Drag/OCR also state-on-leaf. **P** rewrite · Esc peels · outer Esc saves.

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data → Refresh; code → Restart.  
**Test:** [HARNESS.md](HARNESS.md) · [`lab-context.json`](../lab-context.json).

## What landed recently

- Phase map Atom Create kind gate + G/H/T/S/R/A/E/X leaves; scroll defs = drag; expand-on-save
- Sample Cards phase map (`phase_map_cards`)
- Feel Lab sandbox (`python -m idle_lab.feel_lab` / Desktop shortcut)
- Atom Create Automation: **B** Basic Gesture, **P** Playbook, **E** Edit

## Soft parked

- Richer OCR color picker UI · spam hold-time variants beyond clicks/timed  
- Current State schema · package rename · in-app AI dispatch  
- Molecule Lab palette: pick phase-map targets as first-class compose steps (expand works on save today)

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless overridden.

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab
