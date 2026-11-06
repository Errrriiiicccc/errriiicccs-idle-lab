# Probe / mission ownership

Contract for the human-translation loop: **AI authors the question and the steps; Eric Anchors and presses Start; AI reads evidence and iterates.**

Unattended agent-start is a later host problem. Until then, ownership means owning the **batch**, not the mouse.

## Roles

| Who | Owns |
| --- | --- |
| AI | Question, `batch.json` steps, acceptance, reflection, playbook updates |
| Eric | Anchor, Start / Stop, optional Note comments, “probe X ran” ping |
| Idle Lab | Execute steps, Screen Map shots, `run_report.json`, `iterations/NNN/` |

## Genres (`batch.json`)

| `genre` | Meaning |
| --- | --- |
| `probe` | One sharp question → evidence → reflect. Prefer short; spawn a new probe over endless retune. |
| `mission` | Multi-step gather/verify toward a larger goal. |
| `bench` | Regression / offline check (e.g. OCR fixture bench). |
| *(empty)* | General AI batch (legacy). |

List UI shows `[probe]` / `[bench]` prefixes when set.

## Probe folder shape

```
ai-batches/<slug>/
  batch.json          # "genre": "probe", steps[], auto_rerun optional
  QUESTION.md         # one-sentence question (source of truth)
  ACCEPTANCE.md       # checklist for this probe
  run_report.json     # last Start
  iterations/
    001/
      batch.json      # snapshot at Start
      iteration.json
      run_report.json
      reflection.md   # AI fills after reading shots
```

Seeded templates (copied on Missions **Reload** if missing locally):

- [`examples/ai-batches/probe-currency-toggle/`](../examples/ai-batches/probe-currency-toggle/)
- [`examples/ai-batches/probe-upgrade-tabs/`](../examples/ai-batches/probe-upgrade-tabs/)
- [`examples/ai-batches/probe-scroll-one-row/`](../examples/ai-batches/probe-scroll-one-row/)

## Loop (every chat)

1. **Author** — Write or revise `QUESTION.md` + `batch.json` under `ai-batches/<slug>/` (or add under `examples/ai-batches/` for seeding).
2. **Eric Starts** — Anchor → Missions → Reload (once if new seed) → select probe → **Start**.
3. **Ping** — “probe \<slug\> ran” + paths if non-obvious.
4. **Reflect** — Read `run_report.json` + linked `screen-maps/ai-run-<slug>/`. Fill `iterations/*/reflection.md`: answered / partial / blocked.
5. **Iterate** — Patch steps or spawn the next probe; update [TOWER-NAV-PLAYBOOK.md](screen-maps/TOWER-NAV-PLAYBOOK.md) only with confirmed facts.

## Authoring rules

- One question per probe. If you need two answers, two probes.
- Prefer `ensure_*` + `screenshot` before blind clicks.
- `auto_rerun: true` so Start re-queues done requests for another evidence pass.
- Do not take over Eric’s mouse unless he asks.
- Data edits → he **Refresh**es; `src/` edits → **Restart**.

## Handoff paste

Use [HANDOFF-AI-BATCH-RUN.md](HANDOFF-AI-BATCH-RUN.md). For probes, also read `QUESTION.md` before judging success.
