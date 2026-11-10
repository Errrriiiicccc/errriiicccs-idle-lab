# Molecule Lab Conditionals

Living feature board for gating draft steps. Authoring lives in Molecule Lab drafts under `automations/composer/drafts/`; expand still emits a **log stub** until runtime enforcement (C5).

**North star flow:** select a draft step → Conditions panel → Add condition → pick a **previous** step → pick a result field that step can produce → build `all` (AND) with optional nested `any` (OR) → set polarity (when true: Perform / Skip).

## Feature board

| ID | Feature | Status |
| --- | --- | --- |
| C0 | Feature board + schema notes | Done |
| C1 | Selection-gated Conditions UI | Done |
| C2 | Previous-step source + dynamic result fields | Done |
| C3 | Multi-predicate `all` + nested `any` + polarity | Done |
| C4 | Expand: richer gate log / notes / preview (no skip) | Done |
| C5 | Runtime enforce gate (numeric compare + skip) | Not started |
| C6 | Descriptions / detail disclosure (lab-scale, not global toggle) | Not started |
| C7 | **Current State** event (was “parser”) — labeled snapshot from sensors | Not started |
| C8 | State-change-once events (edge vs previous Current State) | Not started |
| C9 | Loop cadence / every-N / “loop everything under sensor” | Not started |
| C10 | Palette: nest any saved molecule + sensor atoms (`stat_collect`) | Done |

## Authoring flow (shipped: C1–C3, C10)

1. Left-click a step in the draft. Conditions are hidden until a step is selected.
2. **When true:** Perform step / Skip step.
3. **Add condition:** choose a previous step → field menu from that step’s output catalog → op + values → append under root `all`.
4. **Add OR group:** nest an `any` of two leaves so you can write `C1 AND C2 AND (C3 OR C4)`.
5. Empty `all` = no gate (step always intended to run).

**Palette (C10):** empty context lists **Nest molecule** for *every* saved Lab molecule (Attack + Defense packs together) plus **Sensors / atoms** (`Persistent state` / `stat_collect`). Inside a tab, same-tab nests stay grouped; other-tab packs appear under **Nest molecule (other tab)**.

Sources must be **strictly previous** (`source_step < current`). No ambient free-floating variables.

## Target runtime model (C7–C9) — Current State

This is the intended shape for the phase loop Eric described. Not implemented yet; condition sources today can still point at `stat_collect` fields for authoring/tests.

### Loop cadence

```text
each minute (or sensor tick):
  1. Persistent state      ← only step that refreshes raw numbers (tool_export)
  2. Current State         ← runs only because Persistent state ran this pass
  3. State-change events   ← run only when Current State ran / values changed
  4. Conditional molecules ← Attack / Defense / … gate on Current State (sticky)
```

- **Persistent state** (`stat_collect`) is the clock. Everything beneath it is “the loop body.”
- Between collects, **last Current State stays sticky**. Downstream conditions keep using that snapshot — they do not require Persistent state to re-fire every child tick.
- **Current State** (renamed from “parser”) does *not* scrape the screen. It reads whichever source events ran this pass (today: tool_export → wave/coins/…), applies range→label rules (e.g. wave 150–400 → `phase=midgame`), and writes a durable snapshot.
- If Persistent state did **not** run this pass, Current State is a no-op: keep the previous snapshot.
- **State-change-once** compares previous Current State vs new Current State (e.g. midgame → endgame) and pulses `true` for one evaluation, then `false` while the new state holds.

### Why gate on Current State, not Persistent state

| Gate on Persistent state directly | Gate on Current State |
| --- | --- |
| Couples buys to sensor atom identity | Buys/policies couple to named game phase / flags |
| Re-parse ranges in every condition | One place defines Midgame / Endgame bands |
| Harder to say “only when stats refreshed” | Current State’s `ran_this_pass` / freshness is explicit |

Authoring rule of thumb: put **Persistent state → Current State** near the top of the draft; later steps condition on **Current State** fields (`phase`, `wave`, …), not on the sensor atom.

### Persistent state (how we remember)

Runtime already keeps a sticky `variables` bag across ticks. Current State / state-change need a small explicit memory:

| Slot | Meaning |
| --- | --- |
| `current.*` | Latest Current State snapshot (labels + numeric mirrors) |
| `current.prev.*` | Snapshot from the previous time Current State ran |
| `current.updated_this_pass` | True only on passes where Current State recomputed |
| `edge.<name>` | One-shot true when a named transition fires |

Persistent state continues to write raw vars (`wave_number`, `coins`, …) from tool_export. Current State is the **policy-facing** layer conditionals should prefer.

### Example draft (authoring target)

1. `[ATOM] Persistent state` (`stat_collect`)
2. `[STATE] Current State` — rules from Persistent state outputs (C7)
3. `[MOL] Test Attack Buy` — when Current State `wave ≤ Y` (or `phase` in {beginning, midgame})
4. `[MOL] Test Defense Buy` — when Current State `wave > X`

Until C7 ships, step 2 is absent and steps 3–4 can temporarily source **Persistent state** `wave` for dry authoring.

## Draft JSON (v2)

Key remains `condition` on each step:

```json
"condition": {
  "when_true": "perform",
  "all": [
    { "source_step": 0, "field": "wave", "op": "gte", "value": 150 },
    { "any": [
      { "source_step": 0, "field": "wave", "op": "lt", "value": 400 },
      { "source_step": 1, "field": "completed", "op": "nonempty" }
    ]}
  ]
}
```

- `when_true`: `perform` | `skip`
- Root `all`: AND of leaves and/or `{ "any": [ …leaves ] }`
- Leaf ops: `gte`, `lte`, `gt`, `lt`, `eq`, `between`, `nonempty`

### Migration from v1

Old flat shape `{ variable, op, value, value_hi, after_step }` loads as one leaf under `all` with `when_true: "perform"`. `after_step` `-1` → previous index; `≥0` → that index. If there is no valid previous source, the gate is dropped.

## Output field catalog

| Step kind | Fields |
| --- | --- |
| Any | `completed` |
| `ensure_tab` | `tab_ready` |
| `seek_and_buy` | `bought`, `skipped_maxed`, `skipped_unaffordable` (stubs until perception) |
| `event_ref` stats-like (`stat_collect`) | `wave`, `cash`, `coins`, `diamonds` |
| `molecule_ref` stats-like | same as above |
| Other `molecule_ref` / `event_ref` | `completed` only |
| Current State (C7, planned) | `phase`, mirrored numerics, `updated_this_pass`, … |

## Expand today (C4)

`_condition_actions` prepends a `log` whose message/description include the full gate summary and polarity. Steps still run. Real skip lands in **C5**. Nested `molecule_ref` / `event_ref` children are listed on the collection as-is (gate shim for nested refs still pending with C5).

## Recommended build order

1. **C5** — runtime numeric compare + honor `when_true`.
2. **C7** — Current State event (range→label + sticky snapshot; refresh only when sources ran).
3. **C8** — state-change-once against `current.prev`.
4. **C9** — sensor-driven loop cadence (Persistent state every N ms; body uses sticky Current State).
5. **C6** — denser on-screen summaries + progressive detail.

## Code map

| Concern | Path |
| --- | --- |
| Gate model + catalog + palette | `src/idle_lab/composer/model.py` |
| Conditions UI | `src/idle_lab/composer/window.py` |
| Expand log stub | `src/idle_lab/composer/expand.py` |
| Tests | `tests/test_composer.py` |
