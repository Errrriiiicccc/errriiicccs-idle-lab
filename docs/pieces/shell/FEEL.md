# Operator feel (draft)

**Status:** draft — not locked.  
**Purpose:** [VISION.md](../../VISION.md) · **Shell:** [README.md](README.md) · **Info:** [info.md](info.md)

**In-app:** Idle Lab → Info → **How it talks** is a **specimen tray** (poke parts; captions from doing). Agents use the same ids below when asking “accordion or Lab button?” — not freeform widgets. If nothing fits, extend this file and the tray before coding.

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
