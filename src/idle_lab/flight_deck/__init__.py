"""In-flight operator deck: sparse HUD beside the anchored target."""

from idle_lab.flight_deck.keymap import FlightDeckKeymap, KeymapNode, load_keymap
from idle_lab.flight_deck.keys import DEFAULT_EXPAND_VK, vk_label
from idle_lab.flight_deck.window import FlightDeckWindow

__all__ = [
    "DEFAULT_EXPAND_VK",
    "FlightDeckKeymap",
    "FlightDeckWindow",
    "KeymapNode",
    "load_keymap",
    "vk_label",
]
