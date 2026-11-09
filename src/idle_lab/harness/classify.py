"""Map a short work-surface hint to the cheapest verification tier."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Classification:
    hint: str
    tier: str
    command: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Cheapest tier that can falsify the claim for each surface keyword.
_RULES: list[tuple[tuple[str, ...], str, str, str]] = [
    (
        ("composer", "molecule", "draft", "expand", "palette"),
        "T2",
        "story composer-save-roundtrip",
        "Composer/molecule authorship is file + expand; no Tower/LCO needed.",
    ),
    (
        ("schema", "validate", "taxonomy"),
        "T0",
        "story schema-validate-all",
        "Schema/validation is pure file checks.",
    ),
    (
        ("dry-run", "dry_run", "plan"),
        "T2",
        "story molecule-dry-run",
        "Dry-run plans atoms/molecules without mouse.",
    ),
    (
        ("ocr", "fixture", "perception", "hud"),
        "T1",
        "fixture ocr",
        "Perception regressions use committed crops.",
    ),
    (
        ("unit", "unittest", "test_"),
        "T0",
        "unit",
        "Focused unit tests cover pure logic.",
    ),
    (
        ("lco", "live", "buy", "tower", "bluestacks", "click", "scroll_map", "mission"),
        "T3",
        "doctor  # then: live mission <slug> | live atom <id>",
        "Live game state needs BlueStacks + mouse; doctor first.",
    ),
    (
        ("story", "user-story", "acceptance"),
        "T2",
        "story <id>",
        "Offline user stories exercise Lab APIs without the game.",
    ),
]


def classify_hint(hint: str) -> Classification:
    text = (hint or "").strip().casefold()
    if not text:
        return Classification(
            hint=hint,
            tier="T0",
            command="classify <hint>",
            rationale="Empty hint — pass a work surface like composer, ocr, or lco.",
        )
    for keywords, tier, command, rationale in _RULES:
        if any(key in text for key in keywords):
            return Classification(hint=hint, tier=tier, command=command, rationale=rationale)
    return Classification(
        hint=hint,
        tier="T0",
        command="unit",
        rationale="Unrecognized surface — start with unit/file checks before escalating.",
    )
