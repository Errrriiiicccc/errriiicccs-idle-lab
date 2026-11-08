# Refresh vs Restart

Contract for Eric and AI chats working on Idle Lab.

## Refresh (F5 or chrome **Refresh**)

Use after **data** changes on disk:

- `presets/*.json`
- `automations/**`
- `ai-batches/*/batch.json`
- `screen-maps/**` manifests
- `lab-comments.json`

Refresh reloads those stores, soft-resyncs the Loops scheduler, and keeps the process alive. Mid-run definitions update; Stop all if you need a clean idle state.

**Chat default:** “I edited the batch/automation JSON — hit **Refresh**, then Start.”

## Restart (chrome **Restart**)

Use after **code** changes:

- anything under `src/idle_lab/**/*.py`
- dependency / install changes

Restart stops runners, saves settings, relaunches `python -m idle_lab`, and exits the current process.

**Chat default:** “I changed Python — hit **Restart**.”

## Stop all

Halts Bench playback, Mission runner, Loops scheduler, Observe capture, and Walkthrough without quitting.

## Deck-first quit

Lab **X** / hide only withdraws the Lab window. With Lab hidden, Esc on the flight deck peels menus then asks **Quit Idle Lab?** — **Enter** exits the process, **Esc** cancels.

## Workspaces

| Tab | Role |
| --- | --- |
| **Bench** | Presets / playback (hands) |
| **Observe** | Screen Map evidence |
| **Missions** | AI batch gather/verify runs |
| **Loops** | Timed automations |

## Comments

**Note** on any preset, mission, request, event, collection, Observe batch, or individual shot. Notes live in `lab-comments.json` (and sync into Screen Map `manifest.json` notes when commenting Observe objects). Refresh reloads them for the next chat.
