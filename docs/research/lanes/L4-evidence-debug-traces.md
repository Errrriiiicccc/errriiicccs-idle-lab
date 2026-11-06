# L4 — Evidence & debug traces

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P6, P7, C4  
**Split:** balanced UX + engine

## 1. Restatement

When an automation or AI Batch misbehaves, the operator (or offline AI) needs a **time-travelable story**: what was seen, what was decided, what was clicked, and what the screen looked like before/after. Today: console lines, CSV, clips, Screen Map PNGs, `run_report.json` — powerful but not yet a unified **trace**.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| Playwright Trace Viewer | Action timeline + before/action/after + filmstrip |
| Flight data recorder / QA stations | Mandatory evidence synced to events |
| Screen Map + AI Batch reports | Existing Idle Lab building blocks |

## 3. Extracts

### Playwright Trace Viewer

- Trace is a **post-run artifact** (`trace.zip`), openable offline ([trace.playwright.dev](https://trace.playwright.dev/)).
- Per action: locator, duration, log, source; **Before / Action / After** snapshots; click position highlighted.
- Filmstrip screencast; timeline filters console + network to selected range.
- Errors marked on timeline; attachments for visual diffs.

Sources: [Trace viewer](https://playwright.dev/docs/trace-viewer), [Python trace docs](https://playwright.dev/python/docs/trace-viewer).

### FDR / QA inspection

- Record **what matters for reconstruction**, not everything forever.
- Tie evidence to a **run id** and step index.
- On fail: stop or enter reviewed recovery — don’t click a look-alike to “keep going” (visual testing guidance).

## 4. Idle Lab translation

| Borrow | Engine | UI |
| --- | --- | --- |
| Action-centric timeline | Append structured events to `runs/<run>/trace.jsonl`: `{ts, event_id, action, vars_delta, shot_path?}` | Observe workspace: simple step list → open shot |
| Before / After | Optional screenshot hooks around `click` / `play_preset` / `decide` | Image viewer already exists — link from step |
| Filmstrip | Reuse clips + Screen Map; don’t require full screencast always | “Open evidence folder” |
| Filter by action | Trace viewer filters logs by selected step | Console already noisy — correlate by step id |
| Offline AI | Trace + Screen Map is the knowledge-batch observation payload | Export pack button (see L8/L9) |

**Minimum viable trace fields:** `run_number`, `event_id`, `action_index`, `action_type`, `ok`/`error`, `variables` snapshot (or diff), optional `screenshot_before` / `after`, OCR `raw`/`parsed`.

## 5. Conflict check

- Full before/after every action is disk- and CPU-heavy on a single worker — make it **opt-in levels**: Off / On failure / Every act.
- Don’t replace file-as-truth with DB; traces live under `runs/` like today.
- Redesign Observe workspace is the natural home; don’t stuff traces into Bench first viewport.

## 6. Candidate experiments

1. JSONL tracer behind a runtime flag; one demo event writes before/after PNGs.
2. AI Batch `run_report.json` gains `steps[].evidence` paths (normalize with Automations later).
3. “Open last failure” button (Observe) → folder or image viewer.
4. Prompt snippet: “Given this trace.jsonl + shots, explain the failure” for review chats.

## 7. Takeaways

Aim for a **Playwright-shaped mental model** without building a full DOM snapshot system: action timeline + linked screenshots + variable snapshots is enough for GUI pixel automation.
