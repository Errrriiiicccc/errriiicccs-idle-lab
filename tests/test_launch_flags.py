"""Restart / launch flag helpers."""

from __future__ import annotations

import unittest

from idle_lab.launch_flags import (
    AUTO_ANCHOR_FLAG,
    pop_auto_anchor_flag,
    restart_command,
)


class LaunchFlagsTests(unittest.TestCase):
    def test_pop_auto_anchor_present(self) -> None:
        remaining, flag = pop_auto_anchor_flag([AUTO_ANCHOR_FLAG])
        self.assertEqual(remaining, [])
        self.assertTrue(flag)

    def test_pop_auto_anchor_absent(self) -> None:
        remaining, flag = pop_auto_anchor_flag([])
        self.assertEqual(remaining, [])
        self.assertFalse(flag)

    def test_pop_preserves_unknown(self) -> None:
        remaining, flag = pop_auto_anchor_flag(["--nope", AUTO_ANCHOR_FLAG])
        self.assertEqual(remaining, ["--nope"])
        self.assertTrue(flag)

    def test_restart_command_includes_flag(self) -> None:
        cmd = restart_command("python", auto_anchor=True)
        self.assertEqual(cmd, ["python", "-m", "idle_lab", AUTO_ANCHOR_FLAG])

    def test_restart_command_can_omit_flag(self) -> None:
        cmd = restart_command("python", auto_anchor=False)
        self.assertEqual(cmd, ["python", "-m", "idle_lab"])


if __name__ == "__main__":
    unittest.main()
