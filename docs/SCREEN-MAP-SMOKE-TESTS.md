# Screen Map — smoke tests

Manual checks on Windows after `pip install -e .`.

## Automated

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Expect `test_screen_map` (sanitize, manifest, mode machine) to pass with the rest of the suite.

## Manual: three titled shots

1. Start Idle Lab. **Clicker** → Set anchor → click a visible window (BlueStacks or Notepad is fine).
2. **Screen Map** → **Start batch…** → title `smoke-three`.
3. Confirm status shows `Screenshot mode: ON` and a path under `screen-maps/smoke-three` (or `smoke-three-N` if reused).
4. Press **Space**, title `Alpha`, Capture. Status shows saved `01_alpha.png`. List shows the title.
5. Press **Space**, title `Beta with spaces`, Capture → `02_beta-with-spaces.png`.
6. Press **Space**, then **Esc** on the dialog → shot cancelled; mode still ON; shot count unchanged.
7. Press **Space**, title `Gamma`, Capture.
8. Press **Esc** (no dialog) → mode OFF; status reports 3 shots.
9. Open the batch folder. Confirm three PNGs + `manifest.json` with matching titles, filenames, timestamps, null review fields.

## Manual: refuse bad anchor

1. Start a batch with a good anchor.
2. Minimize the anchored window (or clear the anchor on Clicker).
3. Space → title → Capture → status error; no new PNG / no new manifest row.

## Hotkey isolation

1. Screenshot mode **OFF**. Press Space in another app — Space is not stolen by Idle Lab.
2. Mode **ON**, no dialog — Space opens the title dialog (does not type into BlueStacks).
