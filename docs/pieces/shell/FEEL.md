# Operator feel (draft)

**Status:** draft — direction locked in talk 2026-11-13; not fully coded.  
**Purpose:** [VISION.md](../../VISION.md) · **Shell:** [README.md](README.md) · **Handoff:** [../../CONTINUATION.md](../../CONTINUATION.md)

## What we kept / cut from Feel Lab

| Keep | Cut |
| --- | --- |
| **Multiple themes** → real **Idle Lab skin system** | Structure experiments |
| Nested one-path folder grammar + Esc peel for keys | Info tab as Feel Lab / specimen-tray product surface |
| `[key] Label` expected-action language | Peer Flight Deck as second home |

Feel Lab (`python -m idle_lab.feel_lab`) may remain a private toy; product chrome only needs **skins**.

## Two costumes, one window

| Costume | Feel |
| --- | --- |
| **Expanded** | Desk. Mouse builds atoms/molecules. Left = file-tree labs; bottom of rail = **Hotkey Flight Deck** pocket; right = action space. |
| **Condensed** | Shoulder glance. Lab on pause while LOL/Observation owns focus. Status + outside chords. Same window, less furniture. |

`` ` `` = Deactivate = Stop all. Esc out of LOL = **loud confirm on the anchored screen**, not a tiny Lab dialog.

## Hotkey pocket (expanded)

App saying: *I think your focus is here — here are the expected actions as keys.*  
Screen buttons always work. Pocket tracks. Height breathes. Minimize is obvious (`Hotkey flight deck · [key] open/close`). Never floats; never eats the action pane.

**Mouse** may teleport in the tree (sibling click collapses the other branch).  
**Keys** walk the stack; Esc peels one folder.

## Voices (updated)

| Voice | Channel | Density |
| --- | --- | --- |
| **Expanded Lab** | Mouse · tree · action pane | Explanatory |
| **Hotkey pocket / condensed** | Expected chords · status | Terse · muscle-memory |
| **LOL glass** | Overlay on target | Hands-on; *is* the LOL hotkey UI |

No peer Deck window. No third cancel story.

## Surfaces (updated)

| Part | What it is |
| --- | --- |
| **Idle Lab** | The app — expanded or condensed |
| **Hotkey Flight Deck** | Docked pocket in left rail (expanded) / condensed face language |
| **Overlay (LOL)** | Marks / regions / handles on the game |
| **Queue** | Script list when authoring atoms |
| **Console** | Shared log — progressive in condensed; docked when useful in expanded |

## Menus / controls (leaning)

| Type | Use when |
| --- | --- |
| **File-tree labs** | Left rail navigation |
| **Action pane** | Right — the work |
| **Hotkey pocket leaves** | Expected actions for current folder depth |
| **Lab button** | Mouse twin of a pocket leaf |
| **Esc peel** | One folder out (keys); LOL exit = confirm overlay |
| **`` ` ``** | Deactivate = Stop all |
| **Hold D** | Describe (LOL) |

## Hard refuse

- Peer Flight Deck as a second exclusive OS  
- Floating hotkey window over the action pane  
- Atom Create as Deck-only piano with no mouse desk  
- Silent no-ops — fail loud or abstain  
- Inventing a new cancel / save story mid-feature  

## Agent gate

Before proposing UI:

1. Expanded or condensed? Pocket or glass?  
2. Does this extend skins / tree grammar? Update this draft first.  
3. Prefer “tree + pocket + Esc peel” over a new window type.

Ask: “Lab button or pocket leaf?” · “Morph to condensed or stay expanded?” — not freeform widgets.

---

## Palette ids (legacy specimen — revisit with skins)

Older accordion/tray ids below may still inform naming; **Info specimen tray is not a product requirement.** Prefer skins + pocket language above when they conflict.

### Fundamental feel (still true)

1. User lands on a **layer** / folder. Only that layer’s expected actions are live.  
2. Live actions read **`[key] Label`** (in pocket and/or on glass).  
3. Key → push deeper; mouse may re-root.  
4. **Esc** peels one layer (except LOL exit confirm).  
5. Condensed + pocket speak this same language.
