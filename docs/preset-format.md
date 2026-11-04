# Preset format

Version 1 JSON. One file per preset in `presets/`.

Coordinates are fractions of the anchored window rectangle from `GetWindowRect`. `nx` 0 is the left edge. `nx` 1 is the last pixel inside the window (the rect's right edge is exclusive). The same numbers are reused after the window moves or is resized.

`button` is `left` only.

```json
{
  "name": "sample three points",
  "version": 1,
  "timing_mode": "instantaneous",
  "loop": true,
  "loop_count": null,
  "notes": "Center column. Labels are for you, not the clicker.",
  "points": [
    {"nx": 0.25, "ny": 0.25, "delay_ms": 50, "hold_ms": 50, "button": "left", "label": "upper"},
    {"nx": 0.50, "ny": 0.50, "delay_ms": 50, "hold_ms": 50, "button": "left", "label": "middle"},
    {"nx": 0.75, "ny": 0.75, "delay_ms": 50, "hold_ms": 50, "button": "left", "label": "lower"}
  ]
}
```

`timing_mode` is `instantaneous`, `one_second`, or `realtime`. That field records how the preset was captured. Playback uses `delay_ms` and `hold_ms` on each point, not the mode name.

`loop` true and `loop_count` null repeats until you stop. `loop_count` 2 runs two passes. `loop` false runs once.

The loader will reject a missing name, an unknown mode, a non-numeric coordinate, a negative delay, a hold below 1 ms, and any button other than `left`.
