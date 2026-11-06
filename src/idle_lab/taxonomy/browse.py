"""Browse helpers for Loops panel + Unfiled."""

from __future__ import annotations

from collections.abc import Iterable

from idle_lab.taxonomy.model import Taxonomy, TaxonomyNode


def find_node(taxonomy: Taxonomy, node_id: str) -> TaxonomyNode | None:
    want = (node_id or "").strip()
    if not want:
        return None

    def walk(nodes: list[TaxonomyNode]) -> TaxonomyNode | None:
        for node in nodes:
            if node.id == want:
                return node
            found = walk(node.children)
            if found is not None:
                return found
        return None

    return walk(taxonomy.roots)


def listed_ref_ids(node: TaxonomyNode, kind: str) -> set[str]:
    """Collect ref targets of ``kind`` under ``node`` (recursive)."""

    out: set[str] = set()

    def walk(n: TaxonomyNode) -> None:
        if n.ref is not None and n.ref.get("kind") == kind:
            out.add(n.ref["id"])
        # Also accept resolved actions.
        if n.action is not None:
            if kind == "event" and n.action.get("type") == "start_event":
                out.add(str(n.action.get("event") or ""))
            elif kind == "collection" and n.action.get("type") == "start_collection":
                out.add(str(n.action.get("collection") or ""))
            elif kind == "preset" and n.action.get("type") == "play_preset":
                out.add(str(n.action.get("preset") or ""))
        for child in n.children:
            walk(child)

    walk(node)
    out.discard("")
    return out


def with_unfiled(
    root: TaxonomyNode,
    *,
    kind: str,
    all_ids: Iterable[str],
    titles: dict[str, str],
) -> TaxonomyNode:
    """Return a copy of ``root`` with an Unfiled folder for missing store ids."""

    listed = listed_ref_ids(root, kind)
    missing = sorted(set(all_ids) - listed)
    if not missing:
        return root

    unfiled_children: list[TaxonomyNode] = []
    # Keys: Space for first, then 2..9, then A.. (avoid 1; Space is flagship)
    key_pool = ["Space"] + [str(n) for n in range(2, 10)] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    key_pool = [k for k in key_pool if k.upper() not in {"X", "D"}]
    for index, item_id in enumerate(missing):
        key = key_pool[index] if index < len(key_pool) else f"F{index}"
        label = titles.get(item_id) or item_id
        if kind == "event":
            action = {"type": "start_event", "event": item_id}
            ref = {"kind": "event", "id": item_id}
        else:
            action = {"type": "start_collection", "collection": item_id}
            ref = {"kind": "collection", "id": item_id}
        unfiled_children.append(
            TaxonomyNode(
                id=f"{root.id}.unfiled.{item_id}",
                key=key,
                label=label,
                description=f"Not filed in taxonomy ({kind} {item_id}).",
                action=action,
                ref=ref,
            )
        )

    unfiled = TaxonomyNode(
        id=f"{root.id}.unfiled",
        key=_next_sibling_key(root),
        label="Unfiled",
        description=f"{kind.title()}s present on disk but missing from taxonomy.",
        children=unfiled_children,
    )
    return TaxonomyNode(
        id=root.id,
        key=root.key,
        label=root.label,
        description=root.description,
        children=[*root.children, unfiled],
        action=root.action,
        ref=root.ref,
    )


def _next_sibling_key(root: TaxonomyNode) -> str:
    used = {child.key.strip().upper() for child in root.children}
    for candidate in ["3", "4", "5", "6", "7", "8", "9", "U", "V", "W", "Y", "Z"]:
        if candidate not in used and candidate not in {"X", "D"}:
            return candidate
    return "U"
