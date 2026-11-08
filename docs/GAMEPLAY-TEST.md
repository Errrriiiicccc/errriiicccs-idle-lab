# Observation sessions — design sketch

**Status:** shipped + capture tightened (2026-11-06)  
**Product name:** **Observation** (replaces Space-titled Screen Map capture as the default Observe path)  
**Related:** [VISION.md](VISION.md), [L4](research/lanes/L4-evidence-debug-traces.md), [L10](research/lanes/L10-assistive-attended-sessions.md), flight deck **O**

## Locked decisions (Eric, 2026-11-06)

| # | Decision |
| --- | --- |
| 1 | Nest under **O**; **replace** Start batch / Capture shot / End batch. Observation is the default Observe path. |
| 2 | Auto-title on start. On stop: **Y/N rename**; if Yes, open a title dialog. |
| 3 | Drag threshold **12 px** to start; retune after real Tower use. |
| 4 | Emit **`anchor_changed`** if the anchor rect/title changes mid-session (do not hard-end). |
| 5 | **Dual-write** into the Screen Map batch (same folder = observation). Named as observations. |
| 6 | **Mark** leaf included in v1 (bookmark a frame). |
| 7 | **Esc** ends an active observation (same as Stop leaf / Stop all). |
| 8 | Observe tab: Start / Mark / End observation + existing catalog (batches are observations). |

## Operator story

1. Anchor the target.
2. Flight deck **O** → **1** Start observation (auto title `Observation YYYY-MM-DD HHMM`).
3. Play normally with the mouse. Lab records the full pointer timeline + **sparse keyframes**; does **not** swallow mouse input.
4. Optional **O** → **2** Mark (extra bookmark frame).
5. **O** → **3** Stop, or **Esc**, or Stop all.
6. Prompt: rename? Y → dialog; N → keep auto title.
7. Review in Observe catalog (Screen Map batch folder with timeline + shots).

## Artifact layout

One folder under `screen-maps/` (existing catalog):

```text
screen-maps/observation-2026-11-06-1442/
  manifest.json           # Screen Map shots (dual-write)
  observation.json        # session header / policy / counts
  timeline.jsonl          # append-only events
  01_session-start.png
  02_before-click-1.png
  03_after-click-1.png
  04_mark.png
  ...
```

Timeline frame paths are the same filenames as Screen Map shots (no separate `frames/` tree).

### `observation.json`

```json
{
  "version": 1,
  "kind": "observation",
  "id": "observation-2026-11-06-1442",
  "title": "Observation 2026-11-06 1442",
  "created_at": "...",
  "ended_at": "...",
  "duration_ms": 42012,
  "anchor": { "title": "...", "rect": { "left": 0, "top": 0, "width": 1280, "height": 720 } },
  "policy": {
    "mode": "discovery",
    "frames": "sparse",
    "move_hz": 15,
    "move_min_px": 4,
    "drag_threshold_px": 12,
    "settle_ms": 180,
    "burst_gap_ms": 350,
    "max_shots": 40,
    "nav_ny_min": 0.92
  },
  "counts": { "events": 86, "clicks": 21, "scrolls": 0, "drags": 1, "marks": 0, "shots": 6, "bursts": 4 },
  "end_reason": "operator"
}
```

### Timeline envelope

```json
{"t_ms": 1820, "ts": "...", "i": 12, "type": "pointer_up", "button": "left", "x": 902, "y": 511, "nx": 0.72, "ny": 0.61, "hold_ms": 90, "nav": false}
{"t_ms": 2200, "ts": "...", "i": 18, "type": "keyframe", "shot": "02_after-burst-1.png", "role": "after", "kind": "burst"}
```

Types: `session_start`, `session_end`, `pointer_sample`, `pointer_down`, `pointer_up`, `wheel`, `drag`, `mark`, `anchor_changed`, `keyframe`.

## Flight deck **O**

| Key | Label | Action |
| --- | --- | --- |
| 1 | Start observation | `observation_start` |
| 2 | Mark | `observation_mark` |
| 3 | Stop observation | `observation_end` |

Legacy `observe_start` / `observe_shot` / `observe_end` remain accepted as aliases → same handlers.

## Capture maturity ladder

Observations get cheaper as knowledge compounds. Same timeline shape at every tier; frames shrink then disappear.

| Mode | When | Frames | Timeline |
| --- | --- | --- | --- |
| **discovery** (default now) | Unknown / first walkthroughs | Sparse **full-window** keyframes | Full pointer stream |
| **refined** | Regions mapped (upgrade panel, buy boxes, tabs) | **Crops** of the relevant box/list only | Full pointer stream (+ optional region ids) |
| **semantic** | Live Control/hotkey overlay vocabulary exists | **None** (Mark still allowed) | Semantic `action` events (`stat_collect`, `upgrade.buy`, …) |

### Discovery rules (shipped hard tighten)

Goal: a ~60s spam-click session stays under ~`max_shots` (30) and is chat-analyzable from `DIGEST.md` + a handful of frames.

1. **Timeline coalescing** — same-locus spam → `pointer_burst {count,…}` (not hundreds of ups).
2. **Down debounce** (~45ms / ~16px) — ignore OS double-fires / rage downs.
3. **Hook queue backpressure** — soft coalesce moves; hard-drop excess downs if UI is behind.
4. **Deferred session-start frame** — first real input, not at arm time (avoids start+spam crash window).
5. **Click bursts** → at most one keyframe after quiet; **adaptive** min interval (~2s) for non-forced frames.
6. **Nav / drag / wheel / Mark** → forced keyframes (Mark = full-res PNG).
7. **Scaled JPEG keyframes** (~0.5×, q≈65); skip near-duplicate hashes.
8. **Worker backpressure** + `max_shots` / `max_pending_frames` — never block the mouse hook.
9. **Periodic header flush** + `digest.json` / `DIGEST.md` on stop.
10. **UI refresh ≤ ~3 Hz** while recording.
11. Legacy `before_after_click` remains available for debugging only — not the default.

### Refined (next; object map exists)

Object templates + Tower instances: [OBJECT-MAP.md](OBJECT-MAP.md) / [`automations/maps/tower_main_gameplay.objects.json`](../automations/maps/tower_main_gameplay.objects.json).

Eric’s upgrade-box idea:

1. Start still takes a full frame → classify / know which panel is open.
2. Click inside a known upgrade tile → crop **that tile** (title + value + cost) instead of the whole window.
3. Scroll inside a known list ROI → crop **that list region** only.
4. Buy hit-zone clicks → same tile crop after settle → see value/cost change.
5. Fill `buy_visual_states` colors and tighten `panel.*.roi` / grid from those crops.

This is the bridge into Live Control Overlay: discovery builds the map; refined proves the map with tiny images; semantic then stops needing images for known loops.

### Semantic / Live Control record (later)

Once hotkey overlays fire named actions, record:

```json
{"type": "action", "id": "nav.defense", "ok": true}
{"type": "action", "id": "upgrade.buy", "target": "health"}
```

No screencaps required for analysis of a known loop. Screenshots become optional proof on failure only.

## Analysis guidance (for chats)

Default read order: `observation.json` → `timeline.jsonl` → **only** open PNGs for session-start, tab changes, scrolls, and ambiguous bursts. Do not ingest every shot.

## Success bar

Start from the deck, buy three upgrades across tabs with a scroll, stop. Folder has a complete click story in JSONL and **on the order of a handful of PNGs**, not dozens. A one-minute observation stays under the shot cap and is still reconstructible.
