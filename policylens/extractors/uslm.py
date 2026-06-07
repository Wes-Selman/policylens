"""
uslm.py — Congressional USLM XML extractor.

Handles <bill> and <resolution> root elements.

Hierarchy (from corpus inspection):
  <legis-body> → <section> → <subsection> → <paragraph>
                                           → <subparagraph> → <clause>

For each node at any level that has a <text> child:
  - section_path: list of <enum> text values from root to this node
  - source_element_id: id attribute on the node (always present on
    <section>/<subsection>; derived for deeper levels if absent)
  - element_type: 'provision_candidate'

<header> child of <section> → element_type: 'header' (no deontic content)

Preamble: <legis-body> may have introductory text before first <section>;
if present, tagged element_type: 'preamble'.

source_element_id derivation:
  - id attribute on the element (always present for section/subsection in USLM)
  - If absent: {parent_id}:{enum_text}:{depth}:{index}
"""

from __future__ import annotations

import re
from lxml import etree

from policylens.extractors.base import BaseExtractor
from policylens.chunker.types import ExtractedUnit

# USLM hierarchy tags, in nesting order
_HIERARCHY_TAGS = {
    "section", "subsection", "paragraph", "subparagraph", "clause",
    "subclause", "item", "subitem",
}

# Tags whose text content we extract as provision text
_TEXT_TAG = "text"
_HEADER_TAG = "header"
_ENUM_TAG = "enum"


def _clean_text(text: str | None) -> str:
    """Normalize whitespace in extracted text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _get_all_text(elem: etree._Element) -> str:
    """Recursively get all text content from an element."""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        child_text = _get_all_text(child)
        if child_text:
            parts.append(child_text)
        if child.tail:
            parts.append(child.tail)
    return _clean_text(" ".join(p for p in parts if p.strip()))


def _make_derived_id(parent_id: str, enum_text: str, depth: int, index: int) -> str:
    """Derive a source_element_id when the XML id attribute is absent."""
    slug = re.sub(r"[^a-z0-9]", "", (enum_text or "").lower())
    return f"{parent_id}_{slug or str(index)}_d{depth}"


class USLMExtractor(BaseExtractor):
    """Extractor for Congressional USLM XML (bills and resolutions)."""

    @property
    def source_schema(self) -> str:
        return "uslm"

    def extract(self) -> list[ExtractedUnit]:
        if not self.raw_text or not self.raw_text.strip():
            return []

        try:
            # USLM documents often have DOCTYPE declarations; use recover=True
            parser = etree.XMLParser(recover=True, resolve_entities=False)
            root = etree.fromstring(self.raw_text.encode("utf-8"), parser)
        except etree.XMLSyntaxError as exc:
            return [ExtractedUnit(
                source_doc_id=self.doc_id,
                source_schema=self.source_schema,
                source_element_id="parse_error_0",
                raw_text="",
                element_type="preamble",
                extraction_notes=[f"XML parse error: {exc}"],
            )]

        units: list[ExtractedUnit] = []

        # Find legis-body (bill) or resolution-body (resolution)
        body = root.find(".//legis-body")
        if body is None:
            body = root.find(".//resolution-body")
        if body is None:
            # Some docs have the body directly under root
            body = root

        self._extract_preamble(body, units)
        self._walk_hierarchy(body, section_path=[], depth=0, units=units)
        return units

    def _extract_preamble(
        self,
        body: etree._Element,
        units: list[ExtractedUnit],
    ) -> None:
        """
        Extract any introductory text in <legis-body> before the first
        <section> element.
        """
        preamble_parts = []

        # Collect direct text children / inline content before first section
        if body.text and body.text.strip():
            preamble_parts.append(body.text.strip())

        for child in body:
            if child.tag in ("section",):
                break
            # Content elements before the first section
            if child.tag not in _HIERARCHY_TAGS:
                text = _get_all_text(child)
                if text:
                    preamble_parts.append(text)

        if preamble_parts:
            text = " ".join(preamble_parts)
            units.append(ExtractedUnit(
                source_doc_id=self.doc_id,
                source_schema=self.source_schema,
                source_element_id="preamble_0",
                raw_text=text,
                element_type="preamble",
                section_path=[],
                nesting_depth=0,
            ))

    def _walk_hierarchy(
        self,
        parent: etree._Element,
        section_path: list[str],
        depth: int,
        units: list[ExtractedUnit],
        parent_id: str = "root",
    ) -> None:
        """
        Recursively walk the USLM hierarchy and emit ExtractedUnit records.

        For each hierarchy element encountered:
          1. Emit a 'header' unit if it has a <header> child.
          2. Emit a 'provision_candidate' unit if it has a <text> child.
          3. Recurse into child hierarchy elements.
        """
        child_index = 0
        for child in parent:
            if child.tag not in _HIERARCHY_TAGS:
                continue

            # ── Determine section_path and source_element_id ───────────────
            enum_elem = child.find(_ENUM_TAG)
            enum_text = _clean_text(enum_elem.text) if enum_elem is not None else ""

            child_id: str = child.get("id") or _make_derived_id(
                parent_id, enum_text, depth, child_index
            )

            child_path = section_path + [enum_text] if enum_text else section_path + [child.tag]

            # ── Header ────────────────────────────────────────────────────
            header_elem = child.find(_HEADER_TAG)
            if header_elem is not None:
                header_text = _get_all_text(header_elem)
                if header_text:
                    units.append(ExtractedUnit(
                        source_doc_id=self.doc_id,
                        source_schema=self.source_schema,
                        source_element_id=f"{child_id}_header",
                        raw_text=header_text,
                        element_type="header",
                        section_path=child_path,
                        nesting_depth=depth,
                    ))

            # ── Provision candidate (<text> child) ────────────────────────
            text_elem = child.find(_TEXT_TAG)
            if text_elem is not None:
                provision_text = _get_all_text(text_elem)
                if provision_text:
                    units.append(ExtractedUnit(
                        source_doc_id=self.doc_id,
                        source_schema=self.source_schema,
                        source_element_id=child_id,
                        raw_text=provision_text,
                        element_type="provision_candidate",
                        section_path=child_path,
                        nesting_depth=depth,
                        extraction_notes=(
                            [f"header: {_get_all_text(header_elem)}"]
                            if header_elem is not None else []
                        ),
                    ))

            # ── Recurse into children ──────────────────────────────────────
            self._walk_hierarchy(
                child,
                section_path=child_path,
                depth=depth + 1,
                units=units,
                parent_id=child_id,
            )

            child_index += 1
