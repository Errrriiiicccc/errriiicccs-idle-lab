"""Feel Lab — home areas + structure experiments."""

from __future__ import annotations

from dataclasses import dataclass, field

from idle_lab.feel_lab.themes import FAMILIES


@dataclass(frozen=True)
class Variant:
    id: str
    key: str
    title: str
    blurb: str
    is_new: bool = False


@dataclass(frozen=True)
class Stage:
    id: str
    key: str
    title: str
    question: str
    variants: tuple[Variant, ...]
    is_new: bool = False
    new_ids: tuple[str, ...] = field(default_factory=tuple)

    def novelty_keys(self) -> tuple[str, ...]:
        keys = []
        if self.is_new:
            keys.append(f"stage:{self.id}")
        for v in self.variants:
            if v.is_new:
                keys.append(f"variant:{self.id}:{v.id}")
        keys.extend(self.new_ids)
        return tuple(keys)


HOME_TABS: tuple[Stage, ...] = (
    Stage(
        id="describe_feel",
        key="D",
        title="Describe the Feel",
        question=(
            "Dense screen mockups under the current colour scheme. "
            "Folder-tree structure expands children underneath."
        ),
        is_new=False,
        variants=(),
    ),
    Stage(
        id="change_theme",
        key="C",
        title="Change Colour Scheme",
        question=(
            "Primary lean: Type → Bracket (ink). "
            "Other families are side rooms. Pick family → look."
        ),
        is_new=False,
        variants=tuple(
            Variant(id=f.id, key=f.key, title=f.title, blurb=f.blurb, is_new=False) for f in FAMILIES
        ),
    ),
    Stage(
        id="change_structure",
        key="S",
        title="Change Structure",
        question=(
            "Folder list is the main experiment: expand a folder, children appear underneath, "
            "keep flowing down. Depth tints the plates. Other layouts stay as contrasts."
        ),
        is_new=True,
        variants=(
            Variant(
                id="folder_tree",
                key="1",
                title="Folder tree",
                blurb="Explorer list — expand under the parent; depth colors the controls. Main lean.",
                is_new=True,
            ),
            Variant(
                id="top_down",
                key="2",
                title="Top-down bands",
                blurb="Stacked LIVE / Esc bands (older experiment).",
                is_new=False,
            ),
            Variant(
                id="left_right",
                key="3",
                title="Left → right",
                blurb="Columns flow right as you drill in.",
                is_new=False,
            ),
            Variant(
                id="collapse",
                key="4",
                title="Collapse return",
                blurb="Behind layers shrink to Esc → Title / current: …",
                is_new=False,
            ),
        ),
    ),
)

STAGES: tuple[Stage, ...] = HOME_TABS


def stage_by_id(stage_id: str) -> Stage | None:
    for stage in STAGES:
        if stage.id == stage_id:
            return stage
    return None
