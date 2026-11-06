# L5 — Authoring UX (files + AI)

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P9, P11, C5, C8  
**Split:** balanced

## 1. Restatement

Idle Lab treats **JSON files as source of truth** (presets, ROIs, events, collections, AI batches). The UI reloads and runs; inline editors are intentionally absent. Authoring will increasingly be **human + any gen-AI** via prompt packets. This lane asks: keep files-first, add **validation / dry-run / Basic narrative**, and only add visual graphs where they beat text.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| n8n canvas vs workflows-as-code | Visual prototype vs git-friendly declarations |
| Kestra YAML-first | Readable day-1 declarative orchestration |
| n8nctl / n8n-cli | Lint, dry-run apply, desired-state directories |
| VS Code / JetBrains | Files as truth + rich chrome |
| Jupyter | Experiment cells as runbooks (AI Batches cousin) |

## 3. Extracts

### Visual vs declarative

- n8n’s strength: fast canvas prototyping; weakness for fleets: browser-owned JSON, weak default VCS story.
- Kestra / YAML-first tools: PR diffs, CI, AI copilots writing workflow text.
- Ecosystem response: CLIs that **lint**, **dry-run apply**, convert YAML↔JSON, reconcile directories.

Sources: [Kestra vs n8n](https://kestra.io/vs/n8n), [n8nctl workflows-as-code](https://jjuanrivvera.github.io/n8n-cli/workflows-as-code/), [ubie-oss/n8n-cli](https://github.com/ubie-oss/n8n-cli).

### Pattern that fits Idle Lab

1. Author (human or AI) writes artifacts in repo folders.  
2. **Validate/lint** against schema.  
3. **Dry-run** (parse + resolve presets/ROIs + print plan) without clicking.  
4. Reload + run for real.  
5. Optional: visual *view* of collections later — not the source of truth.

## 4. Idle Lab translation

| Borrow | UI | Engine / tooling |
| --- | --- | --- |
| Lint before run | Automations console: schema errors already skip bad files — surface as first-class “Lint” | `idle_lab.automations` validate CLI or Reload report card |
| Dry-run | “Walkthrough” exists for collections — extend to events: expand actions, resolve preset names, no mouse | Pure function planner |
| Basic vs Detailed | Keep; Basic = human/AI-readable descriptions on every action | Encourage `description` fields in schema (already present) |
| Desired state | Folders under `automations/` *are* desired state | Avoid second database |
| Graphs | Optional later for C6 collection graphs | Render from JSON; never round-trip edit from graph first |
| AI authoring | Prompt packets (L8) emit JSON into folders | Validate strictly (`additionalProperties` mindset) |

## 5. Conflict check

- Building a full n8n-like canvas **now** fights redesign lock and file-as-truth.
- Auto-writing JSON from UI without export path creates dual sources — bad for AI packets.
- Personal-lab constraint: prefer one `Reload` + clear errors over enterprise GitOps ceremony; still keep lint/dry-run because AI authors need them.

## 6. Candidate experiments

1. `py -m idle_lab.automations.validate` (or script) → exit nonzero on bad JSON/refs.
2. Dry-run mode: expand one event’s actions to console without actuating.
3. Template “event stub” + “ROI stub” files for AI few-shot examples in prompt packets.
4. Collection Walkthrough shows resolved branch table from current variables (read-only).

## 7. Takeaways

**Stay files-first.** Steal lint/dry-run/desired-state from workflows-as-code; steal Basic narratives for humans; defer visual editors until collections actually execute and hurt to read as JSON.
