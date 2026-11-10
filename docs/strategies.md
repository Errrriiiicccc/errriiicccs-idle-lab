# Asking for a strategy preset

There is no chatbot in the app. A strategy preset is a JSON file written in chat and dropped into `presets/`. Press **Refresh** (or Loops Reload).

North star: [VISION.md](VISION.md). Bench format: [preset-format.md](preset-format.md).

`presets/sample-three-points.json` is a working example. Anchor the click logger and the three markers should sit on the drawn targets.

Send:

1. A screenshot of the emulator, cropped to the same window you anchor. Include the BlueStacks frame if that is what the cyan frame hugs.
2. The click order, in plain language.
3. The timing: instantaneous, one second, or specific delays and holds.
4. Whether it should loop.

Coordinates guessed from a screenshot are approximate. Record with Space when the spots have to be exact, or nudge the markers after import.

For gated multi-step policies, prefer Molecule Lab + atoms/molecules over a single mega-preset — [MOLECULE-LAB-CONDITIONALS.md](MOLECULE-LAB-CONDITIONALS.md).
