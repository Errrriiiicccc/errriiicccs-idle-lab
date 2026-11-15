# Shell

**Job:** One window — **Idle Lab** — with two costumes (**expanded** / **condensed**) and an in-Lab **Hotkey Flight Deck** pocket.  
**Decisions:** [decisions.md](decisions.md) · **Feel:** [FEEL.md](FEEL.md) · **Handoff:** [../../CONTINUATION.md](../../CONTINUATION.md)

## Direction (2026-11-13 — leaning / docs ahead of code)

Peer Flight Deck as a second exclusive surface is **out**. Fold that job into Idle Lab.

| Costume | Role |
| --- | --- |
| **Expanded** | Full Idle Lab. Mouse desk. Left rail = labs as file-tree; right = action space. Hotkey pocket at bottom of left rail. |
| **Condensed** | Same window, skinny representation. Auto when LOL / Observation owns focus (Steam Play: Lab takes a break). Close that Lab → expand again. |

### Hard rules (new — replace exclusive-Deck law)

1. **One window** — no peer Deck process/surface.
2. **Authoring is mouse-first** — buttons on the right are real; hotkey pocket mirrors **expected actions** for current focus.
3. **`` ` `` = Deactivate = Stop all** — unchanged.
4. **Pocket tracks focus** — click elsewhere retargets the map; no separate “announce mismatch” UI.
5. **Tree grammar** — one open path; mouse may collapse/re-root; hotkeys **Esc**-peel.
6. **LOL Esc** → big confirm on **anchored screen**: Exit Live Overlay Lab? · Esc cancel · Enter exit.
7. **Condensed during LOL** = outside chords + status only (Hold D, Esc, `` ` ``, status) — glass owns LOL actions.
8. Factory / fresh start → expanded Idle Lab (Info or last lab — revisit). Live status in chrome / condensed face.

### Hotkey Flight Deck (pocket)

- Always inside Idle Lab — **never floating**.
- Left-rail bottom (“dead space”) so it never steals action-space.
- Titlebar feel: `Hotkey flight deck · [key] open/close` + obvious minimize; key in Settings later.
- Grows/shrinks with the focused chord map.
- Console in condensed: progressive disclosure + verbosity toggle (control TBD).

### Labs inventory

| Lab | Doc |
| --- | --- |
| **Info** | [info.md](info.md) — docs/onboarding (not a Feel Lab) |
| **Live Overlay Lab (LOL)** | [lol.md](lol.md) — triggers condensed |
| **Molecule Lab** | [molecule-lab.md](molecule-lab.md) — Atom + Molecule + Trial; authoring in expanded |
| **Observation Lab** | [observation-lab.md](observation-lab.md) — triggers condensed |

~~Peer Flight Deck~~ → condensed costume + in-Lab pocket ([flight-deck.md](flight-deck.md) is historical until rewritten).

## Feel

[FEEL.md](FEEL.md) — themes become **Idle Lab skins**; Structure / Info specimen-tray product surface omitted.

## Ships today vs this direction

**Ships:** expanded rail + pocket + action pane; **collapsed** on LOL/Obs; Atom Create in expanded Lab; peer Deck never shown (withdrawn keymap host). Still missing: Esc confirm on glass, richer pocket maps, delete `flight_deck/` package. [FEATURES.md](../../FEATURES.md) · [CONTINUATION.md](../../CONTINUATION.md).

## Implementation

Prior waterfall: [SHAPE-FIRST-PLAN.md](SHAPE-FIRST-PLAN.md) (historical). Next coding pass follows [CONTINUATION.md](../../CONTINUATION.md) — not more peer-Deck leaves.
