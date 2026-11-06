# Idle Lab — product vision

**Status:** canonical north star (2026-11-05)  
**Audience:** humans and AI chats building this repo  
**Related:** [research/PRODUCT-MAP.md](research/PRODUCT-MAP.md), [FEATURES.md](FEATURES.md), [CONTINUATION.md](CONTINUATION.md)

This document states **what Idle Lab is for**. Implementation docs describe what ships today; research lanes explore how. When those disagree with this file on purpose, update this file deliberately — do not silently drift.

---

## 1. One sentence

Idle Lab is a **human-translation workbench**: a person shows a screen, says what they see and what they want, and the system (with AI as the authoring backbone) turns that into **repeatable, inspectable automations** that act through ordinary mouse, keyboard, and pixel observation — never by reading memory or injecting into the target.

---

## 2. The heart of the idea

A human already knows how to use an application. They look at the screen, recognize state, decide, and act. Idle Lab exists to **capture that competence** and replay the mechanical parts.

The intended loop:

1. **Show** — Open a game, app, or site. Anchor Idle Lab on that window. Record clicks and/or capture Screen Map batches while navigating real UI.
2. **Speak** — In plain language (chat, notes, voice-to-text later), describe what is on screen, what matters, and the goal. Example intent is not a macro script; it is a policy:
   - “When an enemy nameplate appears here, press Attack.”
   - “When the loot list appears there, open inventory; sell non-weapons; keep only daggers; leave me a pile of dagger types when I return.”
3. **Translate** — AI proposes the working vocabulary of interaction: ROIs, templates, presets, events, branches, waits, scrolls (“drag ~300px to reveal the next button row”). Idle Lab is the **handler** that stores and runs those artifacts.
4. **Prove** — Missions / knowledge batches execute, screenshot, OCR or match, fail loudly, and leave evidence. The AI does not have to one-shot the goal; iteration is expected.
5. **Remember** — Durable knowledge documents (playbooks, screen maps, state models, calibrated gestures) accumulate so **later chats inherit** menu geometry, scroll distances, and “how this app feels,” instead of rediscovering from zero.

That is the product: **human judgment in → structured actuation out**, with a growing shared map of the target UI.

---

## 3. Principles

| Principle | Meaning |
| --- | --- |
| **Human translation, not process injection** | Sense what a person could see; act how a person could act. No ADB memory dumps, no game-process hooks, no “undetectable” claims. |
| **Pixels and input are the contract** | Observation = screenshots, ROIs, OCR, template match, panel/color cues. Actuation = ordinary clicks, keys, scrolls, waits. |
| **Files are the language** | Presets, ROIs, events, collections, templates, Screen Maps, mission reports, and knowledge docs are the durable “templates” AI and humans edit. The app reloads and runs them. |
| **AI authors; Idle Lab executes** | Models propose and revise artifacts. The lab must **faithfully** run and evidence them. Hallucinated success is a product bug. |
| **Iterate in public** | Failures produce shots, traces, CSVs, and reports. Batches exist so first attempts can be wrong. |
| **Knowledge compounds** | Each calibrated scroll, menu path, and state discriminator should land in a document successors can cite. |
| **Attended and honest** | Operator can Refresh, Restart, Stop all. Supervised modes and visible queues beat silent autonomy. |
| **Tower is a proving ground** | Idle games stress HUD text, layered menus, and long loops. The ceiling is **any** Windows GUI the user can demonstrate. |

---

## 4. Perception: turning the screen into data

Automation logic only works if the screen becomes **typed, trustworthy data**. Perception is not “run Tesseract and hope.” It is a stack of cue types, each mapped to variables the scheduler and branches can use.

### 4.1 Cue families (non-exhaustive)

| Cue | Role | Examples |
| --- | --- | --- |
| **Text / numerics** | Read labels and quantities inside defined regions; constrain ranges, phrases, formats | Wave number, coins `11.28K`, `$1.24K/min`, dialog titles |
| **Icon / template presence** | Detect stable pictograms OCR mishandles | Gem box open/closed, currency icons, tab glyphs |
| **Layout / panel state** | Coarse UI mode from structure or color | Upgrade panel open vs closed; which footer tab |
| **Spatial / gesture calibration** | How far to scroll or drag to reveal the next control | “300px down reveals the next upgrade row” |
| **Transient indicators** | Short-lived popups that gate actions | Enemy nameplate in a fixed band; loot list region |
| **Composite screen state** | Layered model built from the above | See §5 |

Every cue should produce either a **clean value**, a **known enum**, or an explicit **unknown / abstain** — never a silently invented quantity. Bad data must not drive irreversible actions without a policy.

### 4.2 Quality bar for numeric / text fields

For data collection and branching:

- Prefer **tight crops** and field-specific parsers over global “recover anything.”
- Prefer **reject** (blank / `UNKNOWN`) over order-of-magnitude hallucinations.
- Treat format families separately (e.g. `142/min` vs `1.68K/min`) instead of one regex that “fixes” both.
- Keep probe screenshots and CSV as regression ground truth when tightening perception.

OCR engines (Tesseract today; stronger readers later), template match, and (where appropriate) vision-assisted authoring are **instruments**. The product requirement is trustworthy variables — not loyalty to one library.

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

1. **Named states** with discriminators (ROI text, templates, `detect_panel`, etc.).
2. **Dependencies** — e.g. option-rail icons only matter when the rail is expanded; tab scroll only matters when a tab is open.
3. **Persistence** — scroll position and last tab are part of state, not forgotten between ticks.
4. **Knowledge docs** — once calibrated (“Utility tab + ~300px scroll → Free Upgrade row visible”), write it down for future chats and for the operator.

Building these structures is primarily a **data and schema** problem: define the state machine, map cues to fields, store playbooks. The runtime then branches on those fields.

---

## 6. Authoring experience (target story)

This is the experience the product is aiming at — not a claim that every step is automated in-app today.

1. User opens a new target (game, desktop app, website in a window).
2. User starts an Observe batch and/or records Bench presets while walking the UI.
3. User (in Cursor or notes) states goals and observations in plain language.
4. AI inspects shots and descriptions, then proposes:
   - ROIs and templates for cues  
   - presets for clicks/drags/scrolls  
   - events/collections for policies  
   - a first **knowledge document** (menu map, state list, calibrated gestures)
5. User Reload / Restart as appropriate and runs Missions or Loops.
6. Evidence returns; AI revises artifacts; acceptance criteria get stricter.
7. Later sessions load the knowledge doc and extend it (“add dagger filter,” “also log wave to CSV”) without remapping the whole app.

**Prompt packets** (screenshots + Idle Lab schema contracts + human intent) are the portable brief that lets any capable model participate in step 4–6.

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

## 8. How current workspaces serve the vision

| Workspace | Vision role |
| --- | --- |
| **Bench** | Hands — record and replay the physical gestures the human demonstrated |
| **Observe** | Eyes & atlas — titled evidence of what the human saw |
| **Missions** | Teaching loop — AI-proposed procedures with evidence and iteration folders |
| **Loops** | Habits — scheduled policies once perception and states are trustworthy |
| **Chrome** | Honesty — Anchor, Refresh, Restart, Stop all, supervised modes |

---

## 9. Near-term implication (perception rework)

The Tower `stat_collect` OCR path proved both the need and the failure mode: classical OCR plus aggressive “recovery” can look good on one number shape and invent catastrophic values on another (`142/min` → `21.42m`).

Under this vision, the next perception work should:

1. Treat HUD reading as **typed fields with contracts**, not a single catch-all parser.
2. Prefer **abstain** over false confidence for automation decisions.
3. Expand beyond text to **state discriminators** (panel, tab, overlay, HUD mode).
4. Leave **knowledge artifacts** (ROI notes, playbooks, probe ground truth) that future chats extend.
5. Keep the method **screen-faithful** — same information a careful human could use.

Detail and tasking for OCR/state work belong in handoffs and implementation docs; they must stay aligned with §§1–5 here.

**Perception status (2026-11-06):** typed `parse_as` + rate-unit sanitizer landed; then **paused** so Idle Lab can be reshaped at product level. Resume notes: [HANDOFF-PERCEPTION.md](HANDOFF-PERCEPTION.md), [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md).

---

## 10. Success looks like

- A new target can be taught by **demonstration + language**, not by reverse-engineering binaries.
- Automations are **readable files** a human can audit.
- AI batches **converge** with screenshots and reports, not with imagined clicks.
- Screen **state** is queryable at multiple layers for branching.
- Numeric/text collection is **boring and correct** enough to drive logic — or explicitly blank.
- A returning operator (or chat) can open a knowledge doc and **continue** instead of starting over.
