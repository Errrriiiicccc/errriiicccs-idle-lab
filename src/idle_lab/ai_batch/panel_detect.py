"""Detect whether an upgrade panel is open and which tab (Attack/Defense/Utility)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageStat

from idle_lab.ai_batch.scroll_metrics import crop_normalized

UpgradeTab = Literal["attack", "defense", "utility", "ultimate"]

# Mid tile row of the upgrade grid. Closed combat is near-black here.
# Tuned on ai-run-menu-nav-currency-toggle-lab-2 shots (Attack cyan / Defense red / Utility yellow).
_PANEL_BODY = {"nx": 0.08, "ny": 0.60, "nw": 0.84, "nh": 0.12}


@dataclass(frozen=True)
class PanelState:
    """What the upgrade footer currently shows."""

    panel_open: bool
    tab: UpgradeTab | None
    mean_rgb: tuple[float, float, float]
    reason: str


def _mean_rgb(image: Image.Image) -> tuple[float, float, float]:
    crop = crop_normalized(image, **_PANEL_BODY)
    stats = ImageStat.Stat(crop.convert("RGB"))
    means = stats.mean or [0.0, 0.0, 0.0]
    return (float(means[0]), float(means[1]), float(means[2]))


def detect_upgrade_panel(image: Image.Image) -> PanelState:
    """Classify upgrade panel from a full-window capture.

    Uses average color of the tile grid ROI:
    - closed / combat-only → very dark
    - attack → cyan/blue tiles (B,G high, R low)
    - defense → red/pink tiles (R high)
    - utility → yellow/olive tiles (R,G high, B low)
    """

    r, g, b = _mean_rgb(image)
    brightness = (r + g + b) / 3.0

    if brightness < 35.0:
        return PanelState(
            panel_open=False,
            tab=None,
            mean_rgb=(r, g, b),
            reason="panel body too dark — upgrade list closed",
        )

    # Defense: red/magenta dominant
    if r >= 110 and r > g + 15 and r > b:
        return PanelState(
            panel_open=True,
            tab="defense",
            mean_rgb=(r, g, b),
            reason="red/pink tile body → Defense",
        )

    # Utility: yellow / olive (R+G high, B low)
    if r >= 110 and g >= 100 and b < 95 and (r + g) > 2.2 * max(b, 1.0):
        return PanelState(
            panel_open=True,
            tab="utility",
            mean_rgb=(r, g, b),
            reason="yellow tile body → Utility",
        )

    # Attack: cyan / blue tiles
    if b >= 110 and g >= 90 and r < 90 and b > r + 30:
        return PanelState(
            panel_open=True,
            tab="attack",
            mean_rgb=(r, g, b),
            reason="cyan/blue tile body → Attack",
        )

    # Ultimate / unknown colored panel — open but not A/D/U
    if brightness >= 50.0:
        return PanelState(
            panel_open=True,
            tab=None,
            mean_rgb=(r, g, b),
            reason="panel looks open but tab color unmatched",
        )

    return PanelState(
        panel_open=False,
        tab=None,
        mean_rgb=(r, g, b),
        reason="ambiguous / likely closed",
    )
