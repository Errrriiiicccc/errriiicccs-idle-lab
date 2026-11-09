"""Molecule composer — context-gated palette that exports atoms/molecules as files."""

from idle_lab.composer.catalog import CapabilityCatalog, TabCapabilities, load_capability_catalog
from idle_lab.composer.expand import ExportResult, expand_and_write, preview_expansion
from idle_lab.composer.model import (
    ComposerContext,
    ComposerDraft,
    DraftStep,
    PaletteItem,
    SeekGuards,
    build_palette,
)

__all__ = [
    "CapabilityCatalog",
    "ComposerContext",
    "ComposerDraft",
    "DraftStep",
    "ExportResult",
    "PaletteItem",
    "SeekGuards",
    "TabCapabilities",
    "build_palette",
    "expand_and_write",
    "load_capability_catalog",
    "preview_expansion",
]
