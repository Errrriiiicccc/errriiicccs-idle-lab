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
    rois/
    events/
    collections/
  runs/                    # gitignored output
  screen-maps/             # gitignored Screen Map batches
  ai-batches/              # gitignored AI information batches
  examples/
    ai-batch-spec.json
  src/idle_lab/
    __main__.py
    app.py                 # Clicker | Automations | Screen Map | AI Batches
    overlay.py
    anchor.py
    recorder.py
    player.py
    click_foreground.py
    click_background.py
    click_logger.py        # includes WAVE/SIGNAL OCR harness
    hotkeys.py
    presets.py
    settings_store.py
    models.py
    win32_api.py
    scroll_memory.py       # drag scroll + in-session scroll persistence
    image_viewer.py
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
