# Idle Lab — external research

Durable home for **external research and information procurement**: product decomposition, analogue maps, and lane deep-dives that inform redesign and engine work without casually rewriting locked code.

| Doc | Role |
| --- | --- |
| [../VISION.md](../VISION.md) | **Canonical north star** — human-translation workbench |
| [../FEATURES.md](../FEATURES.md) | **Ships today** — living product inventory (not this tree) |
| [../README.md](../README.md) | Docs cascade |
| [PRODUCT-MAP.md](PRODUCT-MAP.md) | Scaffolding: pieces, combinations, analogues, research lanes, prompt templates |
| [lanes/](lanes/README.md) | Deep-dives L1–L10 (complete as of 2026-11-05; some “today” snapshots are stale — prefer FEATURES) |

**Framing:**

- Research weight: **balanced** UI/UX / IA **and** runtime/engine patterns.
- Audience: **personal lab** for now; craft should not block later sharing.
- Domain: **general Windows GUI observation + actuation**, not Tower-only. Accessibility (assistive automation) is an intentional horizon.
- Product identity: **human sees → says intent → AI authors files → Idle Lab executes** (screen pixels + ordinary input + first-party exports when available).
- Vision hook: **prompt packets** → any gen-AI implements automations; well-integrated AIs also run **knowledge batch** iterate-until-good loops; durable playbooks feed later chats.

This tree is for research inputs other chats can **cite**. It does **not** own live shipping status — that lives in [FEATURES.md](../FEATURES.md). Lane prose may still say “Clicker / AI Batches”; operator terms today are Bench · Observe · Missions · Loops ([VISION lexicon](../VISION.md#lexicon-operator--disk--code)).

## Historical “landed in code” snapshot (2026-11-05)

Kept as a research checkpoint. Prefer FEATURES for current truth.

| # | Feature | Where (then) |
| --- | --- | --- |
| 1 | Operator honesty (mode chip, deferred Activity) | chrome Mode menu + Activity |
| 2 | Overdue policies | event `overdue_policy` + scheduler |
| 3 | Collection runner | Loops **Run pack** |
| 4 | `wait_until` | automation actions |
| 5 | Failure packs | `runs/failures/` |
| 6 | `trace.jsonl` | `runs/traces/` (level in settings) |
| 7 | Validate / Dry-run | Loops buttons + `python -m idle_lab validate` |
| 8 | `match_template` | optional OpenCV; `automations/templates/` |
| 9 | Humanize cancel + tooltips | interruptible waits; status tip on change |
| 10 | Supervised mode | chrome **Auto / Supervised** |
| 11 | Prompt packet export | Missions **Export packet** → `prompt-packets/` |
| 12 | Mission iterations | `ai-batches/<slug>/iterations/NNN/` |

## Suggested next use

1. Cite L1–L10 / PRODUCT-MAP when redesigning; check FEATURES before claiming something is missing.
2. Engine follow-ups still worth research: richer `wait_until` deadband, OpenCV install for gem-box, collection yield vs interval coexistence, Current State as queryable fields (VISION §5).
