# Features

**Purpose:** [VISION.md](VISION.md) · **Cascade:** [README.md](README.md) · **Shell plan:** [pieces/shell/](pieces/shell/README.md) · **Hygiene:** [pieces/hygiene/CUT-REFINE-KEEP.md](pieces/hygiene/CUT-REFINE-KEEP.md)

This file has two layers on purpose:

1. **Target shell** — agreed redesign (shape-first code aims here).  
2. **Ships today** — what the running app is after the shape-first waterfall.

Day-to-day chat focus: [CONTINUATION.md](CONTINUATION.md).

---

## Target shell (agreed)

### Surfaces

| Surface | Role |
| --- | --- |
| **Idle Lab** | Mouse-first home. **No hotkeys** while open. Tabs = **Info** + Labs. Factory boot. Persist last tab. |
| **Flight Deck** | Hotkey companion. Starts **deactivated** (only `` ` ``). Never shown with Idle Lab at once. |
| **Labs** | Focused modules (embedded in Idle Lab; **floating** from Deck). |

Hard rules: anything running → Idle Lab closes, Deck only; **Deactivate** = Stop all; resume handle after Deactivate; shared **console** object (docked bottom when Molecule Lab open; floating on Deck).

Detail: [pieces/shell/README.md](pieces/shell/README.md), [pieces/shell/flight-deck.md](pieces/shell/flight-deck.md).

### Idle Lab tabs

| Tab | Job |
| --- | --- |
| **Info** | Nested verbose docs / onboarding; checklists + links to Labs |
| **Live Overlay Lab** | Interactive target map + live object-map hands |
| **Molecule Lab** | **Atom** create/edit · **Molecule** compose · **Trial** browse/run |
| **Observation Lab** | **User** capture/review + **AI mission** (Start / Mission view / Results) |

No separate Bench, Loops, Missions, or Autoclicker top-level tabs.

### Flight Deck (target)

- Top-level accordion: **L** / **M** / **O** / **S** · **X** collapse · hold **D** describe · `` ` `` Deactivate.
- Prefer nested leaves over flat enter — e.g. **L** Start + console toggles; **M** Molecule vs Atom Lab; **S** common settings inline.
- Modes abandon prior hotkeys when a Lab owns the surface (LOL / ML float / Settings). **Atom Create** keeps accordion grammar with a create keymap.
- Atom Create: accordion step sections · **E** edit stub · save on exit (needs event id) · shared overlay primitives with Live Overlay Lab.

### Sense / state / hygiene (target)

- Sense ladder: structured source → title-native hooks → pixels/OCR ([VISION §4.3](VISION.md)).
- Current State is core (timing vs ML polish parked).
- Deprecated demos/docs → [archive/](../archive/README.md); observations are **deleted**, not auto-archived.
- Full disk/package rename pass with or after shape-first ([pieces/hygiene/](pieces/hygiene/README.md)).

### Shape-first build rule

Show UI skeletons/stubs before full wiring — no fake success. Exact runtime (C5 gates, etc.) follows once the shell looks right.

---

## Ships today (shape-first shell on `shape-first-shell`)

Phases **0–5** landed: exclusive surfaces, Info + Labs tabs, Deck **L/M/O/S**, shared overlay + Atom Create stubs, Molecule/Observation hosts, CUT demos archived.

### Global chrome

- Single instance; tray; Anchor; Refresh / Restart / Stop all; Activity + files-changed; Auto/Supervised; Humanize Off default.
- Idle Lab ↔ Flight Deck exclusive; Deactivate = Stop all; resume handle after Deactivate.
- Boot preference (Idle Lab / Flight Deck) in Settings — applies on **Restart**.
- Contract: [REFRESH-RESTART.md](REFRESH-RESTART.md).

### Flight Deck

- Inactive → Activate `` ` ``; accordion **L/M/O/I/S** ([`automations/flight_deck.json`](../automations/flight_deck.json)).
- **L** → Start · Toggle Console · Console Verbosity; **M** → Molecule Lab · Atom Lab · Create Atom; **O** → Observation float; **I** → Start (closes Flight Deck → Idle Lab); **S** → Open Settings · Set Deactivate Key · Boot Preferences.
- Idle Lab chrome always has **Open Flight Deck** `(closes Idle Lab)` — surfaces never share the screen.
- **M→2 Atom Lab** = lightweight Atom library/coverage float; **M→3 Create Atom** = queue + drag-place on Deck. Esc from Create asks to save then returns to Atom Lab. `` ` `` pauses Deck only (keeps Create).
- Live overlay: object map, hold D describe, Esc exit. [LIVE-CONTROL-OVERLAY.md](LIVE-CONTROL-OVERLAY.md), [OBJECT-MAP.md](OBJECT-MAP.md).

### Idle Lab Labs

| Tab | Ships |
| --- | --- |
| **Info** | Nested outline + tab links |
| **Live Overlay Lab** | Map list + Start live → Deck |
| **Molecule Lab** | **Atom** library + LOL coverage · Atom Create (**B** Basic Gesture · **P** Playbook · **E** Edit + queue) · **Molecule** in-tab composer (+ Pop out) · **Trial** browse/run |
| **Observation Lab** | **User** capture/review (date groups; Mark + rename-on-stop cut) · **AI mission** (Add feedback cut) |

### Engines still callable

- Atoms/molecules files, scheduler, queue, Walkthrough, Validate/Dry-run (explicit packs only).
- Composer drafts / conditions C1–C4; C5 skip still stub. [MOLECULE-LAB-CONDITIONALS.md](MOLECULE-LAB-CONDITIONALS.md).
- Persistent state via `tool_export`. [knowledge/TOWER-TOOL-EXPORT.md](knowledge/TOWER-TOOL-EXPORT.md).
- AI batches under `ai-batches/`. [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md).

### Archive / CUT demos

- Flagship demos (`ocr_ab_tick`, `minute_clip`, `stat_broll_5m`, `humanize_upgrade_loop`, noisy `composer_test_*`) live under [`archive/automations/2026-11-10-cut-demos/`](../archive/automations/2026-11-10-cut-demos/REASON.md). Live Refresh never loads `archive/`.

### Harness

- `python -m idle_lab.harness …` — [HARNESS.md](HARNESS.md). [`lab-context.json`](../lab-context.json).
- Click-logger demos are archived — restore from archive only if a harness story needs them.

### Still not finished (honest stubs / parked)

- Atom Create OCR deep fields / color-shape · keyboard capture without prompt  
- Current State deep schema · package rename · in-app AI dispatch  
- Process injection / stealth / in-process LLM  
- Fully finished Tower buy-priority product loop · C5–C9  
