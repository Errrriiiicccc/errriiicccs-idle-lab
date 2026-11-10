# Observation Lab

**Parent:** [README.md](README.md) · evidence: [../evidence/README.md](../evidence/README.md)

## Settled

### One Lab, two tabs

| Tab | Role |
| --- | --- |
| **User** | Human-driven observations (pointer / molecule-linked / LOL-linked capture + review) |
| **AI mission** (Missions) | Same Lab — mission definition, planned walkthrough, and results evidence |

Not a separate Missions Lab elsewhere. Selecting a mission uses **center panes** (below).

### Capture modes

| Mode | Records |
| --- | --- |
| **User / pointer** | Mouse + keyboard while using the anchored app; screenshots + event data |
| **Molecule / atom** | Evidence tied to a molecule/atom run (e.g. ML Trial) |
| **LOL** | Evidence tied to Live Overlay Lab usage |

- **Stop capture:** `` ` `` (Deactivate) only.  
- **Mark:** **Cut**.  
- **Rename on stop:** **Cut** — no rename prompts. Rename only later in **review** UI.  
- Flight Deck presentation of “observation ended / open OL” — **park for Flight Deck dive**.

### Start elsewhere → review in OL

Deck can start LOL observation; ML Trial can start molecule observation. Afterward, a link opens Observation Lab. Deck chord details (**O→…**) — **Flight Deck dive**.

### User review catalog

Group: **Today** · **Yesterday** · **Last 7 Days** · **The Past** (dropdowns); **most recent first** inside each.  
Step-by-step **timeline walkthrough** (actions + screenshots + other data). Keep `timeline.jsonl` (extend for keyboard / molecule / LOL).

### AI mission — center panes (settled)

When a mission is selected:

1. **Start mission** — not started yet: created date, purpose, details, how to begin.  
2. **Mission view** — visual representation of the mission itself; user can **walkthrough what will be performed**.  
3. **Mission results** (if completed) — same spirit as User observation review: timeline of mouse/events, screenshots, walkthrough of what was observed.

Mission definition + collected data live together here (not “jump out to a different Observe app”).

### Agreed inventory leans (Eric did not override)

Keep: Start observation (as modes), timeline, digest/session header, catalog (restructured), View all (inside review), Open folder (secondary), Notes, batch.json/list, probe materials, Start mission, run_report, FAIL shots, Export packet, seed examples, offline OCR bench.  
Stop → Deactivate. Legacy Add feedback → **Cut**. Open-linked-Observe as a *separate* destination → **replaced** by in-tab mission results / OL panes above.

---

## What “Screen Map” meant (plain English)

**Today’s code** does two related things when you observe:

1. Saves an **observation session** (`observation.json`, `timeline.jsonl`, shots).  
2. **Also** writes the same shots into a **Screen Map–shaped folder** (`manifest.json` + PNGs) so Missions and old “Screen Map” browse could share one shot pipeline.

“Screen Map” was the **older product name** for “folder of titled screenshots + a manifest index.” Observation sessions **dual-write** into that shape so nothing had two screenshot systems.

**For the redesign:** we are **not** keeping “Screen Map” as something you have to understand. We keep **one evidence store** (sessions + shots + timeline). Folders get restructured to match Today/Yesterday/…. Internally it may still look a bit like the old manifest files until a rename pass — that is implementation debt, not a second Lab.

---

## Open / parked

| Item | Status |
| --- | --- |
| Exact on-disk layout for date groups | open (implement with shape-first) |
| Flight Deck UX after observe / O→ leaves | parked → FD dive |
| Keyboard event schema in timeline | open |
| Mission view / results UI detail | shape-first when building OL |
