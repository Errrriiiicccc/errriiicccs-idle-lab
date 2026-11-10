# Code layout

**Operator language:** [VISION.md § Lexicon](VISION.md#lexicon-operator--disk--code) · **Target vs ships:** [FEATURES.md](FEATURES.md) · **Shell plan:** [pieces/shell/](pieces/shell/README.md)

Disk/package names below are **today’s** tree (rename pass later). `archive/` is never loaded by the app.

```
errriiicccs-idle-lab/
  README.md
  AGENTS.md
  requirements.txt
  pyproject.toml
  lab-context.json         # active target (Tower / BlueStacks)
  archive/                 # deprecated docs/demos — app does not load
  docs/
    README.md              # cascade
    VISION.md · FEATURES.md · CONTINUATION.md · HARNESS.md
    pieces/                # redesign plan (shell, hygiene, …)
    knowledge/             # Tower compounds
    research/              # cite-only
  presets/                 # legacy Bench macros (→ atoms later)
  automations/
    runtime.json
    taxonomy.json          # Loops browse labels (→ ML library)
    flight_deck.json       # legacy U/O/C/N/A/M (→ L/M/O/S)
    maps/                  # object maps (LOL / Atom overlays)
    playbooks/
    rois/
    events/                # Atoms (disk name lag)
    collections/           # Molecules
    composer/              # Molecule Lab drafts
    templates/
  runs/                    # gitignored traces, harness, clips, CSV
  screen-maps/             # gitignored observations (user-deletable)
  ai-batches/              # gitignored missions (→ OL AI mission)
  examples/
    ai-batches/
    harness-stories/
  src/idle_lab/
    __main__.py
    app.py                 # mega Lab chrome today → rebuild as Idle Lab wrap
    overlay.py · anchor.py · recorder.py · player.py · humanize.py
    click_foreground.py · click_background.py · click_logger.py
    hotkeys.py · tool_export.py · prompt_packet.py
    flight_deck/           # Flight Deck
    live_control/          # LCO → LOL (+ shared overlay future)
    composer/              # Molecule Lab
    observation/ · screen_map/
    ai_batch/              # Missions runner
    harness/ · taxonomy/ · automations/
    presets.py · settings_store.py · models.py · …
    tray.py · single_instance.py · lab_watch.py · comments.py
  tests/
```

`settings.json` is gitignored beside the project.
