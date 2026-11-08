# Code layout

```
errriiicccs-idle-lab/
  README.md
  requirements.txt
  pyproject.toml
  docs/
  presets/
  automations/
    runtime.json
    taxonomy.json           # Lab Loops folder catalog (Atoms / Molecules)
    flight_deck.json        # in-flight accordion hotkeys (O/C/N/A/M → digits)
    maps/                   # typed UI object maps (LCO source of truth)
    playbooks/              # thin shims → maps/ (legacy path)
    rois/
    events/
    collections/
  runs/                    # gitignored output (traces, failure packs)
  screen-maps/             # gitignored Observation / Screen Map batches
  ai-batches/              # gitignored AI information batches
  examples/
    ai-batch-spec.json
  src/idle_lab/
    __main__.py
    app.py                 # Bench | Observe | Missions | Loops + chrome
    overlay.py
    anchor.py
    recorder.py
    player.py
    click_foreground.py
    click_background.py
    click_logger.py        # includes WAVE/SIGNAL OCR harness
    hotkeys.py
    flight_deck/           # in-flight HUD (actions + movable deck window)
    observation/           # Observation sessions (timeline + Screen Map dual-write)
    taxonomy/              # shared virtual taxonomy load/browse/deck adapt
    presets.py
    settings_store.py
    models.py
    win32_api.py
    scroll_memory.py       # drag scroll + in-session scroll persistence
    image_viewer.py
    comments.py            # hierarchical lab-comments.json store
    comment_ui.py          # Note button + dialog
    lab_watch.py           # mtime fingerprint for Refresh badge
    ai_batch/
      schema.py
      store.py
      ui.py
    screen_map/
      names.py
      manifest.py
      batch.py
      catalog.py
      ui.py
    automations/
      schema.py
      store.py
      scheduler.py
      capture.py
      ocr.py
      decide.py
      csv_log.py
      video.py
      mouse_sync.py
      runtime.py
      ui.py
  tests/
```

`settings.json` is created beside the project and is gitignored. Presets live in `presets/`. Automations live in `automations/`.
