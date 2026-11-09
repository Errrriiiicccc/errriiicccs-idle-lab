"""python -m idle_lab  |  python -m idle_lab validate  |  python -m idle_lab harness …"""

from __future__ import annotations

import sys

from idle_lab.launch_flags import pop_auto_anchor_flag


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

    if args and args[0] in {"harness", "--harness"}:
        from idle_lab.harness.cli import main as harness_main

        raise SystemExit(harness_main(args[1:]))

    args, auto_anchor = pop_auto_anchor_flag(args)
    if args:
        raise SystemExit(f"Unknown idle_lab args: {' '.join(args)}")

    from idle_lab.app import main as app_main

    app_main(auto_anchor=auto_anchor)


if __name__ == "__main__":
    main()
