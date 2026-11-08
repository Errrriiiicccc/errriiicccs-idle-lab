# Observe / Screen Map — usage

**Observation sessions** are the default Observe path: play the game normally while Idle Lab records pointer events and before/after screenshots into a Screen Map batch folder. Same Idle Lab window; uses the **same window anchor**.

Design detail: [GAMEPLAY-TEST.md](GAMEPLAY-TEST.md).

## Setup

1. Launch Idle Lab (`pythonw -m idle_lab` from the venv).
2. Use the top **Anchor** control, then click the emulator/game window.
3. Open the **Observe** tab (or use the flight deck).

## Start an observation

1. Flight deck **O → 1**, or Observe tab **Start observation**.
2. Auto title: `Observation YYYY-MM-DD HHMM`. Folder under `screen-maps/<slug>/`.
3. Play normally — spam-safe timeline (click bursts coalesce; downs debounce). Screenshots are **sparse scaled JPEG keyframes** (deferred session start, burst ends, nav/tabs, scrolls/drags, full-res PNG marks only). Cap ~30 shots/session. Open `DIGEST.md` first when analyzing.
4. Optional: **O → 2** or **Mark** to bookmark the current screen.
5. **Esc**, **O → 3**, Observe **Stop observation**, or **Stop all** to end.
6. Prompt: rename? **Yes** → title dialog; **No** → keep auto title.

### Esc hierarchy

- Flight deck open → Esc **closes the deck** first.
- Else observation active → Esc **stops** the observation (rename prompt).
- Stop all ends without rename prompt.

## Batch folder contents

```
screen-maps/<batch-slug>/
  observation.json      # session header, policy, counts
  timeline.jsonl        # pointer + mark events
  01_session-start.png
  02_before-click-1.png
  03_after-click-1.png
  manifest.json         # Screen Map shot index (dual-write)
```

`manifest.json` holds batch metadata and one object per shot: `index`, `title`, `filename`, `captured_at`, optional `anchor` hints, plus null placeholders `classification`, `how_opened`, `notes` for a review chat to fill.

## Catalog

Observe tab lists observations on disk. Select a batch → view shots → **View all screenshots** / **Open folder**. Comment bubbles still work on batch or shot.

## Tips

- Prefer one observation per “story” (upgrade buy order, menu dive-and-return).
- After chat edits files on disk, hit global **Refresh (F5)**.
- Missions can still link Screen Map batches; observation folders are valid Screen Map batches.
