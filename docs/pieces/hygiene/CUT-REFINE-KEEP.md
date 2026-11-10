# Cut / Refine / Keep — shell-era pass

**Status:** **Agreed** (Eric 2026-11-10) — leans accepted. Historical → [archive/](../../../archive/README.md).

**Meanings**

- **CUT** — Do not rebuild in the new shell; drop from UX; move archaeology to `archive/` (or delete junk).  
- **REFINE** — Keep the *job*; reshape into Idle Lab Labs / Flight Deck / shared overlays.  
- **KEEP** — Remains part of the product; rename OK.

---

## A. Shell / windows / chrome

### A1. Mega tabbed Idle Lab (Bench · Observe · Missions · Loops in one window)
**Intent:** One window for everything after the clicker fork.  
**Lean: REFINE → rebuild.** Destroy this layout; recreate Idle Lab as mouse dual of Deck with Info + Labs only (Molecule, Observation, LOL tab, …). Same product home, new IA.

### A2. Separate Pause / Stop beside Deactivate
**Intent:** Fine-grained stop vs idle companion.  
**Lean: CUT.** Deactivate = Stop all; only `` ` `` when idle.

### A3. Loops-local Reload button
**Intent:** Reload automations JSON without full Refresh.  
**Lean: CUT as separate control.** Global Refresh only.

### A4. Stop all (chrome button)
**Intent:** Abort everything from Idle Lab without Deck.  
**Lean: REFINE.** Keep a clear stop affordance on Idle Lab chrome if useful, but behavior = same as Deactivate (not a third stop model).

### A5. Auto / Supervised mode chip
**Intent:** Attended vs freer auto; honesty.  
**Lean: KEEP** (Settings or chrome later). Fits attended vision.

### A6. Activity pulse + files-changed badge
**Intent:** Know disk changed → Refresh.  
**Lean: KEEP.**

### A7. System tray + single-instance
**Intent:** Find the app; one process.  
**Lean: KEEP.**

### A8. Expand-key remap beside Anchor (today)
**Intent:** Remap `` ` ``.  
**Lean: REFINE → Settings.** Boot preference already in Settings; remap can live there too eventually.

---

## B. Flight Deck (legacy accordion)

### B1. Letter map U/O/C/N/A/M + digit leaves in `flight_deck.json`
**Intent:** Hotkey start everything without opening Lab.  
**Lean: CUT map; REFINE job.** Replace with L/M/O/S redesign; rewrite catalog file in waterfall.

### B2. Tap-D for accordion descriptions
**Intent:** Explain leaves.  
**Lean: CUT tap-D.** Hold D for describe everywhere (shared overlay principle).

### B3. X collapse menus
**Intent:** Back out of accordion.  
**Lean: KEEP.**

### B4. Deck Close → quit confirm when Lab hidden
**Intent:** Esc peel to exit app.  
**Lean: KEEP** (peel details implement-time).

### B5. I = open Lab / A = anchor / Enter = re-anchor from Deck
**Intent:** Bootstrap without Idle Lab chrome.  
**Lean: REFINE.** Keep jobs; fit new deactivated/activated Deck + boot preference (Idle Lab factory default).

---

## C. Live Control / LOL

### C1. LCO product (object-map overlay, hold D, fire modes, Esc exit)
**Intent:** Hands on Tower UI without leaving the run.  
**Lean: REFINE → LOL.** Same job; shared overlay objects with Atom Create; map tab in Idle Lab.

### C2. LCO Troubleshoot (U→2)
**Intent:** Debug overlay/session.  
**Lean: REFINE or bury.** Keep as LOL power tool if still useful; not flagship.

### C3. Hard-coded LCO-only overlay UI
**Intent:** Ship fast.  
**Lean: CUT as architecture.** Factor shared primitives (queue, marks, hold D, regions).

---

## D. Bench / presets / “Autoclicker”

### D1. Bench workspace tab (record/play presets UI)
**Intent:** Classic macro recorder.  
**Lean: CUT as top-level Lab.** Job moves to Molecule Lab → Atom Create (visual).

### D2. Preset files under `presets/` (gem box, currency toggle, sample three points, humanize loop, …)
**Intent:** Saved click macros; demos; Deck one-shots.  
**Lean: REFINE later / don’t block.** Not important to migrate now; eventually representable as atoms or archive. Don’t make Bench UI come back for them.

### D3. Click logger (WAVE/SIGNAL window)
**Intent:** Offline harness for OCR A/B without Tower.  
**Lean: REFINE → bury in harness/dev.** Not a user Lab. Keep for tests if useful.

### D4. Humanize Off/Light/Medium/Heavy
**Intent:** Less robotic playback.  
**Lean: KEEP** (Settings or run options). Not stealth.

### D5. Foreground vs background click methods
**Intent:** Click through different Windows input paths.  
**Lean: KEEP** as atom/runtime capability; not a Bench tab.

---

## E. Loops tab / scheduler UI

### E1. Loops workspace (Atoms/Molecules browse + Start all + Run pack + …)
**Intent:** Operate file-backed automations.  
**Lean: CUT tab; REFINE into Molecule Lab.** Library + Trial + queue + walkthrough live in ML.

### E2. Start all enabled
**Intent:** Fire every `enabled: true` atom on intervals.  
**Lean: CUT.** Explicit molecule packs only.

### E3. Walkthrough
**Intent:** Guided human-paced tour of a molecule.  
**Lean: KEEP** inside ML Trial.

### E4. Validate / Dry-run
**Intent:** Catch bad JSON; plan without clicking.  
**Lean: KEEP** (save path + Trial).

### E5. Queue + Console (Loops-owned)
**Intent:** See scheduler truth + logs.  
**Lean: REFINE.** Elevated conditional queue; shared console (docked with ML, floating on Deck).

### E6. Taxonomy.json as product concept
**Intent:** Folder labels for long lists.  
**Lean: CUT name; REFINE into ML library org** (three skins later in-app).

### E7. Details Basic/Detailed panel
**Intent:** Read what an atom/molecule does.  
**Lean: KEEP** beside library / flowing ML UI.

### E8. Interval scheduler + overdue policies + traces/failure packs
**Intent:** Reliable timed jobs + debug.  
**Lean: KEEP** as engine under Trial/runs.

---

## F. Molecule Lab (composer today)

### F1. Composer window + expand-to-disk + condition authoring (C1–C4)
**Intent:** Build molecules without hand JSON.  
**Lean: REFINE** into ML Molecule side + Atom tab; flowing focus; shape-first gates.

### F2. Runtime gate skip still stub (C5)
**Intent:** Conditions actually skip.  
**Lean: KEEP as goal;** shape in UI first, wire later.

---

## G. Observe / Screen Map

### G1. Observe tab + observation sessions (timeline + shots)
**Intent:** Record playing the game.  
**Lean: REFINE → Observation Lab User tab** (+ molecule/LOL capture modes).

### G2. Mark bookmark (O→2)
**Intent:** Force a keyframe.  
**Lean: CUT.**

### G3. Rename prompt on stop
**Intent:** Title the batch.  
**Lean: CUT prompt.** Rename only in review.

### G4. “Screen Map” as product name / dual-write story
**Intent:** Shared shot folders for Missions + Observe.  
**Lean: CUT name; REFINE store.** One evidence store; date-grouped catalog.

### G5. View all / Open folder / Notes on batches
**Intent:** Review + escape hatch + folklore.  
**Lean: KEEP** inside OL review.

### G6. DIGEST.md / observation.json
**Intent:** Readable session summary.  
**Lean: KEEP.**

---

## H. Missions / AI batches

### H1. Missions workspace tab
**Intent:** Run AI-authored step batches.  
**Lean: CUT tab; REFINE → Observation Lab AI mission tab** (Start / Mission view / Results).

### H2. Probe materials (QUESTION/ACCEPTANCE/iterations)
**Intent:** Iterate until acceptance.  
**Lean: KEEP.**

### H3. Export packet
**Intent:** Portable brief for external AI.  
**Lean: KEEP.**

### H4. Legacy Add feedback
**Intent:** Old comments path.  
**Lean: CUT.** Notes only.

### H5. Seed examples (`examples/ai-batches/`)
**Intent:** Starter probes + OCR bench.  
**Lean: KEEP** via Refresh seed policy; prune dead seeds later if needed.

### H6. Offline OCR fixture bench mission
**Intent:** Perception regression without Anchor.  
**Lean: KEEP** as special AI mission.

---

## I. Demo / POC automations & content

### I1. `ocr_ab_tick` + click-logger A/B demo
**Intent:** Prove OCR→branch→preset without Tower.  
**Lean: CUT from product story; KEEP as optional harness fixture** if tests need it.

### I2. `minute_clip` / `stat_broll_5m` ffmpeg clip demos
**Intent:** B-roll / clip naming POC.  
**Lean: CUT from flagship UX.** Engine can keep clip action if useful later.

### I3. `humanize_upgrade_loop` + preset
**Intent:** Show Humanize on a buy path.  
**Lean: CUT as recommended demo.** Humanize itself stays (D4).

### I4. Mass `composer_test_*` / smoke buy atoms
**Intent:** Molecule Lab / LCO placement experiments.  
**Lean: REFINE inventory later.** Keep what still teaches Tower buys; archive noise during waterfall—not a UX feature.

### I5. Persistent state via `tool_export` (`stat_collect`)
**Intent:** Numbers without bad HUD OCR.  
**Lean: KEEP** (sense ladder).

### I6. HUD OCR recovery paths for wallets (paused perception program)
**Intent:** Read coins/etc from screen.  
**Lean: CUT as default driver.** OCR remains for on-screen-only cues / Atom OCR events; no return to hallucinating wallet OCR as primary.

---

## J. Docs / research / archive

### J1. External `idle-lab/docs/` as live vision
**Intent:** Pre-fork concept home.  
**Lean: CUT authority** (already). Ignore unless mining a fact.

### J2. Research lanes L1–L10 as status
**Intent:** Analogue deep-dives.  
**Lean: KEEP as cite-only;** don’t treat as ships-today.

### J3. FEATURES / USAGE / SMOKE / LAYOUT vs new shell
**Intent:** Operator truth.  
**Lean: REFINE** — rewrite to match pieces/shell after this pass (or at shape-first start).

### J4. IMPLEMENTATION.md milestones
**Intent:** Early changelog.  
**Agreed: ARCHIVE** → `archive/docs/IMPLEMENTATION.md`.

### J5. HANDOFF-OCR / old prompts
**Intent:** Chat paste targets.  
**Agreed: ARCHIVE** → `archive/docs/HANDOFF-OCR.md`.

---

## K. Rename pass (not cut, but hygiene)

### K1. Disk/package names (`events`→atoms, `collections`→molecules, `ai_batch`→missions, `live_control`→lol, …)
**Intent:** Match operator language.  
**Lean: KEEP job — do as deliberate rename pass** with shape-first or after (D11). Not a CUT of features.
