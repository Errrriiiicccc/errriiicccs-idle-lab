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

    def test_inactive_resume_opens_idle_lab(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.INACTIVE,
                deck_active=False,
                resume_handle=True,
            ),
            EscAction.OPEN_IDLE_LAB,
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

    def test_molecule_lab_owns_esc(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                molecule_lab_active=True,
                deck_active=True,
            ),
            EscAction.ENTER_MOLECULE_LAB_CLOSE,
        )
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                molecule_lab_active=True,
                molecule_lab_close_confirm=True,
                deck_active=True,
            ),
            EscAction.CANCEL_MOLECULE_LAB_CLOSE,
        )

    def test_lco_esc_beats_molecule_lab(self) -> None:
        """Esc must exit LCO even when Molecule Lab is still open underneath."""

        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                live_control_active=True,
                molecule_lab_active=True,
                deck_active=True,
            ),
            EscAction.EXIT_LIVE_CONTROL,
        )
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                live_control_active=True,
                live_control_rebinding=True,
                molecule_lab_active=True,
                deck_active=True,
            ),
            EscAction.CANCEL_LCO_REBIND,
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
        # Root accordion is not a peel layer — Esc goes to close-confirm.
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_expanded=True,
                open_menu=False,
            ),
            EscAction.ENTER_CLOSE_CONFIRM,
        )
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_expanded=False,
            ),
            EscAction.ENTER_CLOSE_CONFIRM,
        )

    def test_esc_never_deactivates(self) -> None:
        # Deactivate is Activate-key only; Esc goes to close-confirm after peel.
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

    def test_active_unanchored_restart_when_lab_open(self) -> None:
        text = active_unanchored_prompt(
            last_title=None,
            candidate_found=False,
            lab_visible=True,
        )
        self.assertIn("R = restart", text)
        self.assertNotIn("I = open Lab", text)

    def test_close_confirm_lab_open(self) -> None:
        text = close_confirm_prompt(lab_visible=True)
        self.assertIn("Close flight deck", text)
        self.assertNotIn("Quit", text)

    def test_close_confirm_lab_hidden(self) -> None:
        text = close_confirm_prompt(lab_visible=False)
        self.assertIn("Quit Idle Lab", text)

    def test_live_control_active_prompt_is_only_the_three_facts(self) -> None:
        text = live_control_active_prompt()
        self.assertIn("LCO is active", text)
        self.assertIn("Hold D to describe", text)
        self.assertIn("Esc = exit LCO", text)
        self.assertIn("deactivate", text.lower())
        # Accordion leave labels must not leak into the LCO surface.
        self.assertNotIn("Enter Live Control", text)
        self.assertNotIn("Exit Live Control", text)
        self.assertNotIn("Troubleshoot", text)

    def test_live_control_legend_hint_is_bold_d_instruction(self) -> None:
        self.assertEqual(live_control_legend_hint(), "HOLD D = DESCRIBE")
        self.assertEqual(
            live_control_legend_hint(show_descriptors=True),
            "HOLDING D = DESCRIBE",
        )
        self.assertEqual(live_control_legend_hint(paused=True), "HOLD D = DESCRIBE")

    def test_molecule_lab_prompt_says_deck_paused_for_typing(self) -> None:
        text = molecule_lab_active_prompt()
        self.assertIn("Molecule Lab is open", text)
        self.assertIn("paused", text.lower())
        self.assertIn("type", text.lower())
        self.assertIn("Esc", text)
        confirm = molecule_lab_active_prompt(close_confirm=True)
        self.assertIn("Enter = yes", confirm)


if __name__ == "__main__":
    unittest.main()
