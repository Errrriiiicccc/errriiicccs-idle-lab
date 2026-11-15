"""Left-rail lab navigation — one open path; middle desk shows that leaf only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabBranch:
    name: str
    children: tuple[str, ...] = ()


# Roots + optional leaves. Leaves are the only middle-desk destinations when present.
LAB_BRANCHES: tuple[LabBranch, ...] = (
    LabBranch("Info"),
    LabBranch("Live Overlay Lab"),
    LabBranch(
        "Molecule Lab",
        children=("Atom", "Molecule", "Trial"),
    ),
    LabBranch(
        "Observation Lab",
        children=("User", "AI mission"),
    ),
)

IDLE_LAB_TABS: tuple[str, ...] = tuple(b.name for b in LAB_BRANCHES)
DEFAULT_PATH = "Info"


def _branch(name: str) -> LabBranch | None:
    for item in LAB_BRANCHES:
        if item.name == name:
            return item
    return None


def path_root(path: str) -> str:
    return str(path or "").split("/", 1)[0].strip() or DEFAULT_PATH


def path_leaf(path: str) -> str:
    parts = [p for p in str(path or "").split("/") if p.strip()]
    return parts[-1] if parts else DEFAULT_PATH


def join_path(root: str, leaf: str | None = None) -> str:
    branch = _branch(root)
    if branch is None:
        return DEFAULT_PATH
    if not branch.children:
        return branch.name
    child = leaf if leaf in branch.children else branch.children[0]
    return f"{branch.name}/{child}"


def default_path_for_root(root: str) -> str:
    return join_path(root, None)


def normalize_nav_path(raw: str | None) -> str:
    """Map settings / legacy tab names → canonical left-rail path."""

    name = str(raw or "").strip()
    if not name:
        return DEFAULT_PATH
    if "/" in name:
        root, _, leaf = name.partition("/")
        root = root.strip()
        leaf = leaf.strip()
        branch = _branch(root)
        if branch is None:
            return DEFAULT_PATH
        if not branch.children:
            return root
        if leaf in branch.children:
            return f"{root}/{leaf}"
        return default_path_for_root(root)

    # Exact root
    branch = _branch(name)
    if branch is not None:
        return default_path_for_root(name)

    legacy = {
        "Bench": "Molecule Lab/Atom",
        "Observe": "Observation Lab/User",
        "Missions": "Observation Lab/AI mission",
        "Loops": "Molecule Lab/Trial",
        "Clicker": "Molecule Lab/Atom",
        "Automations": "Molecule Lab/Trial",
        "Screen Map": "Observation Lab/User",
        "AI Batches": "Observation Lab/AI mission",
        "LOL": "Live Overlay Lab",
        "Live Overlay Lab (LOL)": "Live Overlay Lab",
        "Atom": "Molecule Lab/Atom",
        "Molecule": "Molecule Lab/Molecule",
        "Trial": "Molecule Lab/Trial",
        "User": "Observation Lab/User",
        "AI mission": "Observation Lab/AI mission",
    }
    return legacy.get(name, DEFAULT_PATH)


# Settings + older call sites still say normalize_last_tab.
normalize_last_tab = normalize_nav_path


def all_desk_paths() -> tuple[str, ...]:
    paths: list[str] = []
    for branch in LAB_BRANCHES:
        if not branch.children:
            paths.append(branch.name)
        else:
            for child in branch.children:
                paths.append(f"{branch.name}/{child}")
    return tuple(paths)
