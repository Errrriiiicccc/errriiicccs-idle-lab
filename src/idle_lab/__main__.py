"""python -m idle_lab  |  python -m idle_lab validate"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"validate", "--validate"}:
        from idle_lab.automations.validate import format_report, validate_project
        from idle_lab.presets import PresetStore, project_root

        root = project_root()
        store = PresetStore(root / "presets")
        store.load_all()
        preset_names = {preset.name for preset in store.presets}
        report = validate_project(root, preset_names=preset_names)
        print(format_report(report))
        raise SystemExit(0 if report.ok else 1)

    from idle_lab.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
