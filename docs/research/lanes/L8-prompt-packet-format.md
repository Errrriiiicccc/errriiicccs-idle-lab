# L8 — Prompt packet format

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P11, C8 (uses P7, P9; feeds L9)  
**Split:** balanced (contract design + UX for pack/export)

## 1. Restatement

North-star: a user builds a **prompt packet** — screenshots + Idle Lab machine contract + plain-language goal — and hands it to **any** gen-AI to emit valid automations/presets/batches. Idle Lab does not need an in-process LLM; it needs a **portable, strict, multimodal brief**. Closest today: Screen Map batches + schema docs + chat handoffs + AI Batches.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| OpenAI tool/function calling + strict JSON schema | Machine-valid outputs |
| Prompt engineering structure | Identity / instructions / examples / context separation |
| Multimodal document tips | Image detail, crop, verbosity for UI screenshots |
| Cursor / repo packs | Code+docs+images as agent context |

## 3. Extracts

### Tool calling / structured outputs

- Tools: clear `name`, `description`, JSON Schema `parameters`, `required`, `additionalProperties: false`, `strict: true` where supported.
- Soft limit: keep initially available tools/functions **small** (≲20).
- Offload known args in host code; don’t make the model invent ids you already know.
- “Intern test”: can a human use the tool from the description alone?

Source: [OpenAI Function calling](https://developers.openai.com/API/docs/guides/function-calling).

### Prompt sectioning

Recommended developer message shape: **Identity → Instructions → Examples → Context** (context often last). Keep builders in code; version and evaluate prompts.

Source: [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering).

### Multimodal

- Combine text + images in one user message.
- Use higher image detail for tiny HUD text; crop to anchored window / ROI.
- Separate “what you see” captions from “what to emit”.

Source: [Multimodal document understanding tips](https://developers.openai.com/cookbook/examples/multimodal/document_and_multimodal_understanding_tips).

## 4. Proposed packet layout (v0 sketch)

```
prompt-packet/<slug>/
  PACKET.md                 # human+AI entry: goal, constraints, success criteria
  contract/
    ACTION_CATALOG.md       # allowed actions, enums, examples (Idle Lab descriptions)
    schemas/                # JSON Schema or excerpts for event/roi/preset/batch
    fewshot/                # 1–2 minimal valid JSON examples
  vision/
    manifest.json           # from Screen Map or export
    *.png                   # titled shots; captions in manifest
  intent/
    GOAL.md                 # plain-language human description
    notes.md                # optional edge cases
  output/                   # AI writes here (or returns as files)
    automations/...
    presets/...
```

**PACKET.md skeleton:**

1. Identity: “You author Idle Lab JSON only; no prose except in description fields.”  
2. Instructions: schema rules, normalized coords, anchor assumptions, forbidden actions.  
3. Examples: link fewshot.  
4. Context: attach vision + GOAL.  
5. Output contract: file paths + validate with lint (L5).

## 5. Idle Lab translation

| Borrow | Product |
| --- | --- |
| Strict schema | Publish JSON Schema next to automation-schema.md for AI tools that support structured output |
| Small catalog | Packet includes only needed action subset (e.g. no video if unused) |
| Multimodal vision | Export Screen Map batch → `vision/` |
| Any-AI portability | Packet is files + markdown; no vendor lock-in |
| Intern test | ACTION_CATALOG written for humans too (accessibility / sharing later) |

## 6. Conflict check

- Huge Screen Map dumps blow context windows — packet export should **select** shots, not zip everything.
- In-app LLM would fight “any gen-AI” portability — keep export-first.
- Redesign can add “Export prompt packet” without changing engine.

## 7. Candidate experiments

1. Hand-build one packet for click-logger A/B demo; run through ChatGPT/Claude/Cursor; measure valid JSON rate.  
2. Draft `contract/ACTION_CATALOG.md` generator from schema enums.  
3. “Export packet” stub: copies chosen Screen Map + GOAL template + schema excerpts.  
4. Add JSON Schema files under `docs/research/contracts/` (or `schemas/`) as the strict spine.

## 8. Takeaways

A prompt packet is a **multimodal, schema-constrained brief** with clear sectioning — not a chat log. Steal strict tools + section order from API best practices; keep the artifact folder-portable.
