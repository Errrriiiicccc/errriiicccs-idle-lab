# Shape-first shell — implementation plan

**Status:** Phase 0 **greenlit** (2026-11-10) — execute Phase 0 only; later phases need their own go  
**Authority:** [VISION.md](../../VISION.md) · [shell/README.md](README.md) · [FEATURES.md](../../FEATURES.md) Target shell · [CUT-REFINE-KEEP.md](../hygiene/CUT-REFINE-KEEP.md)  
**Out of scope here:** new product vision, deep Current State schema, Trial IA polish, disk rename pass, in-app AI dispatch (parked unless a phase hard-depends — none do).

---

## 1. Goal

Rebuild the **operator shell** to match the agreed target: exclusive **Idle Lab** ↔ **Flight Deck**, Labs inventory (Info · LOL · Molecule Lab · Observation Lab), shared overlay primitives, Deactivate = Stop all — **UI skeletons first**, stubs OK, **no fake success**.

Engines underneath (scheduler, observation sessions, AI batches, LCO object maps, composer drafts, tool_export) stay callable; we **reshape chrome and IA**, then rewire gradually. Mega tabs (Bench · Observe · Missions · Loops) are destroyed as layout, not as capability overnight.

---

## 2. Non-negotiables (every phase)

| Rule | Source |
| --- | --- |
| Never show Idle Lab and Flight Deck at once | shell S15–S17 |
| Idle Lab open → **no** keyboard hotkeys (buttons only) | shell hard rules |
| Anything running → Idle Lab closed; Flight Deck only | S15 |
| Deactivate (`` ` ``) = Stop all; Deck starts deactivated | S27, S43 |
| Factory / fresh → Idle Lab on **Info**; then persist last tab | S3 |
| Live status in Idle Lab **chrome**, not inside Info | S20 |
| Shape-first: visible structure before full wiring; abstain/fail loudly over pretend-done | FEATURES / S25 |
| Observations are **deleted** by the user — not auto-archived | [archive/README.md](../../../archive/README.md) |
| Live app never loads `archive/` | archive rules |

---

## 3. Merge risk (working tree — ignore contents, notice conflict)

HEAD docs redesign tip: `b70f5c3`. Working tree currently has **large uncommitted** edits overlapping the shape-first blast radius:

- [`src/idle_lab/app.py`](../../../src/idle_lab/app.py), [`hotkeys.py`](../../../src/idle_lab/hotkeys.py)
- [`flight_deck/`](../../../src/idle_lab/flight_deck/), [`composer/`](../../../src/idle_lab/composer/), [`live_control/`](../../../src/idle_lab/live_control/)
- automations JSON (composer drafts, `flight_deck.json`, events/collections)
- new [`tool_export.py`](../../../src/idle_lab/tool_export.py), [`lco_focus.py`](../../../src/idle_lab/automations/lco_focus.py)

**Before Phase 0 coding:** park / commit / stash / branch that work so shell rebuild does not silently fight Molecule/LCO WIP. Plan assumes a clean baseline from `b70f5c3` **or** an explicit “merge WIP first” decision — not silent overwrite.

---

## 4. Current tree → target map

| Target surface | Ships-today home | Primary packages / files |
| --- | --- | --- |
| Idle Lab window | mega `CTkTabview` in `app.py` (Bench/Observe/Missions/Loops) | [`app.py`](../../../src/idle_lab/app.py) (~4k LoC god-shell) |
| Flight Deck | accordion + `flight_deck.json` U/O/C/N/A/M | [`flight_deck/window.py`](../../../src/idle_lab/flight_deck/window.py), [`shell.py`](../../../src/idle_lab/flight_deck/shell.py), [`actions.py`](../../../src/idle_lab/flight_deck/actions.py), [`keymap.py`](../../../src/idle_lab/flight_deck/keymap.py), [`hotkeys.py`](../../../src/idle_lab/hotkeys.py), [`automations/flight_deck.json`](../../../automations/flight_deck.json) |
| Info | (none — Home never shipped) | **new** tab module under shell |
| LOL | LCO via Deck U + `live_control/` | [`live_control/controller.py`](../../../src/idle_lab/live_control/controller.py), [`overlay.py`](../../../src/idle_lab/live_control/overlay.py), [`objects.py`](../../../src/idle_lab/live_control/objects.py) |
| Molecule Lab | composer window + Loops tab | [`composer/window.py`](../../../src/idle_lab/composer/window.py), Loops UI in `app.py`, [`automations/ui.py`](../../../src/idle_lab/automations/ui.py), [`scheduler.py`](../../../src/idle_lab/automations/scheduler.py) |
| Atom Create | Bench presets + LCO marks energy | [`presets.py`](../../../src/idle_lab/presets.py), [`recorder.py`](../../../src/idle_lab/recorder.py), [`molecule_marks.py`](../../../src/idle_lab/live_control/molecule_marks.py) |
| Observation Lab User | Observe tab | [`observation/`](../../../src/idle_lab/observation/), [`screen_map/`](../../../src/idle_lab/screen_map/) |
| Observation Lab AI mission | Missions tab | [`ai_batch/`](../../../src/idle_lab/ai_batch/) |
| Shared console | LCO console + Loops console | [`live_control/console_window.py`](../../../src/idle_lab/live_control/console_window.py), [`console.py`](../../../src/idle_lab/live_control/console.py) |
| Chrome / honesty | header in `app.py` | Anchor, Refresh/Restart, Stop all, Activity, tray [`tray.py`](../../../src/idle_lab/tray.py), [`single_instance.py`](../../../src/idle_lab/single_instance.py), [`settings_store.py`](../../../src/idle_lab/settings_store.py) |
| Harness | unchanged role | [`harness/`](../../../src/idle_lab/harness/), [`lab-context.json`](../../../lab-context.json) |

**Package rename** (`live_control`→lol, `events`→atoms, …) stays **parked** (hygiene D11). Operator labels in UI first; disk/import paths lag intentionally.

---

## 5. Architecture sketch (shape-first)

Introduce a thin **shell controller** (new module(s), not a rewrite of every engine):

```
idle_lab/
  shell/                  ← NEW (suggested)
    surfaces.py           # exclusive IdleLab | FlightDeck; run→Deck-only
    idle_lab_window.py    # chrome + tab host (Info/LOL/ML/OL)
    tabs/
      info.py
      lol.py
      molecule_lab.py
      observation_lab.py
    resume.py             # post-Deactivate continue / restart-wipe / Esc→Idle Lab
  overlay/                ← NEW or evolve live_control/
    primitives.py         # queue, marks, regions, hold-D describe, keyboard-queue chrome
    modes/
      lol.py
      atom_create.py      # distinct mode; shared primitives
```

Practical approach: **extract** tab bodies and surface rules out of `app.py` phase by phase; keep `App` as process owner (hooks, tray, Refresh/Restart) until the shell controller is stable. Do **not** big-bang rewrite runtime in Phase 0–1.

---

## 6. Phased waterfall

### Phase 0 — Preflight + surface skeleton (recommended first)

**Milestone M0:** Operator can see the *new* Idle Lab tab strip and Deck letter map as stubs; exclusive surfaces + deactivated Deck behave; old mega tabs are gone from the UI (engines may still exist behind stubs).

| Work | Detail |
| --- | --- |
| Baseline | Resolve dirty-tree merge risk (§3) |
| Surface FSM | Codify Idle Lab ↔ Deck exclusivity; running → withdraw Idle Lab; hotkeys off while Idle Lab focused |
| Idle Lab chrome | Anchor · Restart · Settings · live status strip (empty/stub OK) · tab host |
| Tabs (stubs) | **Info** · **LOL** · **Molecule Lab** · **Observation Lab** — placeholder panes (“not wired”) |
| Boot | Fresh → Info; persist last tab in settings |
| Flight Deck | Starts deactivated; only `` ` ``; top-level **L/M/O/S/X** + hold D stub; rewrite [`flight_deck.json`](../../../automations/flight_deck.json) letter map (CUT U/O/C/N/A/M product map) |
| Deactivate | Keep = Stop all; add **resume handle** stub (continue / restart-wipe / Esc → Idle Lab) |
| CUT UX (early) | Hide/remove **Start all enabled** control; remove **Mark** affordance from Deck catalog; no rename-on-stop prompt path in new OL stub |
| Tests | Extend [`tests/test_shell_escape.py`](../../../tests/test_shell_escape.py) + small surface-FSM unit tests (no Computer Use) |

**Touch points:** `app.py` (tab host + chrome), `flight_deck/*`, `hotkeys.py`, `settings_store.py` / `models.py` (last-tab + boot preference), `automations/flight_deck.json`, new `shell/` package, shell tests.

**Done when:** Launch shows Info (or last tab); switching tabs works; Activate Deck hides Idle Lab; Deactivate stops runners; L/M/O/S open stub windows or status “stub”; no Bench/Observe/Missions/Loops labels in UI.

**Risk:** High — `app.py` entanglement. Mitigate by stub panes that *call nothing* rather than partial wiring that lies.

---

### Phase 1 — Exclusive rules hardened + Info + Deck modes

**Milestone M1:** Hard rules feel real; Info is usable nested docs; Deck modes abandon accordion hotkeys; Settings **S** = boot preference only.

| Work | Detail |
| --- | --- |
| Info | Verbose nested outline per [info.md](info.md) — tree/accordion pick implement-time (S21); checklists + **links that switch tabs** |
| Live status | Wire Activity / files-changed into chrome strip (KEEP A5/A6) |
| Mode abandon | Entering LOL / floating ML / floating OL / Atom Create drops menu letters; Esc + `` ` `` per [flight-deck.md](flight-deck.md) |
| Floating Labs | **M** / **O** open lightweight Lab windows; Esc → Deck (skeletons OK) |
| Stop model | Idle Lab stop affordance ≡ Deactivate (REFINE A4); CUT separate Pause (A2); CUT Loops-local Reload (A3) |
| Expand remap | Move toward Settings (REFINE A8) — boot preference first (S52) |

**Touch points:** new Info content module (markdown or CTK nested frames), `flight_deck/shell.py` mode phases, `actions.py` action types for L/M/O/S, Settings UI slice.

**Done when:** Operator can learn the product from Info; Deck modes match settled letter map; exclusivity holds under manual harness checks ([HARNESS.md](../../HARNESS.md)).

**Risk:** Medium — Esc peel minutiae parked; don’t block on peel order perfection.

---

### Phase 2 — Shared overlay primitives + LOL skeleton

**Milestone M2:** One overlay foundation; LOL map tab + live enter; Atom Create mode **exists as distinct mode** with stub create/edit chrome (no silent “saved atom” unless really written).

| Work | Detail |
| --- | --- |
| Factor primitives | Queue UI, numbered marks, regions, arrows, hold-D describe, keyboard-queue box — extract from [`overlay.py`](../../../src/idle_lab/live_control/overlay.py) / [`molecule_marks.py`](../../../src/idle_lab/live_control/molecule_marks.py) |
| LOL tab | Interactive map: tree/list + miniature highlight ([lol.md](lol.md)); hotkey remap + conflict warn stubs |
| Live LOL | **L** / tab Start → Idle Lab hides; Deck up; Esc → entry surface; Anchor required |
| Atom Create stub | **C** / **E** chords; drag-place click indicator; W/S select; R/F reorder; save-on-exit **only when persist path real** — otherwise “needs save path” / warn |
| CUT arch | Stop treating LCO overlay as one-off (CUT C3 as architecture) |

**Touch points:** `live_control/*` → shared `overlay/` (or internal refactor keeping import aliases), Molecule Lab Atom entry that arms Deck mode, `hotkeys.py` mode routing.

**Done when:** LOL and Atom Create do not fork paint/describe code paths; fake success impossible for atom save.

**Risk:** Highest UX risk in the waterfall — place **after** shell exclusivity works; expect iteration on OCR create later.

---

### Phase 3 — Molecule Lab (Atom + Molecule) + console

**Milestone M3:** Molecule Lab is the home for atoms/molecules/Trial shell; Loops tab gone; Start-all dead; console is one object.

| Work | Detail |
| --- | --- |
| Embed + float | Idle Lab tab = full ML; Deck **M** = floating full ML ([molecule-lab.md](molecule-lab.md)) |
| Atom tab | Library + open Atom Create/Edit (Phase 2 mode) |
| Molecule side | Port [`composer/window.py`](../../../src/idle_lab/composer/window.py) flowing composer; C5 skip still stub OK |
| CUT | **Start all enabled** (E2); taxonomy product name (E6 → later org skins parked S30) |
| KEEP | Walkthrough, Validate/Dry-run, queue elevated (S28), interval engine |
| Console | Shared object: docked bottom when ML open; floating on Deck (S29) |
| Trial IA | **Parked** (S42) — skeleton labels only; no polish pass |

**Touch points:** `composer/*`, Loops sections of `app.py` / `automations/ui.py`, `walkthrough.py`, console modules, scheduler entry points (explicit packs only).

**Done when:** Operator builds/runs via ML only; Start-all absent; console not duplicated.

**Risk:** Medium-high — composer WIP in dirty tree; merge carefully. Representability of all atoms in creator (S41) can lag behind skeleton as long as JSON-only ghosts are labeled honestly.

---

### Phase 4 — Observation Lab (User + AI mission)

**Milestone M4:** One Lab, two tabs; Mark/rename-on-stop gone; catalog date groups; missions live as AI mission panes.

| Work | Detail |
| --- | --- |
| User tab | Capture modes (pointer / molecule / LOL); stop = `` ` `` only; review catalog Today/Yesterday/Last 7/The Past |
| CUT | Mark (G2); rename prompt on stop (G3); “Screen Map” product name (G4) |
| KEEP | Timeline, digest, Open folder, Notes, delete in review |
| AI mission tab | Center panes: Start · Mission view · Results; Export packet; probe materials; seeds via Refresh |
| CUT | Legacy Add feedback (H4); separate Missions tab |
| Evidence store | One store; dual-write Screen Map shape = internal debt until rename pass |

**Touch points:** `observation/*`, `screen_map/*`, `ai_batch/*`, Observe/Missions UI in `app.py`, Deck O actions, delete UX in review.

**Done when:** No Observe/Missions top-level; Mark/rename prompts gone; missions reviewable in-lab.

**Risk:** Medium — date-group on-disk layout open (implement-time); don’t auto-archive sessions.

---

### Phase 5 — Hygiene CUT demos → archive + docs sync

**Milestone M5:** Product story matches FEATURES Target shell; CUT demos out of live automations UX.

| Work | Detail |
| --- | --- |
| Archive moves | `ocr_ab_tick`, `minute_clip` / `stat_broll_5m`, `humanize_upgrade_loop` (+ noisy `composer_test_*` triage) → `archive/automations/…` + `REASON.md` + `_index.md` ([archive/README.md](../../../archive/README.md)) |
| Docs | Update FEATURES “Ships today”; LAYOUT/USAGE/smoke if they still name Bench/Loops; CONTINUATION active focus |
| Seeds | Keep useful AI-batch seeds; prune dead |
| Click logger | Bury in harness/dev (D3) — not a Lab |
| Rename pass | **Still parked** unless Eric schedules it with/after this phase |

**Touch points:** `automations/events|collections`, `presets/`, `archive/`, docs cascade, tests that referenced CUT demos.

**Done when:** Refresh never surfaces CUT flagship demos; archive policy followed; FEATURES ships-today ≈ shell.

**Risk:** Low if deferred until Labs exist — do not archive mid-Phase-0 and break harness without replacements.

---

## 7. Risk order (build this sequence)

1. **Exclusive surfaces + Deactivate** — wrong here poisons every Lab  
2. **Deck letter map / mode abandon** — hotkey collisions  
3. **Shared overlay + Atom Create** — highest UX / architecture fork risk  
4. **Molecule Lab embed + Start-all cut** — operator runway for atoms  
5. **Observation Lab IA** — evidence honesty (delete vs archive)  
6. **Archive CUT demos** — after paths exist so harness still has a story  

Parked items that must **not** reorder the waterfall: Trial IA polish, Current State deep schema, package rename, in-app AI dispatch, Esc peel perfection, post-observe Deck chrome.

---

## 8. CUT checklist (track through phases)

| CUT | Phase |
| --- | --- |
| Mega tabbed layout as product UI | 0 |
| Bench / Observe / Missions / Loops top-level labels | 0–4 |
| Separate Pause vs Deactivate | 1 |
| Loops-local Reload | 1 |
| Deck U/O/C/N/A/M map + tap-D | 0–1 |
| Start all enabled | 0 hide / 3 delete path |
| Mark bookmark | 0–4 |
| Rename-on-stop prompt | 4 |
| Screen Map as Lab name | 4 |
| Legacy Add feedback | 4 |
| Autoclicker as sibling Lab | never rebuild (→ Atom) |
| Flagship demo automations (I1–I3) | 5 → archive |
| Hard-coded LCO-only overlay architecture | 2 |

---

## 9. Acceptance bar (per phase)

- UI shows the target IA for that phase.  
- Unwired actions say **stub / not wired** — never green success.  
- Deactivate still stops everything that phase can start.  
- Harness/doctor still runs for untouched engines.  
- No load from `archive/`.  
- Docs touched only when ships-today claims change (Phase 5 primarily; Phase 0 may note “shell skeleton”).

---

## 10. Recommended next execution

**Phase 0 greenlit — execute now.** Phase 1 only after M0 is reviewable and Eric greenlights again.

Phase 0 deliverable for Eric to click:

1. Idle Lab opens on **Info** (stub copy OK).  
2. Tabs: Info · LOL · Molecule Lab · Observation Lab (placeholders).  
3. Activate Deck ↔ Idle Lab exclusive; hotkeys silent while Lab open.  
4. Deck top-level L/M/O/S stubs; old accordion letters gone.  
5. Deactivate = Stop all; resume stub visible.  
6. Start-all + Mark not offered.

**Before coding:** decide dirty-tree fate (§3). Prefer: commit or stash WIP → branch `shape-first-shell` from clean `main` → Phase 0.

---

## 11. Explicitly not in this plan

- Inventing new vision or Labs beyond the settled inventory  
- Wiring C5–C9 / full Current State  
- In-app LLM dispatch  
- Full `events`→`atoms` disk rename  
- Migrating all Bench `presets/` into atoms  
- Trial ↔ creator IA polish  
- External `idle-lab/docs` salvage
