"""
base.py — BaseExtractor abstract interface.

Every source-specific extractor implements this interface.
Adding a new source = new file implementing BaseExtractor.
The normalizer and CLI dispatcher are never touched for new sources.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from policylens.chunker.types import ExtractedUnit


class BaseExtractor(ABC):
    """
    Abstract base for source-specific XML extractors.

    Subclasses implement extract() to parse raw_text from a documents row
    and return a list of ExtractedUnit records.

    Contract:
    - extract() is pure: same input always produces same output (idempotent).
    - extract() never assigns element_type='boilerplate' — that belongs to
      the normalizer (semantic judgment, not structural observation).
    - All returned ExtractedUnits pass validate() without raising.
    - source_element_id values are unique within a single document.
    """

    def __init__(self, doc: dict) -> None:
        """
        Parameters
        ----------
        doc : dict
            A row from the documents table as a dict, with at minimum:
            id, source, doc_type, raw_format, raw_text, title, date, url.
        """
        self.doc = doc
        self.doc_id: int = doc["id"]
        self.doc_title: str = doc.get("title") or ""
        self.doc_type: str = doc.get("doc_type") or ""
        self.raw_text: str = doc.get("raw_text") or ""

    @property
    @abstractmethod
    def source_schema(self) -> str:
        """
        Schema identifier string, e.g. 'fr_presdocu' or 'uslm'.
        Used as the source_schema field on extracted_units rows.
        """

    @abstractmethod
    def extract(self) -> list["ExtractedUnit"]:
        """
        Parse self.raw_text and return a list of ExtractedUnit records.

        Returns an empty list if the document has no extractable content
        (e.g. empty raw_text).  Never raises for expected document structure
        variations; records edge cases in extraction_notes instead.
        """
