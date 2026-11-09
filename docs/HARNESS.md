# Verification harness

Shell-invokable, tiered checks so chat can **test without Computer Use** and without always needing Tower open.

```powershell
.\.venv\Scripts\python.exe -m idle_lab.harness <command> …
# or
.\.venv\Scripts\python.exe -m idle_lab harness <command> …
```

Every command writes `runs/harness/<stamp>-<name>/report.json` and prints a one-line summary + `report:` path.

## Tiers

| Tier | Command | Needs desktop? | Answers |
| --- | --- | --- | --- |
| **T0** | `unit …` / `story schema-validate-all` | No | Schema, expand, unit logic |
| **T1** | `fixture ocr` | No | OCR / perception on committed crops |
| **T2** | `story <id>` | No Tower / no mouse | User stories against Lab APIs + temp dirs |
| **T3** | `doctor` then `live mission\|atom …` | BlueStacks open; **moves mouse** | Real clicks / LCO / missions |

**Rule:** pick the cheapest tier that can falsify the claim. Never escalate to Computer Use if `harness` can answer.

## Context assumptions

[`lab-context.json`](../lab-context.json) bakes the active target (default **tower** → BlueStacks / The Tower title substrings, object map, playbook). Live auto-anchor also prefers `settings.json` → `last_anchor_title` when present.

Chat folklore (“we’re on Tower”) maps to that profile — do not invent a different window hunt.

## Commands

```powershell
# Recommend a tier from a work-surface hint
.\.venv\Scripts\python.exe -m idle_lab.harness classify composer
.\.venv\Scripts\python.exe -m idle_lab.harness classify lco buy

# T0
.\.venv\Scripts\python.exe -m idle_lab.harness unit
.\.venv\Scripts\python.exe -m idle_lab.harness unit composer ocr

# T2 stories (list / run)
.\.venv\Scripts\python.exe -m idle_lab.harness story
.\.venv\Scripts\python.exe -m idle_lab.harness story composer-save-roundtrip
.\.venv\Scripts\python.exe -m idle_lab.harness story molecule-dry-run
.\.venv\Scripts\python.exe -m idle_lab.harness story schema-validate-all

# T1
.\.venv\Scripts\python.exe -m idle_lab.harness fixture ocr

# T3 (asks Eric to open BlueStacks if doctor fails — do not Computer Use to hunt)
.\.venv\Scripts\python.exe -m idle_lab.harness doctor
.\.venv\Scripts\python.exe -m idle_lab.harness live mission ocr-fixture-bench
.\.venv\Scripts\python.exe -m idle_lab.harness live atom buy_damage
```

Stories live under [`examples/harness-stories/`](../examples/harness-stories/).

## Agent contract

1. Infer work surface → `harness classify <hint>` if unsure.
2. Prefer `story` / `unit` / `fixture` before `live`.
3. Composer / molecule composition / “did it save?” → **T2** `story composer-save-roundtrip` (or unit). **Do not** open LCO or Tower.
4. Perception regressions → **T1** `fixture ocr`.
5. Live Tower claims → `doctor` then `live …`. If doctor fails, ask Eric to open BlueStacks; **do not** Computer Use to find windows unless he asks.
6. Computer Use is last resort for **Idle Lab’s own chrome** visual bugs — not for Tower playbook verification.

## Related

- Missions (human Start path): [AI-BATCH-USAGE.md](AI-BATCH-USAGE.md)
- OCR fixtures: [knowledge/TOWER-PERCEPTION.md](knowledge/TOWER-PERCEPTION.md)
- Refresh/Restart: [REFRESH-RESTART.md](REFRESH-RESTART.md)
