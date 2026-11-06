"""Adapt taxonomy roots into the flight-deck keymap shape."""

from __future__ import annotations

from idle_lab.flight_deck.keymap import FlightDeckKeymap, KeymapNode
from idle_lab.flight_deck.keys import normalize_menu_key
from idle_lab.taxonomy.model import Taxonomy, TaxonomyNode


def as_flight_deck_keymap(taxonomy: Taxonomy) -> FlightDeckKeymap:
    """Build a FlightDeckKeymap from a resolved taxonomy (actions already filled)."""

    return FlightDeckKeymap(
        version=taxonomy.version,
        roots=[_to_keymap_node(root) for root in taxonomy.roots],
        path=taxonomy.path,
    )


def child_for_key(nodes: list[TaxonomyNode], token: str) -> TaxonomyNode | None:
    want = normalize_menu_key(token)
    if not want:
        return None
    for node in nodes:
        if normalize_menu_key(node.key) == want:
            return node
    return None


def _to_keymap_node(node: TaxonomyNode) -> KeymapNode:
    return KeymapNode(
        key=node.key,
        label=node.label,
        description=node.description,
        children=[_to_keymap_node(child) for child in node.children],
        action=dict(node.action) if node.action else None,
    )
