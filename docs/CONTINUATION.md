# Continuation handoff

**Errriiiccc's Idle Lab** — `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`

**North star:** [VISION.md](VISION.md)  
**Cascade:** [README.md](README.md) · [../AGENTS.md](../AGENTS.md)  
**Redesign:** [pieces/README.md](pieces/README.md) · shell [pieces/shell/](pieces/shell/README.md) · feel [pieces/shell/FEEL.md](pieces/shell/FEEL.md) · [archive/README.md](../archive/README.md)  
**Target vs code:** [FEATURES.md](FEATURES.md)

## Active focus (2026-11-13)

**One window, two costumes + a hotkey pocket** — abandon peer Flight Deck. Fold its job into Idle Lab.

Talked through with Eric (docs only; code still ships the old exclusive Deck). Detail: [pieces/shell/README.md](pieces/shell/README.md) · [FEEL.md](pieces/shell/FEEL.md) · [DECISIONS.md](pieces/DECISIONS.md).

### Expanded vs condensed

| Costume | Job |
| --- | --- |
| **Expanded** | Normal Idle Lab — mouse desk for authoring (atoms / molecules / settings). |
| **Condensed** | Same window, skinny “Flight Deck representation” — status + outside chords. Auto-morph when LOL (and Observation) takes focus — Steam Play metaphor: Lab takes a break; close LOL → Lab expands again. |

`` ` `` = **Deactivate = Stop all** (unchanged). Condensed chord map is **mode-specific** (don’t invent a universal accordion yet).

**LOL Esc:** big confirm overlay on the **anchored screen** — **Exit Live Overlay Lab?** · Esc = cancel · Enter = exit → expand Lab. LOL has no inner Esc peel (Hold D = describe; `` ` `` = pause/deactivate without killing LOL).

**Condensed during LOL** does **not** mirror glass hotkeys (LOL *is* that UI). It shows **outside** chords + status only for now: Hold D, Esc (→ confirm), `` ` ``, status. Presets later maybe.

Console in condensed: progressive — an action can grow the window slightly to show console; another control cycles verbosity.

### Hotkey Flight Deck (pocket inside Lab)

Always **inside** Idle Lab — never floating.

- Left rail = labs as a **file-tree** (nav chrome).
- Pocket sits at the **bottom of that rail** (dead space — never steals the right-hand action pane).
- Feels like a window-in-window: titlebar **Hotkey flight deck · [key] open/close** + obvious minimize. Key is Settings-remappable (pick later).
- Height **breathes** with the current focus map.
- Mirrors **expected actions** for where the app thinks focus is — screen buttons remain real; pocket is the fast path. Pocket **tracks** clicks (no mismatch theater).

**Tree / focus grammar:** one open path at a time. Mouse may teleport (select sibling → prior branch collapses). Hotkeys walk the stack; **Esc** peels one folder. Example: ABCD → B→XYZ → Y→123; click C → see HJK (B gone). Keys would Esc back to ABCD then C.

Authoring (Atom Create kind gate → phase tools → gesture, etc.) lives in expanded Lab with this pocket — not a peer Deck overlay piano.

### Themes

Fold Feel Lab **themes** into a real Idle Lab **skin system**. Omit Structure experiments. Omit Info-as-Feel-Lab / specimen tray as a product surface. Feel Lab sandbox may linger as a toy; product only needs skins.

### Soft hold (not this arc)

- Current State + C5 Tower vertical — still true product gap; **after** this shell reshape unless Eric reorders.
- Phase map / Atom Create smoke on the *old* Deck Create path — lands until authoring moves into the tree+pocket.

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data → Refresh; code → Restart.  
**Test:** [HARNESS.md](HARNESS.md) · [`lab-context.json`](../lab-context.json).

## What landed recently

- Tonight’s shell feel locked in docs (expanded/condensed, pocket, themes-as-skins) — replaces accidental “state-loop next” handoff
- Phase map Atom Create + Cards sample; Feel Lab sandbox on disk
- Shape-first exclusive Deck/Lab still **ships in code** until this reshape is built

## Soft parked

- LOL presets from condensed · simultaneous Lab+LOL (close/reopen is enough for now)  
- Condensed chord lists beyond LOL/Observation · open/close key pick  
- Current State schema · C5 · package rename · in-app AI dispatch · `app.py` extract  

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless overridden.

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab
