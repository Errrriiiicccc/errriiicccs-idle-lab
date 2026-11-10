# Idle Lab — product & research map

Scaffolding for future research prompts. Captures what the app *is*, which pieces matter, which external systems to study, and how to run lane deep-dives.

**Last updated:** 2026-11-05 (research snapshot — not live shipping status)  
**Canonical vision:** [VISION.md](../VISION.md)  
**Ships today:** [FEATURES.md](../FEATURES.md)  
**Cascade:** [../README.md](../README.md)  
**Related:** [LAYOUT.md](../LAYOUT.md), [automation-schema.md](../automation-schema.md), [CONTINUATION.md](../CONTINUATION.md)

> Operator terms today: **Bench · Observe · Missions · Loops**. This snapshot still says Clicker / Automations / AI Batches / Screen Map in places — treat those as synonyms ([VISION lexicon](../VISION.md#lexicon-operator--disk--code)).

---

## 1. Research framing

| Decision | Choice |
| --- | --- |
| Split | **Balanced** — UI/UX / information architecture *and* runtime / programming patterns |
| Audience | **Personal** for now; keep a path to share when quality feels right |
| Domain | **General Windows GUI observation + actuation lab** (Tower / idle games are a proving ground, not the ceiling) |
| Product identity | **Human-translation workbench** — demonstrate + describe → AI authors file artifacts → Idle Lab executes with screen pixels + ordinary input (no injection / memory dumps) |
| Horizon | Assistive use for people who need **repeatable GUI help** (accessibility-adjacent automation) |
| Artifacts | Durable docs under `docs/research/`; redesign chats cite, do not own, this tree |

### 1.1 North-star loop (vision, not current POC)

Full prose: [VISION.md](../VISION.md). Compressed engineering loop:

```
human demonstrates UI (Observe / Bench) + plain-language goal
    → prompt packet (screenshots + Idle Lab schema + intent)
    → AI proposes ROIs / templates / presets / events / state model / knowledge doc
    → knowledge batches (act → screenshot → inspect → revise)
    → Reload/Restart & run in Idle Lab until acceptance
    → durable playbook so later chats inherit menu geometry & state discriminators
```

**Prompt packet** (conceptual contents):

1. **Screenshots** — visual anchors; exact layout / dimensions of UI under the window frame.
2. **Idle Lab descriptions** — machine contract: schemas, allowed actions/functions, file layout, constraints (“write in this format”).
3. **Human descriptions** — plain language goal and what the operator sees (“when the nameplate appears here… keep only daggers…”).

**Knowledge batch loop** (what AI Batches already gesture at): the AI proposes action sequences, Idle Lab executes and captures evidence (`run_report.json`, Screen Map), the AI inspects results and iterates. Deep integration is a research target, not a claim about current in-process LLM calls (today the LLM stays outside the app).

**Perception implication:** screen cues (text/numerics, icons, panel/tab/overlay state, calibrated scrolls) become typed data or explicit unknowns — see VISION §§4–5. Classical OCR is one instrument, not the product.

---

## 2. Product definition

**Errriiiccc’s Idle Lab** is a Windows **human-translation workbench** for desktop observation + actuation: the operator demonstrates a UI and states intent; AI helps author file-backed automations; the app runs window-anchored **sense → decide → act** loops, a **manual UI atlas**, and **evidence-backed missions**. It sends ordinary mouse input and reads screen pixels. It does not inject into target processes, dump process memory, or claim stealth.

Useful industry labels (better than “autoclicker” alone):

| Label | Fit |
| --- | --- |
| Desktop **RPA workbench** (screen-based, attended) | Capture state, branch, act, log |
| **Macro recorder / player** | Clicker presets |
| **Vision / OCR perception layer** | ROI → Tesseract → typed variables |
| **Priority job scheduler** | Interval events with hard preemption |
| **UI atlas / screenshot corpus** | Screen Map |
| **Experiment runbook runner** | AI Batches (analysis outside process) |
| **Declarative automation DSL host** | JSON files as source of truth |
| *(horizon)* **Assistive GUI agent toolkit** | Prompt packets + reliable actuation for accessibility |

**Not in scope (POC / ethics):** process injection, anti-detect, cloud agents inside the app, “undetectable” game bots.

---

## 3. Core pieces

Each piece is a researchable unit. Paths are relative to repo root.

### P1 — Window anchoring & coordinate frame

- **Terms:** HWND targeting, normalized client coordinates, click-through overlay
- **Job:** Bind clicks / OCR / capture to one moving window so artifacts survive move/resize
- **Where:** `src/idle_lab/anchor.py`, `src/idle_lab/overlay.py`

### P2 — Input actuation (macro layer)

- **Terms:** Macro playback, foreground vs posted/background clicks, humanization
- **Job:** Replay timed click sequences; optional aim/timing jitter at runtime
- **Where:** `src/idle_lab/player.py`, `recorder.py`, `humanize.py`, `click_foreground.py`, `click_background.py`, `presets/`

### P3 — Perception (capture + OCR)

- **Terms:** Screen scraping, ROI crop, OCR post-processing / field parsers
- **Job:** Pixels in named regions → variables (`wave`, `currency`, `game_over`, `presence`, …)
- **Where:** `src/idle_lab/automations/capture.py`, `ocr.py`, `automations/rois/`

### P4 — Decision & branching

- **Terms:** Rule engine, sense–decide–act, pure decision functions
- **Job:** Map observations to action paths (A/B today; collection branches schema-only)
- **Where:** `src/idle_lab/automations/decide.py`, collection schema in `docs/automation-schema.md`

### P5 — Scheduling & preemption

- **Terms:** Interval scheduler, priority queue, mutual exclusion / hard block
- **Job:** Many timed jobs; high-priority work can block lower-priority ticks
- **Where:** `src/idle_lab/automations/scheduler.py`, `runtime.py`

### P6 — Telemetry & evidence

- **Terms:** Run logging, b-roll, CSV telemetry, screenshot archival
- **Job:** Audit trail of what was seen and done
- **Where:** CSV actions, ffmpeg clips, `runs/` (gitignored), Screen Map manifests

### P7 — UI atlas / knowledge capture

- **Terms:** Screenshot corpus, manual labeling, review workflow
- **Job:** Titled map of target UI for humans and offline AI review
- **Where:** `src/idle_lab/screen_map/`, `docs/SCREEN-MAP-USAGE.md`

### P8 — Experiment / mission runbooks

- **Terms:** Scripted exploration, information-gathering batches, external analysis hook
- **Job:** Named step lists → evidence → `run_report.json` for offline AI
- **Where:** `src/idle_lab/ai_batch/`, `docs/AI-BATCH-USAGE.md`

### P9 — Authoring model (files as source of truth)

- **Terms:** Declarative automation DSL, config-as-code, reloadable artifact store
- **Job:** Humans/AI write JSON; UI browses/runs; Reload picks up changes
- **Where:** `presets/`, `automations/`, `ai-batches/`, Basic/Detailed UI modes

### P10 — Application shell / IA

- **Terms:** Multi-workspace instrument panel, operator console
- **Job:** How a human operates workspaces (today: four tabs; redesign: Bench · Observe · Missions · Loops)
- **Where:** `src/idle_lab/app.py`; redesign notes in `docs/CONTINUATION.md`

### P11 — Prompt packets *(vision)*

- **Terms:** Portable AI brief, multimodal task pack, schema-constrained generation
- **Job:** Bundle screenshots + Idle Lab contracts + human intent for **any** gen-AI to implement automations
- **Where:** Not a first-class artifact yet; closest cousins today = Screen Map batches + schema docs + chat handoffs + AI Batches

### P12 — Assistive / accessibility posture *(horizon)*

- **Terms:** Attended RPA, assistive automation, human-in-the-loop GUI agents
- **Job:** Same observation+actuation stack used to reduce repetitive GUI burden for people who need help
- **Where:** Product intent only; research must prefer **transparent, controllable, reversible** patterns over stealth

---

## 4. Combinations (user-facing products-within-the-product)

Composites matter more than isolated features for research.

| ID | Composite | Pieces | Meaning |
| --- | --- | --- | --- |
| C1 | Closed-loop bot tick | P1+P3+P4+P2+P5 | OCR → decide → click on an interval |
| C2 | Priority-aware observation | P5+P6+P3 | Recording/stats can preempt cheap ticks |
| C3 | Humanized scheduled actuation | P2+P5 | Scheduler-driven actions with less robotic pacing |
| C4 | Evidence-backed experiment | P8+P7+P1+P2 | Mission steps → Screen Map + report |
| C5 | Playbook authoring loop | P9+P7+P8 | Atlas → write JSON → reload → run |
| C6 | Phase / strategy orchestration | P4+P5+P9 | Collections, `stop_when`, branch on phase *(runner stub)* |
| C7 | Operator console | P10+P5+P6 | Queue, console, Start/Stop/Reload as control room |
| C8 | Prompt-packet codegen loop | P11+P7+P9(+P8) | Pack intent → AI writes artifacts → optional knowledge-batch refine |
| C9 | Assistive attended session | P12+P1+P2+P10 | Human supervises; lab executes repeatable GUI help |

---

## 5. Analogue map (examples to research)

Use these as **steal-from** targets: UX principles, interaction models, and engineering patterns — then translate into Idle Lab terms.

### 5.1 Desktop RPA / GUI automation

| Analogue | Overlap | Pull |
| --- | --- | --- |
| UiPath, Power Automate Desktop, Automation Anywhere | Screen scrape, attended robots | Job model, exception UX, attended vs unattended |
| SikuliX, PyAutoGUI ecosystems | Image/OCR-driven clicks | Template match vs OCR; debug failed matches |
| AutoHotkey / macro creators | Record/play | Sequence authoring, hotkey ergonomics |
| Playwright / Selenium (cousins) | Locators, waits, traces | Explicit waits, auto-wait, **trace viewer** as debug metaphor |

### 5.2 Emulator / game helpers (proving ground)

| Analogue | Overlap | Pull |
| --- | --- | --- |
| BlueStacks / LDPlayer macros | Emulator macros | Anchor fragility, resolution scaling |
| Streamer.bot, Touch Portal | Operator panels over live apps | Deck/workspace IA, status presence |
| OpenCV screen bots (non-inject) | ROI + template match | Icon presence when OCR is weak |

### 5.3 Observability & control rooms

| Analogue | Overlap | Pull |
| --- | --- | --- |
| Grafana / Datadog operator views | Live signals + actions | Queue/console as observability |
| SCADA / HMI | Sense–act on plant | Manual / supervised / auto modes; big Stop |
| DAW transport (Ableton, Reaper) | Play / pause / record | Refresh / Restart / Stop-all language |
| LabVIEW / instrument benches | “Bench” metaphor | Wire perception to actions |

### 5.4 Scientific / mechanical process analogues

| Process | Maps to | Pull |
| --- | --- | --- |
| PID control loop | Value → decide → act | Deadband, sample rate vs actuation |
| Lab protocol / SOP | Events + collections | Versioned procedures, run numbers, stop conditions |
| CNC G-code + CAM | Presets as toolpaths | Normalized coords, dry-run, feed-rate ↔ humanize |
| QA inspection stations | ROI OCR + CSV | Pass/fail gates, evidence per unit |
| Air traffic sequencing | Priority scheduler | Preemption, single “runway” (worker) |
| Field notes / ethnography | Screen Map titles | Controlled vocabulary for atlas labels |
| Flight data recorder | Clips + CSV + shots | What to record when; sync to events |

### 5.5 Authoring & knowledge tools

| Analogue | Overlap | Pull |
| --- | --- | --- |
| n8n / Node-RED / Zapier | Visual sense→act graphs | When graphs beat JSON for collections |
| GitHub Actions / cron YAML | Declarative jobs | Schema validation, dry-run |
| Obsidian / Anki | Labeled corpora | Screen Map as knowledge UI |
| Jupyter / Observable | Experiment → evidence | AI Batch as external “cell run” |
| Cursor / chat-with-repo packs | Multimodal briefs | **Prompt packet** packaging patterns |

### 5.6 Power-operator UX

| Analogue | Overlap | Pull |
| --- | --- | --- |
| Blender, CAD, Resolve | Dense tools, modes | Workspaces without dashboard clutter |
| VS Code / JetBrains | Files as truth + chrome | Reload model; Basic vs Detailed |
| Stream Deck / MIDI | Physical → actions | Hotkeys as first-class IA |

### 5.7 Accessibility / assistive tech *(horizon)*

| Analogue | Overlap | Pull |
| --- | --- | --- |
| Windows Narrator / Magnifier / Voice Access | OS-level assistive input | Controllability, focus, non-destructive defaults |
| Switch access / scanning UIs | Simplified actuation | Large Stop, clear state, low cognitive load |
| Attended RPA for workplace accommodation | Human-supervised automation | Consent, visibility of what will click next |
| Eye-gaze / alternative input overlays | Pointing intermediaries | Anchor + overlay lessons for “show what will happen” |

---

## 6. Research lanes

Each lane is a future deep-dive prompt. Balanced split: odd/even mix of UX and engine is fine; prefer shipping **one lane note** at a time under `docs/research/lanes/`.

| Lane | Focus | Note | Primary pieces / composites |
| --- | --- | --- | --- |
| L1 | Operator shell IA | [lanes/L1-operator-shell-ia.md](lanes/L1-operator-shell-ia.md) | P10, C7 |
| L2 | Sense–decide–act reliability | [lanes/L2-sense-decide-act-reliability.md](lanes/L2-sense-decide-act-reliability.md) | P3, P4, C1 |
| L3 | Scheduler semantics | [lanes/L3-scheduler-semantics.md](lanes/L3-scheduler-semantics.md) | P5, C2, C6 |
| L4 | Evidence & debug traces | [lanes/L4-evidence-debug-traces.md](lanes/L4-evidence-debug-traces.md) | P6, P7, C4 |
| L5 | Authoring UX (files + AI) | [lanes/L5-authoring-ux-files-ai.md](lanes/L5-authoring-ux-files-ai.md) | P9, P11, C5, C8 |
| L6 | Perception beyond OCR | [lanes/L6-perception-beyond-ocr.md](lanes/L6-perception-beyond-ocr.md) | P3 |
| L7 | Humanize & input quality | [lanes/L7-humanize-input-quality.md](lanes/L7-humanize-input-quality.md) | P2, C3 |
| L8 | Prompt packet format | [lanes/L8-prompt-packet-format.md](lanes/L8-prompt-packet-format.md) | P11, C8 |
| L9 | Knowledge-batch iterate loop | [lanes/L9-knowledge-batch-iterate-loop.md](lanes/L9-knowledge-batch-iterate-loop.md) | P8, C4, C8 |
| L10 | Assistive attended sessions | [lanes/L10-assistive-attended-sessions.md](lanes/L10-assistive-attended-sessions.md) | P12, C9 |

**Deep-dives:** L1–L10 complete (2026-11-05). Index: [lanes/README.md](lanes/README.md).

---

## 7. Lane deep-dive prompt template

Copy into a research chat (or a new `docs/research/lanes/L#.md` authoring pass):

```text
Lane: L# — <title>
Idle Lab framing: personal Windows GUI observation+actuation lab; balanced UX+engine;
  Tower is a proving ground; accessibility is a horizon; prompt packets are north-star.

1. Restate the lane in Idle Lab vocabulary (pieces P#, composites C#).
2. Study 3–5 analogues from PRODUCT-MAP §5 (mix peer product + far-field).
3. For each analogue extract:
   - interaction / mental model
   - state model
   - failure handling & feedback
   - authoring model
   - performance or safety constraints
4. Translate: “In Idle Lab terms this would mean…” (UI only / engine only / both).
5. Conflict check: what fights file-as-truth, single-worker scheduler, or redesign lock?
6. Candidate experiments: small reversible spikes only (no drive-by redesign).
7. Write findings into docs/research/lanes/L#-slug.md with source links.
```

---

## 8. How other chats should use this

- **Redesign chat:** cite lanes L1 / L7 / L10 for shell and operator UX; do not expand this map mid-redesign unless research lands a note.
- **Engine / automation chat:** cite L2 / L3 / L6 / L9; keep collection-runner work aligned with researched semantics.
- **This research chat:** deepen one lane at a time; append notes under `docs/research/lanes/`; update the analogue table here when a lane discovers a better exemplar.

---

## 9. Current capability snapshot (ground truth)

Short reminder of what exists vs vision — so research does not invent already-shipped features.

| Area | Status |
| --- | --- |
| Clicker / presets / humanize | Working |
| Automations events + priority scheduler | Working (interval POC) |
| OCR parsers + A/B decide | Working (demo + Tower-ish parsers) |
| Clips + CSV | Working |
| Screen Map batches | Working |
| AI Batches runner + Screen Map link + `run_report.json` | Working; LLM outside process |
| Collection execution / `stop_when` | Schema + UI; runner stub |
| Inline editors for JSON | Not built (files are source of truth) |
| Prompt packets as first-class artifact | Vision only |
| In-app LLM | Out of POC |
| Assistive productization | Horizon only |
