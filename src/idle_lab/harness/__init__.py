"""Tiered verification harness — offline stories/fixtures first, live only when needed."""

from __future__ import annotations

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from idle_lab.harness.cli import main as cli_main

    return cli_main(argv)
