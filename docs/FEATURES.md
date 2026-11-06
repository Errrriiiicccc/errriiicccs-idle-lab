# Features

Product purpose and north star: [VISION.md](VISION.md). This file lists **what the POC ships today**; VISION describes the destination.

## Global chrome

- Compact **Anchor** button (set/rebind) + red **×** clear (disabled when unbound); tiny window subtitle.
- **Flight deck** toggle + **Expand [key]** remap (default `` ` ``) beside Anchor — opens the in-flight HUD.
- **Refresh** (F5): reload presets, automations, missions, Observe catalog, comments, flight-deck keymap — no process kill.
- **Restart**: stop runners, save settings, relaunch `python -m idle_lab`.
- **Stop all**: halt Bench playback, Missions, Loops, Observe capture, Walkthrough.
- **Activity** pulse + **Files changed — Refresh** badge when watched dirs change on disk.
- Contract: [REFRESH-RESTART.md](REFRESH-RESTART.md).

## Flight deck (in-flight HUD)

- Separate movable topmost window; auto-opens when anchored (unless you closed it); reopen from Lab or expand key.
- Collapsed: compact **Close [Esc]** + **Expand [key]**. Expanded: **Collapse [key]** + accordion hotkey menu.
- While a run is active: Pause / Stop + run name/status (menu still available).
- Expand key (`` ` `` by default, remappable per anchor): toggles expand/collapse only.
- Esc always **closes** the deck (never forwarded to the target while the deck is open).
- Accordion catalog [`automations/flight_deck.json`](../automations/flight_deck.json) (separate from Lab Loops taxonomy): letters **O/C/N/A/M** open one section; digits run leaves; **X** collapses section/menu; **D** descriptions. Max two keys deep. No Space flagship.

## Bench (presets)

- Create presets (instantaneous / one second / realtime); Space/Esc recording.
- Foreground and background clicks; focus; cursor restore; countdown.
- **Humanize** (Off / Light / Medium / Heavy): runtime jitter shared with Missions/Loops.
- Loop forever or N times; F6 / F7 / Esc.
- **Note** comments per preset (`lab-comments.json`).
- Click logger with WAVE/SIGNAL OCR harness.

## Observe (Screen Map)

- Start named batch under `screen-maps/`; Space titles a PNG; Esc ends.
- Browse batches + shots; View all; Open folder.
- **Note** on batch or individual shot (also writes `manifest.json` notes).

## Missions (AI Batches)

- File-backed gather/verify runs with executable `steps[]`.
- Optional `genre`: `probe` / `mission` / `bench` (list shows `[probe]` tags).
- Probes: `QUESTION.md` + `ACCEPTANCE.md` + `iterations/NNN/reflection.md` — [PROBE-MISSIONS.md](PROBE-MISSIONS.md).
- Start/Stop; auto-links Observe batch; `run_report.json`.
- Seeds missing folders from `examples/ai-batches/` on Reload (never overwrites local edits).
- **Open linked Observe** primary cross-link.
- On step failure: captures a **FAIL** screenshot into the linked Screen Map before marking missed.
- **Note** on mission or request; legacy Add feedback still available.

## Loops (Automations)

- **Atoms** (`events/`) and **Molecules** (`collections/`); taxonomy labels Atoms / Molecules (`loops.events` / `loops.collections`).
- **Start selected** on an atom runs it **once** (no interval wait). Molecules: `run: "interval"` → child interval pool; `run: "once"` → serial pass.
- Shared `scroll_list` action + scroll atoms (tab-agnostic).
- Queue; console; Reload/Start/Stop; Walkthrough; Start all enabled.
- Interval scheduler with priorities; OCR, A/B, clips, CSV.
- **Note** on atoms and molecules.

## Scrolling

- Wheel + middle-drag; per-tab scroll position until leave/restart.

## Not in this POC

Full Tower buy-priority playbooks, process injection, stealth claims, in-process LLM, deep nested molecule orchestration.
