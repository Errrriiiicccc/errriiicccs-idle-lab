# L9 — Knowledge-batch iterate loop

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P8, C4, C8  
**Split:** balanced (harness protocol + Observe UX)

## 1. Restatement

AI Batches already run step lists, link Screen Map, and write `run_report.json` for **offline** AI analysis. The vision loop: AI proposes steps → Idle Lab executes → evidence returns → AI reflects → revise until good or budget exhausted. This lane defines the **harness contract** (ReAct/Reflexion-shaped) without requiring an in-process model.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| ReAct (Thought → Action → Observation) | Ground-truth observations from tools |
| Reflexion / observe–plan–act–reflect | Outer retry with verbal memory of failures |
| CI fail→fix loops (`iterative-improve`) | Quality ratchet; max retries; feed logs back |
| Scientific method | Hypothesis → experiment → evidence → revise |

## 3. Extracts

### ReAct / agentic loop

```
while not done:
    action = model.think(context)
    observation = environment.execute(action)
    context += (action, observation)
```

Power comes from **real** observations (screenshots, OCR, errors), not model-imagined success. Stop sequence / harness injects Observation so the model cannot hallucinate tool results.

Source: [Agentic loop — ReAct](https://prakashkagitha.github.io/llm-stack-book/08-agents-harness/02-agentic-loop.html), [Mechanistic agentic AI](https://openbooks.library.northwestern.edu/mcie/chapter/8-2-mechanistic-agentic-artificial-intelligence/).

### Reflection & bounds

- Critic/reflect step after failure; inject feedback into next attempt.
- **max_retries** (often 3–5); return best effort + failure indicator.
- Summarize repeated failures to avoid context sludge.
- CI-as-ratchet: improvements stick; regressions blocked by objective checks.

Sources: [W&B self-correction](https://wandb.ai/site/articles/agentic-ai-self-correction-how-to-build-systems-that-fix-their-own-mistakes/), [ktenman/iterative-improve](https://github.com/ktenman/iterative-improve).

## 4. Idle Lab translation

| Loop stage | Idle Lab artifact |
| --- | --- |
| Plan | `ai-batches/<slug>/batch.json` steps (or packet `output/`) |
| Act | AI Batch Start / Automations event |
| Observe | Screen Map PNGs + `run_report.json` + optional trace (L4) + OCR vars |
| Reflect | Offline AI (chat) or future adapter; write `iterations/N/reflection.md` |
| Ratchet | Human marks acceptance; or checklist script (ROI readable, preset exists, dry-run lint) |

**Harness file sketch:**

```
ai-batches/<slug>/
  batch.json
  iterations/
    001/run_report.json
    001/reflection.md      # AI-written
    002/batch.json         # revised steps (or patch)
    ...
  ACCEPTANCE.md            # human criteria
```

Idle Lab’s job: **execute + evidence faithfully**. The AI host’s job: reflect + revise. Integration = folder conventions + export buttons, not necessarily embedding the LLM.

## 5. Conflict check

- Unbounded auto-retries can click forever — require max iterations + Stop all (L1/L10).
- Parallel Automations + Batch fighting the mouse (L3) — serialize or lock.
- Don’t claim in-app autonomy while LLM stays external — document the split honestly (FEATURES already does).

## 6. Candidate experiments

1. Document iteration folder convention; manually run 2 improve cycles on currency-toggle lab.  
2. Normalize `run_report.json` so reflections always see the same keys (steps, shots, errors).  
3. Acceptance checklist YAML: `screenshots_min`, `no_error`, `ocr_contains`, etc.  
4. Prompt fragment for review chats: “Only trust Observation sections from run_report; never invent click success.”

## 7. Takeaways

Knowledge batches are Idle Lab’s **environment.execute** half of ReAct. Invest in **stable observations + bounded iteration folders**; leave the thinker pluggable (any gen-AI).
