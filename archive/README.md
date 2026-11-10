# Archive

Deprecated product artifacts live here so the **live** tree stays honest.  
Git history remains the ultimate backup; this folder is the **intentional attic**.

## Rules

1. **Live app never loads `archive/`** as automations, presets, missions, or Observe catalog. No silent merge from archive on Refresh.
2. **Move, don’t ghost-delete** product demos/docs you might want to mine later. Prefer `git mv` into a dated bucket.
3. **Observations are not archived here by default** — they are **user-deletable evidence** (see below).
4. Each bucket has a short `REASON.md` (why retired, what replaced it).
5. When in doubt: if the shell Cut/Refine/Keep pass said **CUT** from product story, it belongs here or in the trash — not in `automations/` / Lab UI.

## Layout

```
archive/
  README.md                 ← this file
  docs/                     ← retired markdown (handoffs, old milestones, …)
  automations/              ← retired events/collections/rois demos (when moved)
  presets/                  ← retired Bench macros (when moved)
  misc/                     ← anything else
  _index.md                 ← optional rolling list of what landed + date
```

Suggested move path: `archive/<area>/<YYYY-MM-DD>-<slug>/` with `REASON.md` inside, **or** flat `archive/docs/<name>.md` plus a line in `_index.md` for small doc moves.

## Observations (delete, don’t attic)

Observation Lab evidence (`screen-maps/`, timelines, digests) is **working memory**, not a museum.

| Action | Policy |
| --- | --- |
| **Delete** | First-class in Observation Lab review (per session / bulk). Permanent unless we add Trash later. |
| **Retention UI** | Catalog groups (Today / Yesterday / Last 7 Days / The Past) are for browse — not automatic forever storage. |
| **Export** | If the user wants to keep something long-term, Open folder / future export — not silent copy into `archive/`. |
| **AI mission results** | Same family: deletable with the mission run evidence; mission *definition* files stay in live missions store until the mission itself is retired. |

Do **not** auto-move old observations into `archive/` — that recreates Screen Map hoarding.

## What to archive first (from hygiene pass)

| Kind | Examples | Status |
| --- | --- | --- |
| Historical handoffs / thin milestones | HANDOFF-OCR, IMPLEMENTATION | Moved under `archive/docs/` when this policy landed |
| Flagship-demo automations | `ocr_ab_tick`, `minute_clip`, `humanize_upgrade_loop` (CUT story) | Move in shape-first waterfall, not necessarily today |
| Noise composer smoke atoms | excess `composer_test_*` | Triage during ML cleanup |
| External `idle-lab/docs` | Pre-fork vision | Stay out of this repo; ignore (D12) |

## Operator / agent checklist

Before deleting a live JSON/doc that once shipped:

1. Is it still referenced by Flight Deck / ML library / tests?  
2. If CUT from product but useful archaeology → `archive/…` + `REASON.md` + `_index.md` line.  
3. If pure junk → delete (tests updated).  
4. Refresh docs links (CONTINUATION, FEATURES, pieces).
