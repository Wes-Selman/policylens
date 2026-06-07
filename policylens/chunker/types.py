"""
types.py — ExtractedUnit dataclass.

This is the persisted intermediate produced by Layer 2a extractors and
consumed by the Layer 2b normalizer.  Records are stored in extracted_units.

Design constraints (from handoff):
- source_element_id is the uniqueness key per document; must be deterministic
  so re-running extraction produces the same ids (idempotency).
- element_type values assigned by extractors: 'provision_candidate' | 'preamble' | 'header'
  'boilerplate' is assigned by the normalizer (semantic judgment), never here.
- Pipe character used as separator in provision id: {doc_id}|{section_id}|{provision_index}
"""

from __future__ import annotations
from dataclasses import dataclass, field


# Valid element_type values the extractor may assign.
EXTRACTOR_ELEMENT_TYPES = frozenset({"provision_candidate", "preamble", "header"})


@dataclass
class ExtractedUnit:
    """
    Single structural unit extracted from a source document.

    One ExtractedUnit typically corresponds to one provision record after
    normalization, but the normalizer may merge adjacent units in edge cases.
    """

    # ── Source provenance ──────────────────────────────────────────────────
    source_doc_id: int
    """FK to documents.id — which document this came from."""

    source_schema: str
    """Schema identifier: 'fr_presdocu' | 'uslm'."""

    source_element_id: str
    """
    Deterministic identifier within this document.
    Derived from XML id attributes if present; otherwise constructed from
    {subtype}:{section_path_slug}:{paragraph_index} so that re-extraction
    always produces the same id for the same structural element.
    """

    # ── Content ────────────────────────────────────────────────────────────
    raw_text: str
    """Extracted text, whitespace preserved, boilerplate tags stripped."""

    element_type: str
    """
    Structural classification: 'provision_candidate' | 'preamble' | 'header'.
    'boilerplate' is never assigned here — that is a normalizer judgment.
    """

    section_path: list[str] = field(default_factory=list)
    """
    Hierarchy path as a list of display labels, from outermost to innermost.
    Example FR: ['Sec. 2', '(b)']
    Example USLM: ['1.', '(a)']
    Used to construct section_id on the provision record and for context_text.
    """

    legal_address_raw: str | None = None
    """
    Raw citation string if a legal address is extractable from the element
    text or attributes (e.g. "26 U.S.C. § 7701").  Nullable.
    Parsed into legal_addresses rows by the normalizer.
    """

    nesting_depth: int = 0
    """
    Structural nesting depth of this element in the source XML.
    Depth 0 = top-level section; depth 1 = first sub-level, etc.
    Used by the normalizer's condition_stack heuristic.
    """

    extraction_notes: list[str] = field(default_factory=list)
    """
    Free-text notes from the extractor about edge cases, ambiguities, or
    decisions made during extraction.  Surfaced in debug output.
    """

    # ── Derived helpers ────────────────────────────────────────────────────

    @property
    def section_id(self) -> str:
        """
        Human-readable section identifier built from section_path.
        Example: 'Sec. 2(b)' or '1.(a)'.
        Used as the section_id component of the provision primary key.
        """
        return "".join(self.section_path) if self.section_path else "root"

    def validate(self) -> None:
        """Raise ValueError if the unit is structurally invalid."""
        if self.element_type not in EXTRACTOR_ELEMENT_TYPES:
            raise ValueError(
                f"Extractor may not assign element_type={self.element_type!r}. "
                f"Valid values: {sorted(EXTRACTOR_ELEMENT_TYPES)}"
            )
        if not self.source_element_id:
            raise ValueError("source_element_id must be non-empty.")
        if self.nesting_depth < 0:
            raise ValueError("nesting_depth must be >= 0.")
