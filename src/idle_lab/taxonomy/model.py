"""Taxonomy node types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class TaxonomyError(ValueError):
    """taxonomy.json does not match the contract or refs failed to resolve."""


@dataclass
class TaxonomyNode:
    id: str
    key: str
    label: str
    description: str = ""
    children: list[TaxonomyNode] = field(default_factory=list)
    action: dict[str, Any] | None = None
    ref: dict[str, str] | None = None

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def is_folder(self) -> bool:
        return bool(self.children)


@dataclass
class Taxonomy:
    version: int
    roots: list[TaxonomyNode]
    path: Path | None = None
