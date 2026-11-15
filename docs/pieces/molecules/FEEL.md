# Molecule Lab / Atom Create — feel

**Status:** living feel doc (folded from 2026-11-15 chat). Todos → [WORKBOARD.md](../../WORKBOARD.md). Decisions → [decisions.md](decisions.md).  
**Purpose:** [VISION.md](../../VISION.md) — human judgment in → structured actuation out.

---

## Locked so far

### Job of this corner

Molecule Lab is where **intent becomes a runnable policy**.

- **Atom** = one teachable unit of sense/act (automation path, or phase map of “where the UI is”).
- **Molecule** = atoms wired with gates — when this, do that.
- Authoring + proving stay glued; artifacts stay file-backed and inspectable.

### Trial is a mode, not a third lab

Drop **Trial** as a sibling leaf under Molecule Lab.

- **Atom Lab** and **Molecule Lab** each get a **trial counterpart** (troubleshooting costume).
- Labs enter trial mode; they do not send you to a separate troubleshooting room.

### Gravity

| Mode | Question |
| --- | --- |
| **Atom trial** | Is this brick sound? (more of these — coherency before composition) |
| **Molecule trial** | Does this wall stand? (gates, order, skip/fail) |
| **Live** | Is the habit on, and what’s it doing right now? |

Both Atom and Molecule deserve trials. Atom-trial gets more use in general.

---

## Atom trial (by kind)

Both kinds open their **LOL representatives** so the operator sees on-screen truth — not desk-only readout.

| Atom kind | Trial behavior |
| --- | --- |
| **Automation** | Lab **runs** it; show evidence (shots, pass/fail, traces). |
| **Phase map** | **User** drives; the map is a navigation aid, not a script firing for them. |

---

## LOL costumes — Automation atoms

Same atom, two faces:

| Mode | LOL face |
| --- | --- |
| **Atom trial** | Full story — events in order via numbering; **green** active / **orange** upcoming / **gray** inactive. Represent **clicks, keys, drags, OCR**, etc. (today mostly clicks — expand). |
| **Live LOL** | Minimized glyph — e.g. Health→Gem = on/off symbol; scroll = arrow. No step parade. |

Trial teaches/proves the insides. Live is glanceable while hands are on the target.

---

## LOL costumes — Phase map atoms

Phase maps stay **richer than automation atoms even when live**, because navigation *is* the point — but balance:

**Show (operator affordances):**
- All **current clickables** for the active phase.
- **Transitions** only as the cue the human uses — e.g. `Q` icon to open Attack upgrade tab; scroll/fling glyph; tab-switch cue.

**Do not show (machinery):**
- Drag-to-top that starts a transition.
- OCR that confirms/aligns buttons after a move.
- Full scroll start/end geometry when a fling is only “go to next phase band.”

Example — Upgrade phase map:

1. Press **Q** → represent with **Q** icon (enter Attack upgrade phase).
2. Under the hood: drag up + OCR to confirm buttons → **not** drawn on LOL.
3. In-phase: only the **clickables**.
4. Further moves: scroll/fling / switch tabs → **scroll/fling (or tab) icon only**; phases reached this way may still nest inside the same parent phase story.

**Parked (besides the point for now):** how create UX expresses refined nested phases at the fidelity we want — revisit after feel is solid.

---

## Molecule trial

**Desk (Molecule Lab · trial mode):**
- Enter trial on the selected molecule (same desk, new costume).
- Run once / keep poking; unit under test is the **composition**.
- Evidence is **gate-aware**: which condition passed/failed, which atom ran or skipped, why it stopped — not only “step 3 clicked.”
- Edit gates/order with proof in hand.

**LOL during Molecule trial:**
- Opens the molecule’s on-screen story **through** its child atoms.
- Active child uses its **Atom trial** costume (automation step parade; phase map clickables + thin transitions).
- Molecule layer on top stays light: which branch / which atom is live — not a second full step parade.
- Gate block/skip must be obvious on LOL + desk (no silent no-op).

**Live (molecule as habit):**
- Molecule collapses to glanceable status: on/off, waiting on gate, maybe which child is hot.
- Child **automation** atoms use minimized live faces.
- Child **phase map** atoms keep affordance richness (clickables + thin transitions) — structural, not trial-only.

---

## Atom create/edit — ideal vs today

**Ideal:** teach one brick by hand on glass + queue; creator ≡ editor; kind gate → place → tweak → save; every kept atom reopenable (no JSON-only ghosts).

**Ships today:** skeleton of that idea — kind gate, place click/drag/key/OCR, queue + marks, edit reorder/spam/drag knobs, phase-map leaves + expand-on-save, save-on-exit. Demo, not product.

### Gaps blocking “perfectly representative”

1. **Creator ≠ editor in practice** — library browse + Run once; no solid “open this atom in Create.” Ghosts still JSON-only.
2. **Create doesn’t prove** — authoring and trial aren’t one loop; leave Create → run elsewhere.
3. **Still Deck-shaped** — accordion chords + “pause Deck” DNA; pocket mirrors, but feeling isn’t “mouse desk that owns teaching.”
4. **Glass incomplete** — clicks/drags/OCR yes; keys/depth thin; live vs trial costumes not wired; phase map doesn’t yet split affordance vs machinery on glass.
5. **OCR soft underbelly** — `needs_review` exists; guided text/color/shape authoring mostly doesn’t.
6. **Phase authoring ≠ Upgrade feel** — structure buildable; thin transition cues vs hidden machinery not first-class.
7. **Friction tax** — dialogs, naming/id, Esc/save peel, library vs create as two rooms.

### Unblock first — Create usable after expanded/collapsed reshape

Create is conceptually in-Lab but still **keyed off withdrawn Flight Deck** as keymap host. Pocket is stubby beyond kind gate. Until this is honest, QOL polish is hard to feel.

**Unblock track (before deep QOL):**

| Slice | Job |
| --- | --- |
| **U1** | Create stays **expanded**; never depends on peer Deck chrome. Pocket = sole chord surface; kill “pause Deck” copy. |
| **U2** | Pocket maps full Create/Edit/Phase-map leaves (not kind-gate only). |
| **U3** | Overlay + queue reliably show while Create owns mode; Esc peel + save/discard still works. |
| **U4** | Smoke: Create Atom → place → edit → save → Atom pane; reopen path stub at least. |
| **U5** | Then QOL + trial-mode glue. |

---

## Editor QOL (phase-map + automation) — locked direction

### Eric — copy across phases

**Copy an event** from the same phase or another phase (paste into active phase / selection).

Expand:

- Copy **one** event or a **multi-select series**.
- Paste = duplicate into **active phase** (or chosen target phase), preserving type + params; new ids; clear “stale phase lock” until re-bound.
- Cross-phase copy is the fast path for “same buy button, different tab band.”
- Optional later: **duplicate phase** (copies all in-phase events + asks which transitions to keep).

### Phase event roles (editor) — settled direction 2026-11-15

When authoring **inside a phase**, every event is one of three roles. Nested phases are allowed under within-phase moves, but **soft vs hard** decides what Molecule Lab must care about.

| Role | Meaning | Example |
| --- | --- | --- |
| **In-phase** | Act/sense inside the current phase; does **not** change phase | Click Bounce Shot while Attack is open |
| **Soft phase change** | Nested / within-parent navigation (same menu story) | Scroll/fling through Attack tab bands |
| **Hard phase change** | Whole-menu (or equivalent) shift — sibling surfaces under a parent | `M` → menu expand → **Cards** *or* **Modules** |
| **Hard exit / other** | Hard leave away from this phase tree | Close Cards; unexpand menu; leave to gameplay |

*(Exit/other is a hard change with outbound destination — same hardness, different molecule treatment.)*

#### Soft vs hard — Molecule Lab representation

**Soft changes are not separate molecule actions.** Pathfinding through them is assumed when you name the target in that phase.

- Author does **not** write: `Q → Attack → scroll → scroll → scroll → Bounce Shot`
- Molecule sees: `Q → Attack → Bounce Shot`  
  Scrolls (and align OCR / drag-to-top machinery) live in the phase map; the molecule does not list them.

**Hard sibling changes are real molecule choices.** Cards vs Modules are distinct phases the policy may pick.

- e.g. `M → menu expand → Cards` **or** `M → menu expand → Modules`
- Molecule Lab represents these as different branches / next steps — not collapsed away.

**Hard exit / other — assumed, not authored in the molecule.** When the next atom/molecule needs another surface, the lab infers teardown.

- e.g. after Cards work, next intent is `Q → Attack buys`  
  Molecule understands: exit Cards → unexpand menu → then `Q`.  
  Author does not hand-write that exit chain as molecule steps.

#### Editor UX (direction)

- In-phase / soft / hard(-exit) marked distinctly on queue + glass (glyph + color; hold-D spells role + from→to).
- Soft transitions: editable and trial-visible in the **phase map**; collapsed in **molecule** view.
- Hard siblings: linked in phase tree **and** offered as molecule-facing edges.
- Hard exits: bound in the map for runtime pathfinding; molecule UI does not require listing them.
- Live LOL still shows thin operator cues only; machinery stays under the transition, hidden live.

### Editor QOL — full descriptions (**all keep** — Eric 2026-11-15)

**Copy / structure**

1. **Copy across phases** — Duplicate selected event(s) into the same phase or a different one. Keeps click/key/OCR params; you re-bind role/target if needed.
2. **Duplicate step (same phase)** — One-chord clone in the *current* phase (no “pick destination”). Faster local iterate than full copy.
3. **Move to phase…** — Re-home selected event(s) into another phase **without** leaving a duplicate (copy = leave original; move = relocate).
4. **Multi-select + bulk** — Grab several queue items at once; bulk delete, copy, move, or set role (in-phase / soft / hard / exit).
5. **Stamp / template across phases** — Place one click (or small set), then stamp it into a *list* of phases (e.g. same buy affordance on several tab bands). Stronger than repeating copy.
6. **Duplicate phase** (later) — Clone a whole phase node (its events + optional transitions) as a starting point for a sibling band/menu.

**Phase roles / links**

7. **Role picker on event** — In edit, every event sets: **in-phase | soft change | hard change | exit**. First-class in the phase-map editor (your three + soft/hard split).
8. **Transition binder** — UI: selected event(s) → set role + **target phase** (soft = nested within parent; hard = sibling menu; exit = outbound). Makes from→to explicit, not implied.
9. **Linked machinery group** — Under a soft/hard transition in the queue, collapse the guts (drag-to-top, align OCR) as a nested group. Top row = operator cue; children = machinery. Matches live-glass “hide machinery.”
10. **Bidirectional highlight** — Select a transition event → phase tree lights **from → to**; select a phase edge → queue lights the bound events. So links are visible both ways.

**Aim / sense friction**

11. **Replace place** — Keep the step’s settings (spam counts, drag speed, OCR kind); only re-drop the glyph or region on the game. Fix bad aim without rebuilding the step from scratch.
12. **Needs-review filter + jump** — Filter the queue to unfinished OCR / flagged steps; jump to next needs-review. Soft underbelly stays findable.
13. **Key capture without modal** — When assigning a key step, press the key on glass/pocket without a blocking dialog box when it’s safe to do so.

**Library ↔ Create loop**

14. **Reopen from library** — Select an atom → **Edit** loads it into the same Create/Edit flow from disk. Creator ≡ editor for real (today you mostly only Create new + Run).
15. **Ghost audit** — For library rows marked “JSON-only / needs creator”: try open in creator, or show *which* step kinds the creator can’t represent yet. No forever silent ghosts.
16. **Diff on reopen** — If the file on disk (or expand-on-save child automations) drifted since last edit, show a short “what changed” before you save over it.

**Prove while authoring**

17. **Trial from Create (draft trial)** — Prove the **current unsaved draft** (run automation + evidence, or navigate phase map on LOL) without save → library → run. Author and prove stay one loop.
18. **Phase home + active always visible** — Queue chrome always shows home phase, active phase, active group so you don’t get lost in a deep phase tree while placing.

---

## Unblock — Atom Create/Edit on Idle Lab (active)

**Goal:** Create/Edit is a first-class **expanded Idle Lab** mode — not a Deck leftover. This pass defines how it *looks/feels* on the Lab; QOL 1–18 and trial-glue come after it’s touchable.

**After this:** Atom Lab from first open → library / workstreams / menus (separate round).

### Draft shape (critique next)

| Piece | Role while Create/Edit is open |
| --- | --- |
| **Costume** | Stays **expanded** (not collapsed like LOL live). |
| **Left rail** | Still visible; Atom leaf selected; Create is a **mode on top**, not a new rail leaf. |
| **Middle desk** | Create/Edit **authoring face** (kind gate → queue summary / phase tree / edit details) — mouse can work here, not only chords. |
| **Hotkey pocket** | Full Create/Edit/Phase-map leaves when we get there; sole chord surface; no “pause Deck” copy. **Build last** among unblock work — Eric 2026-11-15. |
| **Glass** | Atom Create overlay (queue + glyphs) on the anchored game — shared grammar with LOL, distinct mode. |
| **Esc** | Peel inward (place → edit → create root → save/discard → Atom Lab). |
| **`` ` ``** | Deactivate / Stop all (global) — **not** “pause Deck.” |

**Shape:** agreed (pocket meaning correct; pocket polish last).

**Hard rule — Create lives in Idle Lab only.** No separate Atom queue window, no peer Deck chrome, no float “shenanigans.” Overlay on the anchored game + middle desk + pocket (later) inside the one Idle Lab window.

**Build order (revised):** U1 costume/mode honesty → U3 overlay+queue+Esc → U4 smoke place→save (+ reopen stub) → U5 QOL/trial glue as needed → **U2 pocket maps last**.

### Create mode — what you see / do

**One window:** Idle Lab expanded. Create is a mode on Molecule Lab · Atom. No separate windows.

| Surface | Role |
| --- | --- |
| **Glass (on game)** | Place and aim. Shared overlay grammar with LOL; Create mode. **Agreed.** |
| **Pocket** | Chords (build last). **Agreed.** |
| **Esc** | Hotkey peel/exit — **not** sole exit. Primary exit = **button in middle-desk flow**. |
| **`` ` ``** | Stop all. |
| **Middle desk** | Main discussion — three-pane Create/Edit (below). |

#### Middle desk — three panes (leaning — Eric 2026-11-15)

Not fully confident on chrome yet; working bet:

| Pane | Job |
| --- | --- |
| **Left — Create** | Drill nested buttons / text until the thing you want to **add**. |
| **Middle — Specifics** | Params for **current** selection (just created or picked on the right). e.g. click intervals/spam; **phase** defaults to the phase selected on the right. |
| **Right — Queue / phase map** | Whole atom. Select phase or event → middle shows editable fields. Nothing selected → pick here to start editing. |

**Exit** = explicit desk control (Save / Done / Leave); Esc mirrors it.

```
┌─────────────┬──────────────────┬────────────────────┐
│ Create      │ Specifics        │ Queue / phase map  │
│ (drill add) │ (edit selection) │ (select → middle)  │
└─────────────┴──────────────────┴────────────────────┘
              + glass on game for place/aim
```

#### Specifics — events vs phases

**Event:** role (in-phase / soft / hard / exit) · target if change/exit · type params (click/drag/key/OCR) · phase membership (default = right-pane selected phase).

**Phase:** name/parent/home · inbound soft/hard changes into sub-phases or siblings · exit paths (bound for pathfinding; molecule assumes) · contents as tree (in-phase + nested soft bands).

Glass places geometry; middle desk owns **classification and links**.

#### Left pane — Create drills (draft 2026-11-15)

**Critique of current (Deck accordion) nesting:**

- **Edit (E) as a Create sibling is wrong** for three-pane desk — select lives on the right; params live in the middle. Left should only **add**.
- **Playbook as a mode rewrite** fights the desk: Tower shortcuts should be an add-source under Create, not a whole menu swap.
- Phase map roots **G/H/T/S/R/A/E/X** are author-taxonomy, not operator intent — too many peer doors; soft/hard/exit aren’t first-class.
- **Raw Actuation (A)** duplicates Basic Gesture and invites junk beside Targets/Scrolls.
- Number-hotkey “set active phase” belongs on the **right** (select phase), not buried in Create drills.
- Expand preview (X) is inspect — belongs near right/middle, not Create add.

**Principle:** Left = *what do I want to add?* → place on glass → middle opens specifics (role/target/params). Right = truth + selection.

**Automation — left Create (liked; Eric 2026-11-15):**

1. Kind badge.
2. Add → **Click** | **Drag** | **Key-press** | **Sense** (see vocab) | **From playbook…**
3. **Playbook** is a *catalog* you can grow/prune later — not forever-hardcoded Deck leaves. Open: where that catalog lives (file vs in-app editor).
4. Desk chrome: **Done / Save**. No Edit on left.

**Phase map — left Create (revised after Eric 2026-11-15):**

Same **event palette** under every role door — events are events (click/buy/equip were always just clicks with labels):

```
Add
├── Phase
├── In-phase event     → Click | Drag | Key-press | Sense
├── Soft change        → same palette (often a *sequence* + conditions)
├── Hard change        → same palette (sequence + conditions)
│                        target = deeper nested phase OR previous phase (exit)
└── From playbook…     → same catalog concern as Automation
```

- **No separate Exit door** — exit = hard change whose target is a previous/outer phase.
- **No Key group / Region·prove as Create roots** for now — explain or fold later (see below).
- Soft/hard changes may be **multi-step procedures with conditionals** (scroll → sense → if miss scroll → if hit click), not single glyphs.

#### Vocabulary — “OCR” vs what we mean

**OCR** (optical character recognition) = one *instrument*: read **text** from pixels. Too narrow for the product.

Better umbrella (operator language): **Sense** — look at a region of the screen and produce a typed result (or abstain).

Instruments under Sense (sense ladder still applies): text/OCR, icon/template, color/panel, later structured export when it replaces pixels.

**Sense jobs — locked lean (Eric 2026-11-15):**

| Job | Meaning | Scope |
| --- | --- | --- |
| **Collect** | Grab data → **record** for later use | Often feeds **molecules** / Current State later (e.g. wave → midgame vs endgame) |
| **Check** | Grab data → **branch / confirm** inside this atom (or immediate molecule gate) | Local — e.g. “am I on the right upgrade button?” while authoring Attack buys |

Check may **yield aim point** when hit (old Locate folded in). No separate Locate Create job.

**Key group** → **hard change** (upgrade tab keys, menu-expand map).

#### Soft vs hard (molecule + editor)

| | Soft | Hard |
| --- | --- | --- |
| **Story** | Bands inside one parent phase (scroll Attack list) | Deeper menu **or** previous phase (exit) |
| **Molecule** | **Never shown** — auto-routed forward/reverse | Shown; exits assumed between intents |
| **Editor** | Linked chain + reverse + optional **type** (e.g. fling) | Target = child or ancestor |

#### Soft-change authoring rules (from Upgrade-tab story)

1. **Chain** — soft bands link; top → deep may need N softs in order.
2. **Reverse** — every soft change has a backwards twin; Create lets you **test forward then reverse** easily.
3. **Typed softs** (e.g. **fling**) — select softs → tag as one major type: “this fling, from anywhere in the menu, lands on soft-band X of this phase.”
4. **Test in Create** — run/scrub a soft drag on glass until scroll amount feels consistent before placing the next six clicks.

#### Multi-step changes + conditionals

Soft/hard may be procedures: `scroll → check → if miss scroll → if hit click(at aim)`. Specifics show sequence + conditions when a change is selected.

#### Walkthrough — Upgrade tabs → buys (target UX)

1. Atom Create → **Phase map**.
2. Three phases: Attack / Defense / Utility (+ hard enters via tab keys as hard changes).
3. Per phase: setup to known top (e.g. fling/drag to top) — click + drag params as needed.
4. **Cut here** → molecule already sees **three outputs**: Attack open / Defense open / Utility open (hard surfaces). Soft guts hidden.
5. Re-edit → Attack: place six named buy clicks → add soft drag → **test on glass** → six more named clicks → repeat to bottom.
6. Link softs into a chain; define reverses; optionally tag a **fling** type that jumps to a known soft-band.
7. Molecule: pick “buy Bounce Shot” (or any in-phase event under Attack) without listing scrolls — router uses soft forward/reverse automatically.

#### Extrapolation made visible

Create must show **what the molecule will see** vs **what stays inside the atom** (hard outputs + named in-phase events vs soft chain / setup machinery). Not only the queue of everything you placed.

#### Atom complexity (reframe)

Atoms are **not** “one click.” They are the **teachable unit of a surface** — can be a rich phase map. Molecules **string those units** into something more complex. Smallest gestures live *inside* atoms; atoms are still the brick.

#### LOL — how to show a complex phase-map atom (proposal)

Don’t draw the whole soft chain at once.

| Mode | Glass shows |
| --- | --- |
| **Live** | **Current soft-band only** — up to ~6 clickables + thin hard-enter cues (`Q`, etc.) + one soft glyph (scroll/fling) if a typed soft exists. No full band parade. |
| **Create / Atom trial** | Band you’re editing: numbered clicks; selected soft as rubber-band; **band depth** cue (e.g. band 2/5); forward/reverse test highlight; optional “molecule preview” strip: hard outputs + event names molecule will list. |
| **Fling type** | Single fling mark → destination soft-band name/index, not every intermediate scroll. |

Reasonable = **progressive disclosure by current band + role**, matching earlier affordance-vs-machinery rule. Complexity lives in Create desk (right tree + specifics); glass stays glanceable.

#### Shelved / folded

- Key group → hard change.
- Region/prove → Check on phase or change sequence.
- Locate → Check + yield aim.

---

## Tracking

Open work, archive, and build order: **[WORKBOARD.md](../../WORKBOARD.md)**.  
Decision IDs: [decisions.md](decisions.md). Shell Molecule Lab doc still needs a rewrite pass ([../shell/molecule-lab.md](../shell/molecule-lab.md) — drop Trial leaf, Idle Lab Create).
