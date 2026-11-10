# Continuation handoff

**Errriiiccc's Idle Lab** — `c:\DEV\Projects\Cursor\errriiicccs-idle-lab`

**North star:** [VISION.md](VISION.md)  
**Cascade:** [README.md](README.md) · [../AGENTS.md](../AGENTS.md)  
**Redesign (docs complete):** [pieces/README.md](pieces/README.md) · shell [pieces/shell/](pieces/shell/README.md) · hygiene [pieces/hygiene/CUT-REFINE-KEEP.md](pieces/hygiene/CUT-REFINE-KEEP.md) · [archive/README.md](../archive/README.md)  
**Target vs code:** [FEATURES.md](FEATURES.md)

## Active focus (2026-11-10)

**Phase 0 greenlit.** Shape-first shell — execute **Phase 0 only** from:

→ **[pieces/shell/SHAPE-FIRST-PLAN.md](pieces/shell/SHAPE-FIRST-PLAN.md)** (§6 Phase 0 · §10 deliverable)

Do **not** treat legacy Bench/Loops/Missions/LCO naming in running code as the plan — FEATURES “Target shell” + pieces/shell win. Do **not** start Phase 1+ until M0 is reviewable and Eric greenlights the next phase.

**Chat contract:** [REFRESH-RESTART.md](REFRESH-RESTART.md) — data → Refresh; code → Restart.  
**Test:** [HARNESS.md](HARNESS.md) · [`lab-context.json`](../lab-context.json).

**Before coding Phase 0:** resolve dirty-tree merge risk (plan §3) — park/commit/stash/branch WIP so shell rebuild does not fight Molecule/LCO edits. Prefer clean baseline from `b70f5c3` or an explicit “merge WIP first” decision.

## What the plan locked (short)

- Idle Lab ↔ Flight Deck exclusive; Deactivate = Stop all; factory boot Idle Lab / Info then last tab  
- Labs: Info, LOL, Molecule (Atom create on Deck), Observation (User + AI mission)  
- Shared overlay primitives; Atom Create distinct from LOL; archive for deprecated; observations delete  
- CUT list agreed (Start-all, Mark, mega tabs as-is, etc.)

## Soft parked (OK later)

- ML Trial ↔ creator IA polish  
- Current State detailed schema  
- In-app AI dispatch  
- Disk rename pass  
- Esc peel / post-observe Deck chrome minutiae  

## Push rule

Local commits anytime. **`git push` only outside Mon–Fri 09:00–17:00 Eastern** unless overridden.

Repo: https://github.com/Errrriiiicccc/errriiicccs-idle-lab
