"""Shared virtual taxonomy for flight deck + Loops browse."""

from idle_lab.taxonomy.browse import find_node, listed_ref_ids, with_unfiled
from idle_lab.taxonomy.deck import as_flight_deck_keymap
from idle_lab.taxonomy.load import default_taxonomy_path, load_taxonomy, resolve_taxonomy
from idle_lab.taxonomy.model import Taxonomy, TaxonomyError, TaxonomyNode

__all__ = [
    "Taxonomy",
    "TaxonomyError",
    "TaxonomyNode",
    "as_flight_deck_keymap",
    "default_taxonomy_path",
    "find_node",
    "listed_ref_ids",
    "load_taxonomy",
    "resolve_taxonomy",
    "with_unfiled",
]
