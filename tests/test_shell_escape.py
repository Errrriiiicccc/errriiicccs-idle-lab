"""Activate / Esc / close-confirm helpers for deck-first shell."""

from __future__ import annotations

import unittest

from idle_lab.flight_deck.shell import (
    EscAction,
    ShellPhase,
    active_unanchored_prompt,
    close_confirm_prompt,
    inactive_prompt,
    live_control_active_prompt,
    live_control_legend_hint,
    molecule_lab_active_prompt,
    resolve_escape,
)


class ResolveEscapeTests(unittest.TestCase):
    def test_inactive_ignores_esc(self) -> None:
        self.assertEqual(
            resolve_escape(phase=ShellPhase.INACTIVE, deck_active=False),
            EscAction.NONE,
        )

    def test_inactive_resume_does_not_steal_esc(self) -> None:
        # Inactive Deck listens only to Activate — Esc passes through.
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.INACTIVE,
                deck_active=False,
                resume_handle=True,
            ),
            EscAction.NONE,
        )

    def test_live_control_wins(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                live_control_active=True,
                deck_active=True,
            ),
            EscAction.EXIT_LIVE_CONTROL,
        )

    def test_lco_rebind_cancels_before_exit(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                live_control_active=True,
                live_control_rebinding=True,
                deck_active=True,
            ),
            EscAction.CANCEL_LCO_REBIND,
        )

    def test_molecule_lab_running_stops_not_close(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                molecule_lab_active=True,
                molecule_lab_running=True,
                deck_active=True,
            ),
            EscAction.STOP_LAB_RUNNERS,
        )

    def test_molecule_lab_idle_closes_immediately(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                molecule_lab_active=True,
                molecule_lab_running=False,
                deck_active=True,
            ),
            EscAction.CLOSE_MOLECULE_LAB,
        )

    def test_observation_running_stops_before_mode_exit(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_mode_active=True,
                observation_running=True,
                deck_active=True,
            ),
            EscAction.STOP_LAB_RUNNERS,
        )

    def test_lco_esc_beats_molecule_lab(self) -> None:
        """Esc must exit LCO even when Molecule Lab is still open underneath."""

        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                live_control_active=True,
                molecule_lab_active=True,
                molecule_lab_running=True,
                deck_active=True,
            ),
            EscAction.EXIT_LIVE_CONTROL,
        )

    def test_close_confirm_cancel(self) -> None:
        self.assertEqual(resolve_escape(phase=ShellPhase.CLOSE_CONFIRM), EscAction.CANCEL_CLOSE)

    def test_active_section_peels_then_close_confirm(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_expanded=True,
                open_menu=True,
            ),
            EscAction.CLOSE_SECTION,
        )
        # Root accordion — only remaining Esc confirmation (close FD).
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_expanded=True,
                open_menu=False,
            ),
            EscAction.ENTER_CLOSE_CONFIRM,
        )

    def test_deck_mode_exits_immediately(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_mode_active=True,
            ),
            EscAction.EXIT_DECK_MODE,
        )

    def test_esc_never_deactivates(self) -> None:
        action = resolve_escape(phase=ShellPhase.ACTIVE, deck_active=True)
        self.assertEqual(action, EscAction.ENTER_CLOSE_CONFIRM)
        self.assertNotEqual(action, EscAction.NONE)


class PromptTests(unittest.TestCase):
    def test_inactive(self) -> None:
        text = inactive_prompt(activate_key="`")
        self.assertIn("Activate Flight Deck", text)

    def test_active_unanchored_says_close_not_deactivate(self) -> None:
        text = active_unanchored_prompt(
            last_title=None,
            candidate_found=False,
            lab_visible=False,
        )
        self.assertIn("Esc = close", text)
        self.assertIn("I = open Lab", text)
        self.assertIn("R = restart", text)
        self.assertNotIn("deactivate", text.lower())

    def test_close_confirm_lab_open(self) -> None:
        text = close_confirm_prompt(lab_visible=True)
        self.assertIn("Close flight deck", text)
        self.assertNotIn("Quit", text)

    def test_close_confirm_lab_hidden(self) -> None:
        text = close_confirm_prompt(lab_visible=False)
        self.assertIn("Quit Idle Lab", text)

    def test_live_control_active_prompt_pause_resume(self) -> None:
        text = live_control_active_prompt()
        self.assertIn("Live Overlay Lab", text)
        self.assertIn("pause", text.lower())
        self.assertIn("Esc = exit", text)
        paused = live_control_active_prompt(paused=True)
        self.assertIn("resume", paused.lower())

    def test_live_control_legend_hint(self) -> None:
        self.assertEqual(live_control_legend_hint(), "HOLD D = DESCRIBE")
        self.assertEqual(
            live_control_legend_hint(show_descriptors=True),
            "HOLDING D = DESCRIBE",
        )
        self.assertIn("RESUME", live_control_legend_hint(paused=True))

    def test_molecule_lab_prompt_no_confirm(self) -> None:
        text = molecule_lab_active_prompt()
        self.assertIn("Molecule Lab is open", text)
        self.assertIn("Esc", text)
        self.assertNotIn("Enter = yes", text)


if __name__ == "__main__":
    unittest.main()
