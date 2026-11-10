# Features

**Purpose:** [VISION.md](VISION.md) · **Cascade:** [README.md](README.md) · **Shell plan:** [pieces/shell/](pieces/shell/README.md) · **Hygiene:** [pieces/hygiene/CUT-REFINE-KEEP.md](pieces/hygiene/CUT-REFINE-KEEP.md)

This file has two layers on purpose:

1. **Target shell** — agreed redesign (shape-first code aims here).  
2. **Ships today** — what the running POC still is until that waterfall lands.

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
| **Live Overlay Lab (LOL)** | Interactive target map + live object-map hands |
| **Molecule Lab** | **Atom** create/edit + **Molecule** compose; Trial cohesion parked for later polish |
| **Observation Lab** | **User** capture/review + **AI mission** (Start / Mission view / Results) |

No separate Bench, Loops, Missions, or Autoclicker top-level tabs.

### Flight Deck (target)

- Top-level: **L** LOL · **M** Molecule Lab (float) · **O** Observation Lab (float) · **S** Settings (boot preference for now) · **X** collapse · hold **D** describe · `` ` `` Deactivate.
- Modes abandon prior hotkeys (LOL/ML float → Esc + `` ` ``; Atom Create → no accordion).
- Atom Create: **C** place click/drag/key/OCR · **E** edit (**W/S** select, **R/F** reorder) · save on exit · shared overlay primitives with LOL.

### Sense / state / hygiene (target)

- Sense ladder: structured source → title-native hooks → pixels/OCR ([VISION §4.3](VISION.md)).
- Current State is core (timing vs ML polish parked).
- Deprecated demos/docs → [archive/](../archive/README.md); observations are **deleted**, not auto-archived.
- Full disk/package rename pass with or after shape-first ([pieces/hygiene/](pieces/hygiene/README.md)).

### Shape-first build rule

Show UI skeletons/stubs before full wiring — no fake success. Exact runtime (C5 gates, etc.) follows once the shell looks right.

---

## Ships today (POC — lagging the plan)

Until shape-first lands, the running app still has the **mega tabbed** Lab and legacy names.

### Global chrome

- Single instance; deck-first launch; tray; Anchor; Refresh / Restart / Stop all; Activity + files-changed; Auto/Supervised; Humanize Off default.
- Contract: [REFRESH-RESTART.md](REFRESH-RESTART.md).

### Flight Deck (legacy accordion)

- Inactive → Activate `` ` ``; Deactivate = Stop all.
- Accordion `flight_deck.json` letters **U/O/C/N/A/M** (to be replaced by L/M/O/S).
- **LCO** (→ LOL): object map, hold D describe, Esc exit. [LIVE-CONTROL-OVERLAY.md](LIVE-CONTROL-OVERLAY.md), [OBJECT-MAP.md](OBJECT-MAP.md).

### Bench (→ Atom Create)

- Preset record/play, Humanize, click logger. Will dissolve into Molecule Lab → Atom.

### Observe (→ Observation Lab User)

- Observation sessions: timeline + shots under `screen-maps/`; Mark / rename-on-stop still present (**CUT** in plan).
- [SCREEN-MAP-USAGE.md](SCREEN-MAP-USAGE.md), [GAMEPLAY-TEST.md](GAMEPLAY-TEST.md).

### Missions (→ Observation Lab AI mission)

- `ai-batches/` steps, probes, run_report, Export packet, seeds. [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md), [PROBE-MISSIONS.md](PROBE-MISSIONS.md).

### Loops + Molecule Lab composer (→ Molecule Lab)

- Atoms/molecules files, scheduler, queue, console, Walkthrough, Validate/Dry-run; **Start all enabled** still exists (**CUT** in plan).
- Composer: drafts, conditions C1–C4; runtime skip C5 pending. [MOLECULE-LAB-CONDITIONALS.md](MOLECULE-LAB-CONDITIONALS.md).
- Persistent state via `tool_export`. [knowledge/TOWER-TOOL-EXPORT.md](knowledge/TOWER-TOOL-EXPORT.md).

### Harness

- `python -m idle_lab.harness …` — [HARNESS.md](HARNESS.md). [`lab-context.json`](../lab-context.json).

### Still not in POC (and mostly still true after redesign)

- Process injection / stealth / in-process LLM  
- Full finished Tower buy-priority product loop  
- Fully wired Current State + C5–C9  
- In-app auto-classify Observe shots  
- Inline JSON editors (files stay truth)  
