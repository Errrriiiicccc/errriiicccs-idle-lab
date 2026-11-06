# L3 — Scheduler semantics

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P5, C2, C6  
**Split:** primarily engine; UX for deferred/blocked honesty

## 1. Restatement

Automations use an interval scheduler with numeric priority and **hard non-preemptive block**: while one event runs, others due are deferred (clip blocks A/B tick). Collections (ordered children, branches, `stop_when`) are schema-only. This lane clarifies the **intended concurrency model** before wiring the collection runner.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| Fixed-priority RTOS (FPPS / FPNS / FPDS) | Preemptive vs non-preemptive vs deferred preemption |
| Rate-monotonic intuition | Short period ≠ always higher priority in Idle Lab — priority is author-assigned |
| GitHub Actions concurrency groups | Single flight, pending queue, cancel-in-progress |

## 3. Extracts

### RTOS fixed priority

- **FPPS:** higher priority ready task immediately preempts lower.
- **FPNS:** running task finishes; higher waits (Idle Lab today ≈ FPNS on a single worker).
- **FPDS:** preemption deferred until a safe point (cooperative barriers).
- Priority in hard realtime often tracks **timing**, not “business importance” — Idle Lab authors mix both (clip prio 100 vs tick prio 10), which is fine if documented.
- Critical: **priority inversion** / long low-prio critical sections starve high-prio work — recording a 10s clip *is* a long critical section by design.

Sources: [Davis 2016 priority assignment review](https://www.cs.york.ac.uk/rts/static/papers/Davis2016.pdf), [CMU Concise Handbook of RTS](https://course.ece.cmu.edu/~ece749/docs/RTSHandbook.pdf).

### GitHub Actions concurrency

- One **running** job per concurrency group; optional pending queue (`single` vs `max`).
- `cancel-in-progress: true` aborts current work for newer — **dangerous** for deploys / for Idle Lab mid-click sequences.
- Default: replace pending, don’t cancel running unless asked.
- FIFO among waiters; not a general priority queue.

Sources: [GitHub Docs — concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), [runs-on concurrency notes](https://runs-on.com/github-actions/concurrency/).

## 4. Idle Lab translation

| Concept | Today | Recommended stance |
| --- | --- | --- |
| Worker model | Single automation worker | Keep single worker for mouse exclusivity (one “runway”) |
| Preemption | Non-preemptive hard block | Default stay FPNS; add **yield/barrier** points later (FPDS) for long presets |
| Priority | Static int on events | Keep; document “importance”, not RMS-by-period |
| Overdue policy | Deferred until free | Add policy enum: `skip` / `run_once_catchup` / `queue` |
| Cancel-in-progress | Stop button only | Don’t auto-cancel mid-event except Stop all |
| Collections | Not executed | Runner = **serial child graph** on same worker; branch = choose next child; `stop_when` = exit condition checked between children |
| AI Batch vs Automations | Separate threads | Define **mutex on mouse/anchor**: document who wins or forbid parallel Start |

## 5. Conflict check

- True preemption mid-`play_preset` fights humanize cursor travel and game state — **don’t** FPPS-preempt clicks without barriers.
- Collection loops that never yield will starve interval events — collections need explicit **cooperative yield** or lower-priority background ticks.
- GHA-style cancel-in-progress is wrong default for actuation (half-applied upgrades).

## 6. Candidate experiments

1. Write a one-page **scheduler contract** in `docs/` (or extend automation-schema): FPNS, priority meaning, overdue policy.
2. Prototype overdue policy `skip` on a demo tick (log “skipped N”) vs current “run when free”.
3. Collection runner spike: ordered children only (no branch), still single worker; measure starvation of a 10s tick.
4. UI: label deferred reason with blocking event id (ties to L1 disagreement).

## 7. Takeaways

Idle Lab is a **single-runway, non-preemptive, priority-aware interval scheduler**. Collection execution should stay on that runway with cooperative yields — not a second parallel clicker — unless mouse ownership is explicitly multiplexed.
