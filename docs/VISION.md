# Idle Lab — product vision

**Status:** canonical north star (docs redesign closed 2026-11-10)  
**Audience:** humans and AI chats building this repo  
**Cascade:** [docs/README.md](README.md) · surface [FEATURES.md](FEATURES.md) · pieces plan [pieces/README.md](pieces/README.md) · next-chat [CONTINUATION.md](CONTINUATION.md)

This document is the **only** place that may redefine product purpose for Errriiiccc's Idle Lab. Implementation docs describe what ships today; [pieces/](pieces/README.md) is where we plan shell/IA and cut/keep before coding. Research lanes are cite-only. When those disagree with this file on purpose, update this file deliberately — do not silently drift.

The separate workspace `idle-lab/docs/` is a **mineable archive** (useful + deprecated mixed). It does not redefine purpose. Cleanup / salvage of that tree is tracked under [pieces/hygiene/](pieces/hygiene/README.md).

---

## 1. One sentence

Idle Lab is a **human-translation workbench**: a person shows a screen, says what they see and what they want, and the system (with AI as the authoring backbone) turns that into **repeatable, inspectable automations** that act through ordinary mouse and keyboard, sense the UI through pixels when needed, and — when a title offers it — read **first-party structured exports** (saves / tool dumps) instead of guessing numbers from OCR.

---

## 2. The heart of the idea

A human already knows how to use an application. They look at the screen, recognize state, decide, and act. Idle Lab exists to **capture that competence** and replay the mechanical parts.

The intended loop:

1. **Show** — Open a game, app, or site. Anchor Idle Lab on that window. Record clicks and/or capture Observe batches while navigating real UI.
2. **Speak** — In plain language (chat, notes, voice-to-text later), describe what is on screen, what matters, and the goal. Example intent is not a macro script; it is a policy:
   - “When an enemy nameplate appears here, press Attack.”
   - “When the loot list appears there, open inventory; sell non-weapons; keep only daggers; leave me a pile of dagger types when I return.”
3. **Translate** — AI proposes the working vocabulary of interaction: ROIs, templates, presets, atoms, molecules, branches, waits, scrolls (“drag ~300px to reveal the next button row”). Idle Lab is the **handler** that stores and runs those artifacts.
4. **Prove** — Missions execute, screenshot, match or abstain, fail loudly, and leave evidence. The AI does not have to one-shot the goal; iteration is expected.
5. **Remember** — Durable knowledge documents (playbooks, object maps, state models, calibrated gestures, export field catalogues) accumulate so **later chats inherit** menu geometry, scroll distances, and “how this app feels,” instead of rediscovering from zero.

That is the product: **human judgment in → structured actuation out**, with a growing shared map of the target UI.

### 2.1 Why it exists (lineage)

The lab grew out of fascination with limit-pushing idle runs — measurement, footage, playbooks — and a working clicker fork. That content/measurement impulse still matters as an **outcome flavor** (clips, CSVs, checkpoints, handoff notes). The **product identity** is the workbench that makes those outcomes teachable and repeatable through demonstration + language, not a silent bot.

---

## 3. Principles

| Principle | Meaning |
| --- | --- |
| **Human translation, not process injection** | Prefer what a person (or the title’s own tooling) could legitimately access. No silent memory scrapes, no process injection, no “undetectable” claims. First-party exports, documented pulls of those exports, and **in-title automation hooks** (e.g. game macros) are fair game — push every target to its legitimate limits. |
| **Sense ladder + ordinary input** | Prefer trustworthy data in order: **structured source** → **title-native hooks** → **pixels / OCR / our own atoms**. Actuation = ordinary clicks, keys, scrolls, waits (and title-native macros when they exist). |
| **Files are the language** | Presets, ROIs, atoms, molecules, templates, object maps, Observe batches, mission reports, and knowledge docs are the durable artifacts AI and humans edit. The app reloads and runs them. |
| **AI authors; Idle Lab executes** | Models propose and revise artifacts. The lab must **faithfully** run and evidence them. Hallucinated success is a product bug. Today the LLM is outside the process; **dispatching prompts from the app** (packet + evidence in → artifacts out) is an explicit horizon — see [pieces/authoring/](pieces/authoring/README.md). |
| **Iterate in public** | Failures produce shots, traces, CSVs, and reports. Missions exist so first attempts can be wrong. |
| **Knowledge compounds** | Each calibrated scroll, menu path, export field, and state discriminator should land in a document successors can cite. |
| **Attended and honest** | Operator can Refresh, Restart, Stop all, and Deactivate. Supervised modes and visible queues beat silent autonomy. |
| **Tower is the proving ground** | Obsess on The Tower until the workbench is much cleaner. The ceiling remains **any** Windows GUI (or similar) you can demonstrate — switch titles only when the lab earns it. |

---

## Lexicon (operator ↔ disk ↔ code)

Use **operator terms** in UI and product docs. Disk and package names lag for compatibility; do not invent a third vocabulary.

| Operator / docs | On disk | Package / symbols |
| --- | --- | --- |
| **Flight Deck** | `automations/flight_deck.json` | `flight_deck/` |
| **Idle Lab** (window) | (rebuild; replaces mega tabs) | `app.py` today |
| **Info** | (in-app docs tab) | — |
| **Live Overlay Lab (LOL)** | `automations/maps/*.objects.json` | `live_control/` (rename later) |
| **Molecule Lab** / **Atom Create** | `automations/composer/` + atoms on disk | `composer/` |
| **Observation Lab** | `screen-maps/`, `ai-batches/` | `observation/`, `ai_batch/` |
| **Atoms** | `automations/events/*.json` | `Event` |
| **Molecules** | `automations/collections/*.json` | `Collection` |
| **Persistent / Current State** | e.g. `stat_collect` + exports | `tool_export` (+ future state) |
| Legacy Bench presets | `presets/` | `presets.py` … |
| Package import | `errriiicccs-idle-lab` | `idle_lab` |

**Flight Deck** = hotkeys · **Idle Lab** = mouse dual · **Labs** = LOL, Molecule (Atom inside), Observation. Legacy words Bench/Loops/Missions/LCO/Screen Map map into that. Rename pass + archive: [pieces/hygiene/](pieces/hygiene/README.md), [archive/](../archive/README.md). Shell: [pieces/shell/](pieces/shell/README.md).

---

## 4. Perception: turning the screen into data

Automation logic only works if the screen becomes **typed, trustworthy data**. Perception is not “run Tesseract and hope.” It is a stack of cue types, each mapped to variables the scheduler and branches can use.

### 4.1 Cue families (non-exhaustive)

| Cue | Role | Examples |
| --- | --- | --- |
| **First-party export** | Structured numbers/flags from the title’s own tooling | Tower tool dump wallets, wave, tier, labs |
| **Text / numerics** | Read labels and quantities inside defined regions; constrain ranges, phrases, formats | Dialog titles, on-screen-only HUD text |
| **Icon / template presence** | Detect stable pictograms OCR mishandles | Gem box open/closed, currency icons, tab glyphs |
| **Layout / panel state** | Coarse UI mode from structure or color | Upgrade panel open vs closed; which footer tab |
| **Spatial / gesture calibration** | How far to scroll or drag to reveal the next control | “300px down reveals the next upgrade row” |
| **Transient indicators** | Short-lived popups that gate actions | Enemy nameplate in a fixed band; loot list region |
| **Composite screen state** | Layered model built from the above | See §5 |

Every cue should produce either a **clean value**, a **known enum**, or an explicit **unknown / abstain** — never a silently invented quantity. Bad data must not drive irreversible actions without a policy.

### 4.2 Quality bar for numeric / text fields

For data collection and branching:

- Prefer **first-party exports** when the title exposes them.
- Prefer **tight crops** and field-specific parsers over global “recover anything.”
- Prefer **reject** (blank / `UNKNOWN`) over order-of-magnitude hallucinations.
- Treat format families separately (e.g. `142/min` vs `1.68K/min`) instead of one regex that “fixes” both.
- Keep probe screenshots and CSV as regression ground truth when tightening perception.

OCR engines, template match, and (where appropriate) vision-assisted authoring are **instruments**. The product requirement is trustworthy variables — not loyalty to one library.

### 4.3 Preference ladder (any target)

Push the target to its legitimate limits. Do not guess when a better channel exists.

1. **Structured source** — first-party exports, saves, tool dumps, documented pulls (Tower: [knowledge/TOWER-TOOL-EXPORT.md](knowledge/TOWER-TOOL-EXPORT.md)). Prefer this for wallets, wave, tier, labs, run stats, and anything else the title already knows.
2. **Title-native hooks** — automation the app already supports (macros, APIs, accessibility trees, browser DOM when honest and available). Sense *and* act through these when they are the efficient path.
3. **Our pixels + atoms** — screenshots, ROIs, OCR, templates, panel cues, object-map clicks. OCR stays **typed and abstaining**. Use this when (1) and (2) cannot see or do the thing.
4. **Knowledge artifacts** — calibrate and write down what worked so later chats inherit it.
5. **Honesty** — structured sources and native hooks do not excuse silent injection or memory scrapes. Ordinary input (or the title’s own macro surface) remains the actuation story.

Day-to-day perception status lives in [CONTINUATION.md](CONTINUATION.md) and [pieces/sense/](pieces/sense/README.md).

---

## 5. Layered screen state (data, not vibes)

Targets like The Tower are not a single boolean. State is **hierarchical and persistent**. Idle Lab should model it as explicit structures that automations can query.

Illustrative Tower layers (pattern generalizes to other apps):

```
App / window focused
└── Surface: main gameplay loop | shop | settings | other top-level route
    ├── Overlay: hamburger / options rail expanded or collapsed
    │     └── Which option icons are visible
    ├── Dock: upgrade panel closed | Attack | Defense | Utility | Ultimate
    │     └── Scroll offset / which upgrade rows are in view (persists)
    ├── HUD mode: balances vs per-minute rates (currency toggle)
    └── Combat / run phase: in-wave | between waves | game over | …
```

Requirements implied by this model:

1. **Named states** with discriminators (ROI text, templates, `detect_panel`, exports, etc.).
2. **Dependencies** — e.g. option-rail icons only matter when the rail is expanded; tab scroll only matters when a tab is open.
3. **Persistence** — scroll position and last tab are part of state, not forgotten between ticks.
4. **Knowledge docs** — once calibrated (“Utility tab + ~300px scroll → Free Upgrade row visible”), write it down for future chats and for the operator.

Building these structures is primarily a **data and schema** problem: define the state machine, map cues to fields, store playbooks. The runtime then branches on those fields. Molecule Lab conditionals and a queryable **Current State** are the product face of this section.

---

## 6. Authoring experience (target story)

This is the experience the product is aiming at — not a claim that every step is automated in-app today.

1. User opens a new target (game, desktop app, website in a window).
2. User starts an Observe session and/or records Bench presets while walking the UI.
3. User (in Cursor or notes) states goals and observations in plain language.
4. AI inspects shots and descriptions, then proposes:
   - ROIs and templates for cues
   - presets for clicks/drags/scrolls
   - atoms/molecules for policies
   - a first **knowledge document** (menu map, state list, calibrated gestures, export fields)
5. User Refresh / Restart as appropriate and runs Missions or Loops.
6. Evidence returns; AI revises artifacts; acceptance criteria get stricter.
7. Later sessions load the knowledge doc and extend it (“add dagger filter,” “also log wave to CSV”) without remapping the whole app.

**Prompt packets** (screenshots + Idle Lab schema contracts + human intent) are the portable brief that lets any capable model participate in steps 4–6. Molecule Lab is the in-app authoring surface for composing gated molecules from demonstrated objects.

---

## 7. What Idle Lab is — and is not

| Is | Is not |
| --- | --- |
| A workbench for screen-based sense → decide → act | A memory reader or injected game client |
| A file-backed automation host with operator chrome | A cloud agent that owns the mouse without evidence |
| An atlas + mission + loop toolkit for teaching UIs to AI | A one-shot “fully autonomous player” promise |
| A path toward assistive, attended GUI help | Stealth / ToS-evasion tooling |

Ethics remain operator responsibility: check target rules; prefer attended runs; keep Stop all obvious.

---

## 8. How current surfaces serve the vision

Shell redesign ([pieces/shell/](pieces/shell/README.md)): **Flight Deck** (hotkeys) and **Idle Lab** (mouse) both open the same **Labs**. Mega tabbed window is retired in the plan. Until code lands, some docs still say Bench / Observe / LCO.

| Surface | Vision role |
| --- | --- |
| **Flight Deck** | Hotkey companion — quick Labs/starts; Deactivate = Stop all |
| **Idle Lab** (window) | Mouse-dense dual — same power, more description/review |
| **Labs** | Focused modules (LOL, Molecule, Observation, Basic Autoclicker, …) |
| **Current State** | Memory — queryable layered state ([pieces/state/](pieces/state/README.md)) |
| **Chrome** | Honesty — Anchor, Refresh, Restart, Stop all / Deactivate |

---

## 9. Success looks like

- A new target can be taught by **demonstration + language**, not by reverse-engineering binaries.
- Automations are **readable files** a human can audit.
- Missions **converge** with screenshots and reports, not with imagined clicks.
- Screen **state** is queryable at multiple layers for branching.
- Numeric/text collection is **boring and correct** enough to drive logic — or explicitly blank.
- A returning operator (or chat) can open a knowledge doc and **continue** instead of starting over.
