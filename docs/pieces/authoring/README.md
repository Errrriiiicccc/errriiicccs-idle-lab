# Authoring

**Job:** Turn demonstration + language into files Idle Lab can run.  
**Decisions:** [decisions.md](decisions.md)

## Current

- **Files are the language** — edit JSON / knowledge docs; Refresh / Restart.
- **Molecule Lab** — in-app compose for molecules (see [../molecules/](../molecules/README.md)).
- **Prompt packet export** from Missions → `prompt-packets/` (LLM still outside the app).
- AI work happens in Cursor (or elsewhere); Idle Lab executes and evidences.

## Proposed

- Keep files as source of truth.
- **In-app prompt dispatch** (horizon Eric called “really amazing”): Idle Lab sends a packet (shots + schema + intent) to a model and writes/revises artifacts, then runs Prove.
- Clarify operator path: Companion / Labs “Ask” vs stay Cursor-centric for a while.
- Molecule Lab remains the structured editor even when AI drafts the first pass.

## What “in-app authoring loop” meant

Not “a chatbot tab that chats forever.” The exciting slice is:

1. You capture evidence (Observe / Hands / fail shots).  
2. From Idle Lab you **send a prompt packet** (or short intent + attachments).  
3. A model returns atoms/molecules/ROIs/knowledge edits.  
4. Idle Lab validates, saves files, you Refresh, you Prove.  
5. Iterate.

That can start thin (export packet + open in Cursor) and grow into true dispatch.

## Fit to vision

Speak → Translate. AI authors; Idle Lab executes.
