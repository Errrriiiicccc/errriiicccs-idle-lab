# Operator feel (draft)

**Status:** draft — not locked.  
**Purpose:** [VISION.md](../../VISION.md) · **Shell:** [README.md](README.md) · **Info:** [info.md](info.md)

**Two in-app surfaces:**

| Surface | Job |
| --- | --- |
| **Info → How it talks** | Settled **specimen tray** of the current palette (poke; captions from doing) |
| **Feel Lab** | Sandbox. Left **Home** = main tabs. Middle = accordion **sub-tabs** (siblings stay; open one expands children underneath — e.g. Colour: Thread/Rim/Lift/Type). Colour lean: **Type → Bracket**. Structure lean: same accordion. Picks → [`feel/picks.json`](../../../feel/picks.json). |

### Fundamental feel (candidate → FD)

1. User lands on a **layer** (e.g. Stages). Only that layer’s buttons are live/highlighted.  
2. Live buttons read **`[key] Label`**.  
3. Press key → push deeper; parent layer loses keys/highlight.  
4. **Esc** peels one layer.  
5. Flight Deck accordion should speak this same language once a theme wins.

Agents use the palette ids below when asking “accordion or Lab button?” — not freeform widgets. Wild alternatives live in Feel Lab first; winners promote here + Info tray before coding into the shell.

---

## Two voices, one product

| Voice | Channel | Density |
| --- | --- | --- |
| **Idle Lab** | Mouse · buttons · tabs | Explanatory |
| **Flight Deck** | Hotkeys · accordion | Terse · muscle-memory |

Same Labs. Never a third voice (half-hotkey dialogs, unique cancel paths, one-off chrome).

---

## Surfaces

| Part | What it is |
| --- | --- |
| **Idle Lab** | Mouse home · tabs · no hotkeys while open |
| **Flight Deck** | Hotkey companion · never shown with Idle Lab |
| **Lab float** | Lightweight Lab from Deck (ML / Atom Lab / OL) |
| **Overlay** | Marks / regions / handles on the game |
| **Queue** | Separate script list (Atom Create truth) |
| **Console** | Shared log · docked in Molecule Lab · float on Deck |

---

## Menus

| Type | Use when |
| --- | --- |
| **Tabs** | Top Lab switch (Info / LOL / Molecule / Observation) |
| **Sub-tabs** | Inside a Lab (Atom · Molecule · Trial) |
| **Accordion** | Deck letter → digit leaves · Create / Edit too |
| **Nested outline** | Info drill-down only |

---

## Controls

| Type | Use when |
| --- | --- |
| **Chrome button** | Always-on transport (Anchor · Restart · Settings · Open Deck) |
| **Lab button** | Mouse twin of a Deck leaf |
| **Hotkey leaf** | One action in an accordion |
| **Toggle leaf** | Two-state press (e.g. Single \| Spam) |
| **Type-in leaf** | Press → type number/text · Esc cancels |
| **Hold D** | Describe the live leaf |
| **Esc peel** | One layer out · outer save / exit |
| **`` ` ``** | Activate / Deactivate only |

---

## Feedback

| Type | Use when |
| --- | --- |
| **Deck line** | What’s live (“Creating Key Event…”) |
| **Queue line** | Script step truth (`key:?`) |
| **Glyph** | Selection / placement on the game |
| **Status strip** | Running / files changed — chrome, not Info |
| **Needs review** | Incomplete cue (OCR) — honest, not silent |

---

## Hard refuse (anti-patterns)

- Unique dialogs for what **Esc peel** already does  
- Empty chrome / collapse buttons with no job  
- Modes that hide Stop / Deactivate  
- Mouse-only paths with no Deck dual (or the reverse) without documenting why  
- Silent no-ops — fail loud or abstain  
- Inventing a new cancel / save story mid-feature  

---

## Agent gate

Before proposing UI or implementing a Lab slice:

1. Which **surfaces / menus / controls / feedback** does this use?  
2. Does it **extend** the palette? If yes → update this draft + Info first.  
3. Prefer “accordion + queue + Esc peel” over a new window type.

Ask the operator in palette language: “Accordion leaf or Lab button?” · “Lab float or Idle Lab sub-tab?” — not freeform widgets.
