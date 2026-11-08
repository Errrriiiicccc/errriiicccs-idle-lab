# Features

Product purpose and north star: [VISION.md](VISION.md). This file lists **what the POC ships today**; VISION describes the destination.

## Global chrome

- **Single instance:** a second `python -m idle_lab` focuses the running app (Lab + deck) and exits; Restart releases the lock before relaunch.
- **Deck-first launch:** process starts with Lab withdrawn and an **inactive** flight deck showing only **Activate Flight Deck [`]**. Nothing else is captured until Activate (key or button). Lab **X** hides Lab; process stays on the deck.
- **Taskbar + tray:** Lab “hide” parks the window off-screen at alpha 0 (not withdraw/iconify — those hide the flight-deck Toplevel on Windows) so a taskbar button remains. Native tray icon (Open Lab / Show Flight Deck / Quit); Windows 11 often parks new icons under the `^` overflow.
- Compact **Anchor** button (set/rebind) + red **×** clear (disabled when unbound); tiny window subtitle.
- **Flight deck** toggle + **Expand [key]** remap (default `` ` ``) beside Anchor — opens the in-flight HUD.
- **Refresh** (F5): reload presets, automations, missions, Observe catalog, comments, flight-deck keymap — no process kill.
- **Restart**: stop runners, save settings, relaunch `python -m idle_lab`.
- **Stop all**: halt Bench playback, Missions, Loops, Observe capture, Walkthrough.
- **Activity** pulse + **Files changed — Refresh** badge when watched dirs change on disk.
- Contract: [REFRESH-RESTART.md](REFRESH-RESTART.md).

## Flight deck (in-flight HUD)

- Separate movable topmost window. Starts **inactive**: only **Activate Flight Deck [`]** (`` ` `` by default, remappable). No Esc / I / A / menu capture while inactive — no close control either.
- **Activate** → show **Close [Esc]** + **Deactivate [`]**; unanchored prompt offers **Enter** re-anchor (if last title lives), **A** new anchor, **I = open Lab** (when Lab hidden), **R = restart**.
- **Deactivate [`]** = idle companion (deck stays up; only `` ` `` listens). Never Esc.
- **Close** (button or Esc after menu peel) → confirm. If Lab is open: withdraw the deck, app stays. If Lab is hidden: quit Idle Lab. Esc on confirm cancels (stay active).
- **Once anchored** while active: full accordion hotkeys + **I = open Lab · R = restart** (I only when Lab hidden; R always).
- While a run is active: Pause / Stop + run name/status (menu still available).
- **Esc peel** (active only): Live Control exit → remap cancel → close open letter-section → close-confirm. (The root hotkey list is not a peel layer.)
- Accordion catalog [`automations/flight_deck.json`](../automations/flight_deck.json) (separate from Lab Loops taxonomy): letters **U/O/C/N/A/M** open one section; digits run leaves; **X** collapses section/menu; **D** descriptions. Max two keys deep. No Space flagship.
- **Live Control Overlay (U→1 enter / U→2 troubleshoot):** overlay from the Tower object map [`automations/maps/tower_main_gameplay.objects.json`](../automations/maps/tower_main_gameplay.objects.json). Clicks show hotkeys (Q/W/E, 1–6); non-clicks show icons (scroll / ★ stat / ↻ refresh). **D** flips icons ↔ hotkeys. **`** pauses (gray inert) / resumes; Esc exits. Detail: [LIVE-CONTROL-OVERLAY.md](LIVE-CONTROL-OVERLAY.md), [OBJECT-MAP.md](OBJECT-MAP.md).
- **Humanize** defaults to **Off** (precision). Menu still offers Light/Medium/Heavy for experiments.

## Bench (presets)

- Create presets (instantaneous / one second / realtime); Space/Esc recording.
- Foreground and background clicks; focus; cursor restore; countdown.
- **Humanize** (Off / Light / Medium / Heavy): runtime jitter shared with Missions/Loops.
- Loop forever or N times; F6 / F7 / Esc.
- **Note** comments per preset (`lab-comments.json`).
- Click logger with WAVE/SIGNAL OCR harness.

## Observe (Observation sessions)

- **Start observation** (flight deck **O→1** or Observe tab): auto-titled session under `screen-maps/`.
- While active: mouse moves/clicks/scrolls are logged to `timeline.jsonl`; before/after frames dual-write into the Screen Map manifest. **O→2** Mark bookmarks a frame. Esc / **O→3** / Stop all ends; optional rename prompt.
- Browse observations + shots; View all; Open folder (includes `observation.json` + timeline).
- **Note** on batch or individual shot (also writes `manifest.json` notes).
- Design: [GAMEPLAY-TEST.md](GAMEPLAY-TEST.md).

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
