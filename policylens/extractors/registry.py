"""
policylens/extractors/registry.py

Extractor dispatch registry.
Maps source values from the documents table to the appropriate extractor class.

Keeping this separate from cli.py means:
- Tests can import the dispatcher without pulling in the CLI's DB/API imports.
- New extractors are registered here; cli.py never needs to be touched.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policylens.extractors.base import BaseExtractor


_REGISTRY: dict[str, type] = {}


def register(source: str, extractor_class: type) -> None:
    """Register an extractor class for a given source string."""
    _REGISTRY[source] = extractor_class


def get_extractor(doc: dict) -> "BaseExtractor":
    """
    Return an instantiated extractor for the given document row.

    Parameters
    ----------
    doc : dict
        A row from the documents table. Must contain a 'source' key.

    Raises
    ------
    ValueError
        If no extractor is registered for doc['source'].
    """
    # Populate registry lazily to avoid circular import at module load
    if not _REGISTRY:
        _populate_registry()

    source = doc.get("source", "")
    klass = _REGISTRY.get(source)
    if klass is None:
        raise ValueError(
            f"No extractor registered for source: {source!r}. "
            f"Registered sources: {sorted(_REGISTRY)}"
        )
    return klass(doc)


def _populate_registry() -> None:
    from policylens.extractors.fr_presdocu import FRPresdocuExtractor
    from policylens.extractors.uslm import USLMExtractor

    register("federal_register", FRPresdocuExtractor)
    register("congress", USLMExtractor)
