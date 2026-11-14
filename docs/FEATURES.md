# Features

**Purpose:** [VISION.md](VISION.md) · **Cascade:** [README.md](README.md) · **Shell plan:** [pieces/shell/](pieces/shell/README.md) · **Hygiene:** [pieces/hygiene/CUT-REFINE-KEEP.md](pieces/hygiene/CUT-REFINE-KEEP.md)

This file has two layers on purpose:

1. **Target shell** — agreed redesign (shape-first code aims here).  
2. **Ships today** — what the running app is after the shape-first waterfall.

Day-to-day chat focus: [CONTINUATION.md](CONTINUATION.md).

---

## Target shell (direction 2026-11-13 — docs lead code)

### Surfaces

| Surface | Role |
| --- | --- |
| **Idle Lab** | The app. **Expanded** = mouse desk (left file-tree labs + hotkey pocket + action pane). **Condensed** = skinny status/chords when LOL/Observation owns focus (Steam Play morph). |
| **Hotkey Flight Deck** | In-Lab pocket only — never a peer window. Expected-action chords for current focus; remappable open/close later. |
| **Labs** | Info, LOL, Molecule, Observation in the tree. |

Hard rules: `` ` `` **Deactivate = Stop all**; LOL Esc → confirm on anchored screen; pocket never steals action-space; condensed@LOL = outside chords + status (glass owns LOL keys).

Detail: [pieces/shell/README.md](pieces/shell/README.md), [pieces/shell/FEEL.md](pieces/shell/FEEL.md). Historical peer-Deck writeup: [pieces/shell/flight-deck.md](pieces/shell/flight-deck.md).

### Idle Lab labs

| Lab | Job |
| --- | --- |
| **Info** | Nested docs / onboarding (not a Feel Lab) |
| **Live Overlay Lab** | Interactive target map + live hands → **condensed** |
| **Molecule Lab** | **Atom** create/edit · **Molecule** compose · **Trial** — mouse desk + pocket |
| **Observation Lab** | User capture/review + AI mission → **condensed** |

No separate Bench, Loops, Missions, or Autoclicker top-level tabs. No peer Flight Deck.

### Skins / feel (target)

- Multiple **themes** as real Idle Lab skins (from Feel Lab keep-list).
- Omit Structure experiments; omit Info specimen-tray as product surface.

### Sense / state / hygiene (target)

- Sense ladder: structured source → title-native hooks → pixels/OCR ([VISION §4.3](VISION.md)).
- Current State is core (soft-hold vs shell reshape — [CONTINUATION.md](CONTINUATION.md)).
- Deprecated demos/docs → [archive/](../archive/README.md); observations are **deleted**, not auto-archived.
- Full disk/package rename after shell shape stabilizes ([pieces/hygiene/](pieces/hygiene/README.md)).

### Build rule

Docs for this reshape before coding waterfall. Show UI skeletons/stubs before full wiring — no fake success.

---

## Ships today

Phases **0–5** shape-first shell plus **costume skeleton (slice 1)**.

### Global chrome

- Single instance; tray; Anchor; Refresh / Restart / Deactivate (= Stop all); Activity + files-changed; Auto/Supervised; Humanize Off default.
- **Expanded Idle Lab:** left Labs tree + **Hotkey flight deck** pocket + action pane (existing lab bodies). No **Open Flight Deck** button.
- **Condensed:** same window shrinks on LOL / Observation (or **Preview condensed**); outside chords + status; expand when that mode ends.
- Peer `FlightDeckWindow` still exists **withdrawn** for hotkey/runtime compatibility — not a user-facing surface.
- Boot always opens **expanded** Lab (Settings “Flight Deck” boot preference ignored for now).
- Contract: [REFRESH-RESTART.md](REFRESH-RESTART.md).

### Flight Deck (legacy runtime, not chrome)

- Accordion keymap / Atom Create-on-Deck paths still exist under the hood ([`automations/flight_deck.json`](../automations/flight_deck.json)).
- **M→2 Atom Lab** float · **M→3 Create Atom** kind gate still Deck-modal until pocket maps land.
- Live overlay: object map, hold D describe, Esc exit → Lab **expands**. [LIVE-CONTROL-OVERLAY.md](LIVE-CONTROL-OVERLAY.md).

### Idle Lab Labs

| Lab | Ships |
| --- | --- |
| **Info** | Nested outline + tree links |
| **Live Overlay Lab** | Map list + Start live → **condenses** Lab |
| **Molecule Lab** | **Atom** library + LOL coverage · Atom Create still via Deck path · **Molecule** composer · **Trial** |
| **Observation Lab** | **User** capture/review · **AI mission** — start **condenses** Lab |

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

### Feel Lab (sandbox on disk)

- Still runnable: `python -m idle_lab.feel_lab`. Product direction: fold **themes → Idle Lab skins**; sandbox not required.
- [pieces/shell/FEEL.md](pieces/shell/FEEL.md).

### Still not finished (honest stubs / parked)

- **Next slices:** LOL Esc confirm on glass · live pocket chord maps · retire peer Deck window · skins  
- Atom Create still Deck-modal · Current State + C5 · package rename · in-app AI dispatch  
- Process injection / stealth / in-process LLM  
- Fully finished Tower buy-priority product loop · C5–C9  
