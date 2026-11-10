# Living decisions (cross-cutting)

Park questions and ideas here. When settled, **fold into** the owning piece README (and [VISION.md](../VISION.md) only if purpose changes). Strike or move — do not leave zombie open items.

Status tags: `open` · `leaning` · `settled` · `parked`

---

## Naming & shell

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D1 | settled | Keep **Flight Deck** as the hotkey companion | Not renamed to Idle Lab |
| D2 | settled | Rename LCO → **Live Overlay Lab (LOL)** | Lab nomenclature + atoms/molecules |
| D3 | settled | Destroy mega tabbed window; rebuild as **Labs** only | Labs: Info, LOL, Molecule (Atom inside), Observation; Autoclicker folded into Atom |
| D4 | settled | **Idle Lab** = mouse-dense dual of Flight Deck | Same starts; mouse vs hotkeys |
| D5 | settled | **Deactivate = Stop all**; only `` ` `` still listened | Confirmed |
| D6 | settled | Rich surface name = **Idle Lab** | Resolves naming collision |

## Cut / keep / rename

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D10 | settled | Cut / Refine / Keep | Agreed leans in [hygiene/CUT-REFINE-KEEP.md](hygiene/CUT-REFINE-KEEP.md); archive policy in [archive/README.md](../../archive/README.md) |
| D11 | settled | **Full rename pass** (UI + disk + packages) | After shell/LOL names land in plan; before or with code waterfall |
| D12 | settled | External `idle-lab/docs/` — **ignore by default**; mine only if a piece needs a specific fact; no parallel vision | Agent judgment 2026-11-09; happy to cut |
| D13 | parked | FEATURES “Not in this POC” review | Same canvas as D10 |

## Sense & state

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D20 | settled | Sense ladder: source → native hooks → pixels/OCR | VISION §4.3 |
| D21 | settled | **Current State** is core | |
| D22 | parked | Ordering C5 vs Current State vs shell | Everything rewriting; decide later |
| D23 | parked | Browser DOM / a11y trees | Explained below; later-title research, not Tower-now |

### D23 plain English (for later)

**Browser DOM** = the HTML structure of a web page (buttons, text, IDs) — automation can click/read nodes instead of OCR’ing pixels.  
**Accessibility tree** = the OS/app’s “what’s on screen for screen readers” API (names, roles, bounds) — same idea for desktop apps.  
Both are “title-native hooks” on the sense ladder. Tower/BlueStacks won’t give us much here; useful when we hit browsers or accessible desktop apps.

## Authoring & AI

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D30 | parked | In-app prompt dispatch | TBD — not current focus |
| D31 | parked | Model transport | Needs a scoped pass later |
| D32 | parked | Files remain source of truth | Settled in principle; not focusing now |

## Target & ambition

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D40 | settled | Tower until much cleaner; multi-title ceiling | |
| D41 | parked | “Much cleaner” exit checklist | Hard to say; revisit after shell/labs settle |

## Process

| ID | Status | Question / idea | Notes |
| --- | --- | --- | --- |
| D50 | settled | Docs/plan before coding waterfall | |
| D51 | settled | FEATURES/LAYOUT/README synced to target vs ships-today | 2026-11-10 |
| D52 | parked | Research L1–L10 cite-only | |

---

## Fold log

| Date | What folded | Where |
| --- | --- | --- |
| 2026-11-09 | Sense ladder; Tower proving-ground; Deactivate; archive mine | VISION + pieces created |
| 2026-11-09 | Flight Deck kept; Idle Lab = mouse dual; LOL; Labs destroy/rebuild; D12/D22–D32/D41 parked | shell + hands + VISION lexicon + this file |
