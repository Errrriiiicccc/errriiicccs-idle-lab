"""CLI: python -m idle_lab.harness <command> …"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from idle_lab.harness.classify import classify_hint
from idle_lab.harness.context import LabContextError, load_lab_context
from idle_lab.harness.doctor import run_doctor
from idle_lab.harness.fixture import FixtureError, run_fixture_bench_named
from idle_lab.harness.live import LiveHarnessError, run_live_atom, run_live_mission
from idle_lab.harness.report import HarnessReport, now_iso, report_dir, write_report
from idle_lab.harness.stories import StoryError, list_stories, run_story
from idle_lab.harness.unit_cmd import run_units
from idle_lab.presets import project_root


def _print_report_path(path: Path) -> None:
    print(f"report: {path}")


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else project_root()
    folder = report_dir(root, "doctor")
    report = HarnessReport(
        command="doctor",
        name="doctor",
        tier="T3",
        ok=False,
        started_at=now_iso(),
    )
    try:
        ctx = load_lab_context(root)
        result = run_doctor(root=root, context=ctx)
    except LabContextError as exc:
        report.finish(ok=False, summary=str(exc))
        path = write_report(folder, report)
        print(report.summary)
        _print_report_path(path)
        return 1

    report.finish(
        ok=result.ok,
        summary=(
            f"doctor: {result.target_label} → "
            + (f"hwnd={result.hwnd} title={result.title!r} via {result.match_mode}" if result.ok else "NOT FOUND")
        ),
        details=result.to_dict(),
    )
    if result.hint:
        report.hints.append(result.hint)
    path = write_report(folder, report)
    print(report.summary)
    if result.hint:
        print(f"hint: {result.hint}")
    _print_report_path(path)
    return 0 if result.ok else 1


def cmd_classify(args: argparse.Namespace) -> int:
    hint = " ".join(args.hint) if args.hint else ""
    result = classify_hint(hint)
    root = Path(args.root) if args.root else project_root()
    folder = report_dir(root, "classify")
    report = HarnessReport(
        command="classify",
        name="classify",
        tier=result.tier,
        ok=True,
        started_at=now_iso(),
    )
    report.finish(ok=True, summary=f"{result.tier} → {result.command}", details=result.to_dict())
    path = write_report(folder, report)
    print(f"tier: {result.tier}")
    print(f"command: harness {result.command}")
    print(f"why: {result.rationale}")
    _print_report_path(path)
    return 0


def cmd_unit(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else project_root()
    folder = report_dir(root, "unit")
    report = HarnessReport(
        command="unit",
        name="unit",
        tier="T0",
        ok=False,
        started_at=now_iso(),
    )
    result = run_units(list(args.targets or []))
    report.finish(ok=result.ok, summary=result.summary, details=result.details)
    path = write_report(folder, report)
    print(result.summary)
    _print_report_path(path)
    return 0 if result.ok else 1


def cmd_story(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else project_root()
    if args.story_id is None or args.story_id == "list":
        stories = list_stories(root)
        for item in stories:
            print(f"{item['id']}\t{item['title']}\t{item['kind']}")
        return 0

    folder = report_dir(root, f"story-{args.story_id}")
    report = HarnessReport(
        command="story",
        name=str(args.story_id),
        tier="T2",
        ok=False,
        started_at=now_iso(),
    )
    try:
        result = run_story(args.story_id, root=root)
    except StoryError as exc:
        report.finish(ok=False, summary=str(exc))
        path = write_report(folder, report)
        print(report.summary)
        _print_report_path(path)
        return 1

    details: dict[str, Any] = dict(result.details)
    if result.lines:
        details["plan_preview"] = result.lines
    report.finish(ok=result.ok, summary=result.summary, details=details)
    path = write_report(folder, report)
    print(result.summary)
    for line in result.lines[:20]:
        print(line)
    _print_report_path(path)
    return 0 if result.ok else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else project_root()
    folder = report_dir(root, f"fixture-{args.bench}")
    report = HarnessReport(
        command="fixture",
        name=str(args.bench),
        tier="T1",
        ok=False,
        started_at=now_iso(),
    )
    try:
        result = run_fixture_bench_named(args.bench, root=root)
    except FixtureError as exc:
        report.finish(ok=False, summary=str(exc))
        path = write_report(folder, report)
        print(report.summary)
        _print_report_path(path)
        return 1

    report.finish(ok=result.ok, summary=result.summary, details=result.details)
    path = write_report(folder, report)
    print(result.summary)
    _print_report_path(path)
    return 0 if result.ok else 1


def cmd_live(args: argparse.Namespace) -> int:
    root = Path(args.root) if args.root else project_root()
    kind = args.live_kind
    target = args.target_id
    name = f"live-{kind}-{target}"
    folder = report_dir(root, name)
    report = HarnessReport(
        command="live",
        name=name,
        tier="T3",
        ok=False,
        started_at=now_iso(),
        hints=["T3 moves the mouse on the anchored game window."],
    )
    try:
        if kind == "mission":
            result = run_live_mission(target, root=root, timeout_s=float(args.timeout))
        else:
            result = run_live_atom(target, root=root, timeout_s=float(args.timeout))
    except (LiveHarnessError, LabContextError) as exc:
        report.finish(ok=False, summary=str(exc))
        path = write_report(folder, report)
        print(report.summary)
        _print_report_path(path)
        return 1

    report.finish(
        ok=result.ok,
        summary=result.summary,
        details={"kind": result.kind, "doctor": result.doctor, **result.details},
    )
    if not result.doctor.get("ok", True) and result.doctor.get("hint"):
        report.hints.append(str(result.doctor["hint"]))
    path = write_report(folder, report)
    print(result.summary)
    for hint in report.hints:
        print(f"hint: {hint}")
    _print_report_path(path)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idle_lab.harness",
        description="Tiered verification harness (file → fixture → story → live).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Project root (defaults to idle_lab.presets.project_root())",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="Check active target window is findable")
    p_doctor.set_defaults(func=cmd_doctor)

    p_classify = sub.add_parser("classify", help="Recommend tier from a work-surface hint")
    p_classify.add_argument("hint", nargs="*", help="e.g. composer, ocr, lco")
    p_classify.set_defaults(func=cmd_classify)

    p_unit = sub.add_parser("unit", help="Run focused unittest modules")
    p_unit.add_argument(
        "targets",
        nargs="*",
        help="Surface keys (composer, ocr, harness, …) or tests.* module names",
    )
    p_unit.set_defaults(func=cmd_unit)

    p_story = sub.add_parser("story", help="Run an offline user story (or list)")
    p_story.add_argument("story_id", nargs="?", default="list")
    p_story.set_defaults(func=cmd_story)

    p_fixture = sub.add_parser("fixture", help="Run a fixture bench (ocr)")
    p_fixture.add_argument("bench", help="Bench name (ocr)")
    p_fixture.set_defaults(func=cmd_fixture)

    p_live = sub.add_parser("live", help="T3 live mission/atom (moves mouse)")
    p_live.add_argument("live_kind", choices=("mission", "atom"))
    p_live.add_argument("target_id", help="Mission slug or atom event id")
    p_live.add_argument("--timeout", type=float, default=600.0)
    p_live.set_defaults(func=cmd_live)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
