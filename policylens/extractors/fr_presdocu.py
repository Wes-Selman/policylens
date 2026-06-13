"""
fr_presdocu.py — Federal Register PRESDOCU XML extractor.

Handles document subtypes: EXECORD, PROCLA, PRNOTICE, DETERM.
Detected by inspecting the child element tag under <PRESDOCU>.

Section detection logic (from corpus inspection):
  - <FP> containing an <E T="04"> child → new section boundary
  - Section number: text of the <E T="04"> element
  - Section heading: text of <E T="03"> element in the same <FP>, if present
  - Sub-paragraphs: <P> or <FP SOURCE="FP1"> whose text begins with ^\\([a-z0-9]+\\)

Preamble detection:
  - Opening <FP> elements before the first section boundary that contain
    the authority-vested formula → element_type: 'preamble'

Boilerplate tag stripping (before text extraction):
  PRTPAGE, GPH, PSIG, PLACE, DATE, FRDOC, FILED, BILCOD, TITLE3, PRES

source_element_id derivation:
  - Use XML id attribute if present
  - Otherwise: {subtype}:{section_path_slug}:{paragraph_index}

jurisdiction_scope detection:
  - Default: 'federal_only'
  - Set to 'involves_states' when _INVOLVES_STATES_PATTERN matches the unit text.
  - Fine-grained classification (preempts_state, defers_to_state, creates_floor)
    is the normalizer's responsibility, not the extractor's.
"""

from __future__ import annotations

import re
from lxml import etree

from policylens.extractors.base import BaseExtractor
from policylens.chunker.types import ExtractedUnit

# Tags to remove before any text extraction (non-content metadata tags)
_STRIP_TAGS = frozenset({
    "PRTPAGE", "GPH", "PSIG", "PLACE", "DATE",
    "FRDOC", "FILED", "BILCOD", "TITLE3", "PRES",
})

# Patterns for preamble detection
_PREAMBLE_PATTERNS = re.compile(
    r"by (the authority|virtue of the authority) vested in me",
    re.IGNORECASE,
)

# Pattern for sub-paragraph labels: (a), (b), (1), (i), etc.
_SUBPARA_PATTERN = re.compile(r"^\([a-z0-9]+\)", re.IGNORECASE)

# Known subtypes and their root element tag names
_SUBTYPE_TAGS = frozenset({"EXECORD", "PROCLA", "PRNOTICE", "DETERM"})

# Coarse state-reference pattern. Matches text that mentions state governments,
# state law, or state authority. The normalizer refines this into
# preempts_state | defers_to_state | creates_floor.
_INVOLVES_STATES_PATTERN = re.compile(
    r"\b("
    r"State government|States? may|States? shall|States? must"
    r"|State law|State laws"
    r"|preempt|supersede|displace|occupy the field"
    r"|no State may|State law is preempted"
    r"|subject to State law|as determined by the State"
    r"|minimum standard|not less than|may provide greater|more protective"
    r")\b",
    re.IGNORECASE,
)


def _slugify(path: list[str]) -> str:
    """Convert section_path list to a safe string for use in IDs."""
    return "_".join(
        re.sub(r"[^a-z0-9]", "", p.lower()) for p in path
    ) or "root"


def _element_text_clean(elem: etree._Element) -> str:
    """
    Extract all text content from an element, stripping child tag markup
    but preserving whitespace between inline text and child tails.
    Stripped tags have already been removed from the tree before this call.
    """
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        child_text = _element_text_clean(child)
        if child_text:
            parts.append(child_text)
        if child.tail:
            parts.append(child.tail)
    return " ".join(p.strip() for p in parts if p.strip())


def _strip_boilerplate_tags(root: etree._Element) -> None:
    """
    Remove boilerplate metadata tags from the tree in-place.
    Uses etree.strip_tags which removes the element but keeps its tail text.
    We want to drop the element AND its content, so we use a different approach:
    remove the element entirely (including content) using getparent().remove().
    """
    # Collect first, then remove (modifying tree during iteration is unsafe)
    to_remove = []
    for elem in root.iter():
        if elem.tag in _STRIP_TAGS:
            to_remove.append(elem)

    for elem in to_remove:
        parent = elem.getparent()
        if parent is not None:
            # Preserve the tail text (text after the closing tag) by
            # appending it to the previous sibling or parent text.
            tail = elem.tail or ""
            prev = elem.getprevious()
            if prev is not None:
                prev.tail = (prev.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail
            parent.remove(elem)


def _jurisdiction_scope(text: str) -> str:
    """
    Return 'involves_states' if the text contains a state-reference pattern,
    otherwise 'federal_only'. 'unknown' is reserved for empty/unparseable text.
    """
    if not text:
        return "unknown"
    return "involves_states" if _INVOLVES_STATES_PATTERN.search(text) else "federal_only"


class FRPresdocuExtractor(BaseExtractor):
    """Extractor for Federal Register PRESDOCU XML documents."""

    @property
    def source_schema(self) -> str:
        return "fr_presdocu"

    def extract(self) -> list[ExtractedUnit]:
        if not self.raw_text or not self.raw_text.strip():
            return []

        try:
            root = etree.fromstring(self.raw_text.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            return [ExtractedUnit(
                source_doc_id=self.doc_id,
                source_schema=self.source_schema,
                source_element_id=f"parse_error_0",
                raw_text="",
                element_type="preamble",
                extraction_notes=[f"XML parse error: {exc}"],
            )]

        # Identify subtype from the child tag under <PRESDOCU>
        subtype = "unknown"
        doc_root = root  # The PRESDOCU element (or may already be the subtype)
        if root.tag == "PRESDOCU":
            for child in root:
                if child.tag in _SUBTYPE_TAGS:
                    subtype = child.tag
                    doc_root = child
                    break
        elif root.tag in _SUBTYPE_TAGS:
            subtype = root.tag
            doc_root = root

        # Strip boilerplate metadata tags (in-place, before text extraction)
        _strip_boilerplate_tags(doc_root)

        units: list[ExtractedUnit] = []
        self._extract_from_body(doc_root, subtype, units)
        return units

    def _extract_from_body(
        self,
        doc_root: etree._Element,
        subtype: str,
        units: list[ExtractedUnit],
    ) -> None:
        """
        Walk the document body and produce ExtractedUnit records.

        State machine:
          - Before first section boundary → emit preamble units
          - At section boundary (<FP> with <E T="04">) → advance section context
          - Inside section → emit provision_candidate units per paragraph
        """
        current_section_path: list[str] = []
        current_section_heading: str | None = None
        found_first_section = False
        para_index = 0  # paragraph counter within current section

        # Collect all direct content elements in document order
        content_elements = list(doc_root)

        for elem in content_elements:
            tag = elem.tag

            if tag not in ("FP", "P"):
                # HD (heading) elements before sections can provide context
                if tag == "HD":
                    # Only use HD elements that are section headings (SOURCE="HED")
                    # that appear before any section boundary — treat as preamble header
                    pass
                continue

            # ── Check if this FP is a section boundary ─────────────────────
            if tag == "FP" and self._is_section_boundary(elem):
                current_section_path = [self._extract_section_number(elem)]
                current_section_heading = self._extract_section_heading(elem)
                found_first_section = True
                para_index = 0

                # The FP itself may contain inline text beyond the section
                # number and heading — extract it as the first paragraph
                # of this section if there's substantive text.
                text = self._extract_fp_body_text(elem)
                if text:
                    eid = self._make_element_id(
                        subtype, current_section_path, para_index
                    )
                    units.append(ExtractedUnit(
                        source_doc_id=self.doc_id,
                        source_schema=self.source_schema,
                        source_element_id=eid,
                        raw_text=text,
                        element_type="provision_candidate",
                        section_path=list(current_section_path),
                        nesting_depth=0,
                        jurisdiction_scope=_jurisdiction_scope(text),
                        extraction_notes=(
                            [f"section_heading: {current_section_heading}"]
                            if current_section_heading else []
                        ),
                    ))
                    para_index += 1
                continue

            # ── Sub-paragraph inside a section (<P> or <FP SOURCE="FP1">) ─
            if found_first_section:
                text = _element_text_clean(elem)
                if not text:
                    continue

                # Check for sub-paragraph label prefix
                subpara_label = None
                m = _SUBPARA_PATTERN.match(text)
                if m:
                    subpara_label = m.group(0)  # e.g. "(b)"
                    text = text[len(subpara_label):].strip()

                section_path = (
                    current_section_path + [subpara_label]
                    if subpara_label
                    else list(current_section_path)
                )
                eid = self._make_element_id(subtype, section_path, para_index)
                nesting = 1 if subpara_label else 0

                units.append(ExtractedUnit(
                    source_doc_id=self.doc_id,
                    source_schema=self.source_schema,
                    source_element_id=eid,
                    raw_text=text,
                    element_type="provision_candidate",
                    section_path=section_path,
                    nesting_depth=nesting,
                    jurisdiction_scope=_jurisdiction_scope(text),
                    extraction_notes=(
                        [f"section_heading: {current_section_heading}"]
                        if current_section_heading else []
                    ),
                ))
                para_index += 1

            else:
                # ── Pre-section content → preamble ──────────────────────
                text = _element_text_clean(elem)
                if not text:
                    continue

                is_preamble = bool(_PREAMBLE_PATTERNS.search(text))
                # All pre-section FP/P content is preamble (whether or not
                # it contains the authority-vested formula — the formula is
                # a useful signal but not the only preamble content).
                eid = self._make_element_id(subtype, [], para_index)
                units.append(ExtractedUnit(
                    source_doc_id=self.doc_id,
                    source_schema=self.source_schema,
                    source_element_id=eid,
                    raw_text=text,
                    element_type="preamble",
                    section_path=[],
                    nesting_depth=0,
                    jurisdiction_scope=_jurisdiction_scope(text),
                    extraction_notes=(
                        ["authority_vested_formula"] if is_preamble else []
                    ),
                ))
                para_index += 1

    # ── Helpers ────────────────────────────────────────────────────────────

    def _is_section_boundary(self, fp: etree._Element) -> bool:
        """Return True if this <FP> element marks a section boundary."""
        return any(
            child.tag == "E" and child.get("T") == "04"
            for child in fp
        )

    def _extract_section_number(self, fp: etree._Element) -> str:
        """Extract the section number text from a section-boundary <FP>."""
        for child in fp:
            if child.tag == "E" and child.get("T") == "04":
                return _element_text_clean(child)
        return "§"

    def _extract_section_heading(self, fp: etree._Element) -> str | None:
        """Extract the section heading text (<E T="03">) from a section <FP>."""
        for child in fp:
            if child.tag == "E" and child.get("T") == "03":
                return _element_text_clean(child)
        return None

    def _extract_fp_body_text(self, fp: etree._Element) -> str:
        """
        Extract non-section-number, non-heading inline text from a section
        boundary FP. This is the text that comes after the section header
        tags in the same FP element.
        """
        parts = []
        # fp.text = text before first child
        if fp.text and fp.text.strip():
            parts.append(fp.text.strip())
        for child in fp:
            # Skip the section number and heading markers
            if child.tag == "E" and child.get("T") in ("03", "04"):
                # Include tail text (text after this tag, before next sibling)
                if child.tail and child.tail.strip():
                    parts.append(child.tail.strip())
                continue
            # Include text from other inline elements
            ct = _element_text_clean(child)
            if ct:
                parts.append(ct)
            if child.tail and child.tail.strip():
                parts.append(child.tail.strip())

        text = " ".join(p for p in parts if p)
        # Clean up punctuation artifacts from stripping tags
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^[\.\s]+", "", text)  # leading periods/spaces
        return text

    def _make_element_id(
        self,
        subtype: str,
        section_path: list[str],
        para_index: int,
    ) -> str:
        """
        Construct a deterministic source_element_id.
        Format: {subtype}:{section_path_slug}:{para_index}
        """
        slug = _slugify(section_path) if section_path else "pre"
        return f"{subtype}:{slug}:{para_index}"
