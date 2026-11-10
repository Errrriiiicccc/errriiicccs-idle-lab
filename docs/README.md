# Docs cascade

How documentation relates in this repo. Lower tiers cite upper ones; they do not redefine product purpose.

```
PURPOSE          docs/VISION.md
PIECES PLAN      docs/pieces/*             (high-level cut/keep + redesign; before coding)
SURFACE          docs/FEATURES.md          (what code ships today — lagging during redesign)
CONTRACTS        LAYOUT · HARNESS · REFRESH-RESTART · automation-schema · preset-format
OPERATOR HOW-TO  README.md · USAGE · AI-BATCH-USAGE · SCREEN-MAP-USAGE · smoke tests
TARGET KNOWLEDGE docs/knowledge/*          (Tower compounds; not purpose)
RESEARCH         docs/research/*           (cite analogues; do not own status)
EPHEMERAL        CONTINUATION · HANDOFF-*  (next-chat only; cite VISION)
ARCHIVE          archive/                  (deprecated docs/demos; app does not load)
```

| Tier | Owns | Does not own |
| --- | --- | --- |
| **VISION** | What Idle Lab is for; principles; success | What shipped this week |
| **Pieces** | Core categories, current vs proposed, living decisions | Implementation diffs |
| **FEATURES** | What the POC ships today / not yet | Research analogues |
| **Contracts** | File layout, schemas, Refresh vs Restart, harness tiers | Product purpose |
| **How-to** | How an operator runs things | North-star rewrites |
| **Knowledge** | Calibrated Tower facts that compound | App chrome design |
| **Research** | Lanes, analogues, prompt templates | Live “ships today” status (→ FEATURES) |
| **Ephemeral** | Active focus for the next chat | Durable purpose |

**Planning status:** shell + hygiene **agreed**; FEATURES shows **target vs ships-today**. Next is shape-first code when greenlit — not more north-star invention unless purpose drifts.

**Archive:** [archive/README.md](../archive/README.md) (app never loads).

**Rule:** if a lower doc disagrees with [VISION.md](VISION.md) on purpose, update VISION deliberately or fix the lower doc. Do not treat the separate workspace `idle-lab/docs/` as live purpose — that tree is historical concept notes from before this fork.

**Agent entry:** root [AGENTS.md](../AGENTS.md).

**Lexicon (operator ↔ disk ↔ code):** [VISION.md § Lexicon](VISION.md#lexicon-operator--disk--code).
