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
  src/idle_lab/
    __main__.py
    app.py                 # Clicker | Automations tabs
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
