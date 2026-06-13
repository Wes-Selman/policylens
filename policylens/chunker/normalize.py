"""
policylens/chunker/normalize.py

Layer 2b — Source-agnostic normalizer.

Reads ExtractedUnit records from extracted_units for a given doc_id
and produces provision records in provisions, legal_addresses, and
provision_references.

Processing steps per extracted_unit (provision_candidates only):
  1. Skip non-provision units (preamble, header)
  2. Classify element_type:
     a. Parent section already classified boilerplate → boilerplate (inheritance)
     b. Definition block intro → header (normalizer override)
     c. General Provisions boilerplate → boilerplate
     d. Otherwise → provision_candidate (unchanged)
  3. Build condition_stack
  4. Refine jurisdiction from coarse extractor signal
  5. Assign chunk_flag (priority: nested_conditional > cross_reference > boundary > clean)
  6. Construct context_text (section_heading if available; section_path label as fallback)
  7. Resolve legal_address_raw → legal_addresses + provision_references
  8. Assign provision_index (zero-based within doc_id × section_id, ordered by extracted_units.id)
  9. Write provision record (INSERT … ON CONFLICT DO UPDATE)

Design constraints:
  - Source-agnostic: no XML parsing, no source_schema branching.
  - Idempotent: re-running on an already-normalized doc is a safe overwrite.
  - Normalizer never touches cli.py or any extractor file.
  - element_type overrides (provision_candidate → boilerplate | header)
    are semantic judgments; both are sanctioned by decisions_log.md Sessions 5 & 7.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────────────

# Legislative finite verb forms used in the bare-fragment heuristic.
# Covers the modal and auxiliary verbs that appear in deontic propositions.
# Participial phrases lacking a finite verb are a known limitation (decisions_log.md Session 7).
_LEGISLATIVE_VERBS = frozenset({
    "shall", "may", "must", "will",
    "is", "are", "was", "were", "be", "been",
    "have", "has", "do", "does", "did",
})

# Bare fragment threshold: approximately 15 words, calibrated against corpus sample.
# Documented as approximate in decisions_log.md Session 7.
_BARE_FRAGMENT_MAX_WORDS = 15

# Definition block intro pattern.
# Matches: "In this Act:", "In this section—", "In this subsection:", etc.
_DEFINITION_INTRO_RE = re.compile(
    r"^In (this|the) [A-Za-z ]+[:—]\s*$",
    re.IGNORECASE,
)

# General Provisions boilerplate patterns (EO Sec. 3 formulaic language).
_BOILERPLATE_PATTERNS = [
    "Nothing in this order shall be construed to impair or otherwise affect",
    "This order shall be implemented consistent with applicable law",
    "This order is not intended to, and does not, create any right or benefit",
    "The costs for publication of this order shall be borne by",
]

# Jurisdiction refinement signals for 'involves_states' units.
_PREEMPTS_STATE_TERMS = [
    "preempt", "supersede", "displace", "occupy the field",
    "no State may", "State law is preempted",
]
_DEFERS_TO_STATE_TERMS = [
    "State may", "States may", "subject to State law",
    "as determined by the State", "State government",
]
_CREATES_FLOOR_TERMS = [
    "minimum", "at least", "not less than",
    "may provide greater", "more protective",
]

# Condition antecedent patterns → (condition_type, regex).
_CONDITION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("threshold",  re.compile(r"\bif\b.{0,60}(?:exceeds?|reaches?|falls? below|greater than|less than)", re.IGNORECASE)),
    ("existence",  re.compile(r"\bif\b.{0,60}(?:exists?|is present|has been|have been)", re.IGNORECASE)),
    ("temporal",   re.compile(r"\b(?:upon|after|before|until|once|when)\b.{0,80}(?:date|day|year|event|publication|enactment|effective)", re.IGNORECASE)),
    ("other",      re.compile(r"\b(?:if|unless|provided that|except that|subject to)\b", re.IGNORECASE)),
]


# ── Provision dataclass ────────────────────────────────────────────────────────

@dataclass
class ProvisionRecord:
    """
    Intermediate representation of a normalized provision.
    Written to the provisions table by write_provisions().
    """
    id: str                          # {doc_id}|{section_id}|{provision_index}
    doc_id: int
    extracted_unit_id: int
    section_id: str
    section_heading: Optional[str]
    provision_index: int
    text: str
    context_text: str
    doc_type: str
    element_type: str                # provision_candidate | boilerplate | header
    condition_stack: list[dict]      # [{condition_type, text}, ...]
    chunk_flag: str                  # clean | review_nested_conditional | review_cross_reference | review_boundary
    jurisdiction: str                # federal_only | preempts_state | defers_to_state | creates_floor | involves_states | unknown
    legal_address_raw: Optional[str]


# ── Classification helpers ─────────────────────────────────────────────────────

def _classify_element_type(raw_text: str) -> str:
    """
    Determine element_type for a provision_candidate unit.

    Returns one of: 'provision_candidate' | 'boilerplate' | 'header'

    Priority:
      1. Definition block intro → 'header'   (Session 7 decision)
      2. General Provisions boilerplate → 'boilerplate'   (Session 5 decision)
      3. Otherwise → 'provision_candidate' (unchanged)
    """
    # Step 1: definition block intro (structural navigation marker, no deontic content)
    if _DEFINITION_INTRO_RE.match(raw_text.strip()):
        return "header"

    # Step 2: General Provisions formulaic boilerplate
    text_lower = raw_text.lower()
    for pattern in _BOILERPLATE_PATTERNS:
        if pattern.lower() in text_lower:
            return "boilerplate"

    return "provision_candidate"


def _build_condition_stack(raw_text: str) -> list[dict]:
    """
    Scan raw_text for conditional antecedents and return a list of
    {condition_type: str, text: str} objects.

    Priority: threshold > existence > temporal > other.
    Returns [] if no conditions detected.
    """
    stack: list[dict] = []
    seen_types: set[str] = set()

    for condition_type, pattern in _CONDITION_PATTERNS:
        if condition_type in seen_types:
            continue
        match = pattern.search(raw_text)
        if match:
            # Extract a short window around the match as the condition text.
            start = max(0, match.start() - 10)
            end = min(len(raw_text), match.end() + 60)
            condition_text = raw_text[start:end].strip()
            stack.append({"condition_type": condition_type, "text": condition_text})
            seen_types.add(condition_type)

    return stack


def _refine_jurisdiction(jurisdiction_scope: str, raw_text: str) -> str:
    """
    Map the coarse extractor jurisdiction_scope to a refined provision-level value.

    'federal_only' and 'unknown' pass through unchanged.
    'involves_states' is classified by keyword heuristics.
    Priority: preempts_state > creates_floor > defers_to_state > involves_states.
    """
    if jurisdiction_scope != "involves_states":
        return jurisdiction_scope

    text_lower = raw_text.lower()

    # Preemption takes priority — explicit displacement of state law.
    if any(term.lower() in text_lower for term in _PREEMPTS_STATE_TERMS):
        return "preempts_state"

    # Floor — federal minimum, states may exceed.
    if any(term.lower() in text_lower for term in _CREATES_FLOOR_TERMS):
        return "creates_floor"

    # Deference — explicit grant of state discretion (without preemption marker).
    if any(term.lower() in text_lower for term in _DEFERS_TO_STATE_TERMS):
        return "defers_to_state"

    # Pattern present but relationship undetermined.
    return "involves_states"


def _assign_chunk_flag(
    condition_stack: list[dict],
    legal_address_raw: Optional[str],
    raw_text: str,
) -> str:
    """
    Assign chunk_flag using priority order from decisions_log.md Session 7.

    Priority (highest wins):
      1. condition_stack depth > 2 → review_nested_conditional
      2. legal_address_raw not None, OR inline U.S.C. citation detected
         in raw_text → review_cross_reference
      3. Atomicity heuristic fires → review_boundary
      4. Otherwise → clean

    Note on priority 2: legal_address_raw is null across the entire current
    corpus (citations appear in prose, not in structured XML attributes).
    The inline citation fallback ensures provisions that reference U.S.C.
    sections are correctly flagged for cross-reference review regardless of
    whether the extractor surfaced the citation into legal_address_raw.
    """
    # Priority 1: nested conditional (Session 3 decision, ≥3 layers)
    if len(condition_stack) > 2:
        return "review_nested_conditional"

    # Priority 2: cross-reference — explicit legal_address_raw or inline citation
    has_cross_ref = (
        legal_address_raw is not None
        or bool(_CITATION_RE.search(raw_text))
    )
    if has_cross_ref:
        return "review_cross_reference"

    # Priority 3: atomicity heuristic
    if _is_boundary_fragment(raw_text):
        return "review_boundary"

    return "clean"


def _is_boundary_fragment(raw_text: str) -> bool:
    """
    Return True if the text appears to be an atomically incomplete fragment
    requiring boundary review.

    Two signals (decisions_log.md Session 7):
      A. Em-dash stub: raw_text ends with U+2014 em-dash (—).
         Applied regardless of text length.
      B. Bare fragment: no legislative finite verb AND ≤15 words AND
         does not end with em-dash (to avoid double-counting Pattern A).
    """
    stripped = raw_text.strip()

    # Signal A: em-dash continuation stub
    if stripped.endswith("—"):
        return True

    # Signal B: bare noun/verb phrase
    words = stripped.split()
    if len(words) <= _BARE_FRAGMENT_MAX_WORDS:
        words_lower = {w.rstrip(".,;:—").lower() for w in words}
        if not words_lower.intersection(_LEGISLATIVE_VERBS):
            return True

    return False


def _build_context_text(
    doc_type: str,
    doc_title: Optional[str],
    section_heading: Optional[str],
    condition_stack: list[dict],
    provision_text: str,
    section_path: Optional[list[str]] = None,
) -> str:
    """
    Construct the context_text field for vector embedding.

    Format (decisions_log.md Session 4):
      "[{doc_type} — {doc_title} — {section_label}]
       {condition_stack_summary if non-empty}
       Text: {provision_text}"

    section_label is section_heading when available (USLM header units),
    otherwise falls back to the joined section_path (FR and other sources
    that embed headings inline rather than as separate header units).

    context_text is stable across annotation passes; only changes when
    structural metadata changes (title, section heading).
    """
    header_parts = [doc_type or "unknown"]
    if doc_title:
        header_parts.append(doc_title)

    # Use explicit heading if available; fall back to section_path label.
    section_label = section_heading
    if not section_label and section_path:
        section_label = _section_id_from_path(section_path)
    if section_label:
        header_parts.append(section_label)

    header = "[" + " — ".join(header_parts) + "]"

    lines = [header]

    if condition_stack:
        condition_summary = "; ".join(
            f"{c['condition_type']}: {c['text'][:80]}"
            for c in condition_stack
        )
        lines.append(f"Conditions: {condition_summary}")

    lines.append(f"Text: {provision_text}")

    return "\n".join(lines)


# ── Legal address helpers ──────────────────────────────────────────────────────

# Citation patterns for cross-reference detection.
# Two variants found in corpus:
#   1. "26 U.S.C. § 7701" or "8 U.S.C. 1226(c)(1)" — abbreviated form
#   2. "section 553 of title 5, United States Code" — long form
# Both are used in USLM bills and FR executive orders.
_CITATION_RE = re.compile(
    r"(\d+)\s+U\.S\.C\.?(?:\s+(?:§+\s*)?\w[\w\-\.]*)?|title\s+\d+,\s+United\s+States\s+Code",
    re.IGNORECASE,
)


_LONG_FORM_CITATION_RE = re.compile(
    r"section\s+([\w\-\.]+)\s+of\s+title\s+(\d+),\s+United\s+States\s+Code",
    re.IGNORECASE,
)


def _parse_legal_address(raw: str) -> tuple[str, str] | None:
    """
    Parse a raw citation string into (statute, section).
    Returns None if unparseable.

    Handles two variants:
      Short form: "26 U.S.C. § 7701"       → ("26 U.S.C.", "§ 7701")
      Long form:  "section 553 of title 5, United States Code"
                                             → ("5 U.S.C.", "§ 553")
    """
    # Try long form first — more specific, less ambiguous
    long_match = _LONG_FORM_CITATION_RE.search(raw)
    if long_match:
        section_num = long_match.group(1)
        title_num = long_match.group(2)
        return f"{title_num} U.S.C.", f"§ {section_num}"

    # Fall back to short form
    short_match = re.search(
        r"(\d+)\s+U\.S\.C\.?\s+(?:§+\s*)?(\w[\w\-\.]*)",
        raw,
        re.IGNORECASE,
    )
    if short_match:
        return f"{short_match.group(1)} U.S.C.", f"§ {short_match.group(2)}"

    return None


def upsert_legal_address(conn, statute: str, section: str) -> int:
    """
    Upsert a legal_address row. Returns the id (existing or newly inserted).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO legal_addresses (statute, section, canonical_cite)
            VALUES (%s, %s, %s)
            ON CONFLICT (statute, section) DO UPDATE
              SET canonical_cite = EXCLUDED.canonical_cite
            RETURNING id
            """,
            (statute, section, f"{statute} {section}"),
        )
        return cur.fetchone()[0]


def insert_provision_reference(
    conn,
    provision_id: str,
    legal_address_id: int,
    ref_type: str = "references",
) -> None:
    """
    Insert a provision_reference edge. Idempotent (ON CONFLICT DO NOTHING).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO provision_references (provision_id, legal_address_id, ref_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (provision_id, legal_address_id, ref_type) DO NOTHING
            """,
            (provision_id, legal_address_id, ref_type),
        )


# ── Main normalization entry point ─────────────────────────────────────────────

def _has_boilerplate_ancestor(
    section_path: list[str],
    boilerplate_prefixes: set[str],
) -> bool:
    """
    Return True if any strict prefix of section_path is in boilerplate_prefixes.

    Used to propagate boilerplate classification from a parent unit to its
    child list items (e.g. Sec. 3(a) → Sec. 3(i), Sec. 3(ii)).

    Strict prefix only: the unit's own path is not checked here —
    that check happens in _classify_element_type via boilerplate pattern matching.
    """
    for length in range(1, len(section_path)):
        key = _section_path_key(section_path[:length])
        if key in boilerplate_prefixes:
            return True
    return False


def normalize_document(conn, doc: dict) -> dict:
    """
    Normalize all extracted_units for a single document.

    Reads extracted_units for doc['id'], writes to provisions,
    legal_addresses, provision_references.

    Returns a summary dict:
      {
        'doc_id': int,
        'provisions_written': int,
        'chunk_flag_counts': {flag: count},
        'element_type_counts': {type: count},
        'errors': [str],
      }
    """
    doc_id = doc["id"]
    doc_type = doc.get("doc_type", "unknown")
    doc_title = doc.get("title")

    summary = {
        "doc_id": doc_id,
        "provisions_written": 0,
        "chunk_flag_counts": {},
        "element_type_counts": {},
        "errors": [],
    }

    with conn.cursor() as cur:
        # Fetch all extracted_units for this document, ordered by id for
        # deterministic provision_index assignment.
        cur.execute(
            """
            SELECT id, element_type, section_path, raw_text,
                   legal_address_raw, nesting_depth, jurisdiction_scope
            FROM extracted_units
            WHERE doc_id = %s
            ORDER BY id ASC
            """,
            (doc_id,),
        )
        cols = [d[0] for d in cur.description]
        units = [dict(zip(cols, row)) for row in cur.fetchall()]

    # Collect preamble text for context_text construction (all preamble units
    # in the document, concatenated; used as doc-level context for sibling provisions).
    preamble_texts = [
        u["raw_text"] for u in units if u["element_type"] == "preamble"
    ]
    # Not used inline yet — section_heading and doc_title carry the context.
    # Retained for potential future context_text enrichment.
    _ = preamble_texts

    # Fetch section headings: for USLM, header units immediately precede their
    # section's provision_candidates and share the same section_path prefix.
    # Build a map of section_path_key → heading text for context_text construction.
    section_heading_map: dict[str, str] = {}
    for u in units:
        if u["element_type"] == "header" and u["section_path"]:
            key = _section_path_key(u["section_path"])
            section_heading_map[key] = u["raw_text"]

    # Track provision_index per (doc_id, section_id) group.
    provision_index_counter: dict[str, int] = {}

    # Track section path prefixes that have been classified boilerplate.
    # Used to propagate boilerplate classification to child list items
    # (e.g. Sec. 3(i), Sec. 3(ii) as children of a boilerplate Sec. 3(a)).
    boilerplate_section_prefixes: set[str] = set()

    for unit in units:
        # Step 1: skip preamble and header units — not written as provisions.
        if unit["element_type"] in ("preamble", "header"):
            continue

        raw_text = unit["raw_text"] or ""
        section_path = unit["section_path"] or []
        section_id = _section_id_from_path(section_path)
        extracted_unit_id = unit["id"]

        try:
            # Step 2: classify element_type.
            # Check parent boilerplate inheritance before text-based classification:
            # if any prefix of this unit's section_path was classified boilerplate,
            # this unit is a continuation list item of that boilerplate clause.
            if _has_boilerplate_ancestor(section_path, boilerplate_section_prefixes):
                element_type = "boilerplate"
            else:
                element_type = _classify_element_type(raw_text)

            # Record all path prefixes of a boilerplate unit so that children
            # at any depth beneath it will match _has_boilerplate_ancestor.
            # e.g. classifying ["Sec. 3", "(a)"] as boilerplate registers
            # both "Sec. 3" and "Sec. 3|(a)" so that ["Sec. 3", "(i)"] matches
            # at the "Sec. 3" level.
            if element_type == "boilerplate" and section_path:
                for length in range(1, len(section_path) + 1):
                    boilerplate_section_prefixes.add(_section_path_key(section_path[:length]))

            # Step 3: build condition_stack (only for provision_candidates;
            # boilerplate and header don't need condition analysis)
            condition_stack: list[dict] = []
            if element_type == "provision_candidate":
                condition_stack = _build_condition_stack(raw_text)

            # Step 4: refine jurisdiction
            jurisdiction = _refine_jurisdiction(
                unit["jurisdiction_scope"], raw_text
            )

            # Step 5: assign chunk_flag
            # header and boilerplate get 'clean' — they are not reviewed for
            # boundary issues; their classification is the outcome.
            if element_type in ("header", "boilerplate"):
                chunk_flag = "clean"
            else:
                chunk_flag = _assign_chunk_flag(
                    condition_stack,
                    unit["legal_address_raw"],
                    raw_text,
                )

            # Step 6: build context_text
            section_heading = _lookup_section_heading(
                section_path, section_heading_map
            )
            context_text = _build_context_text(
                doc_type=doc_type,
                doc_title=doc_title,
                section_heading=section_heading,
                condition_stack=condition_stack,
                provision_text=raw_text,
                section_path=section_path,
            )

            # Step 7: legal address resolution
            legal_address_raw = unit["legal_address_raw"]

            # Step 8: provision_index (zero-based within doc_id × section_id)
            group_key = f"{doc_id}|{section_id}"
            idx = provision_index_counter.get(group_key, 0)
            provision_index_counter[group_key] = idx + 1

            # Step 9: write provision record
            provision_id = f"{doc_id}|{section_id}|{idx}"

            _write_provision(
                conn=conn,
                provision_id=provision_id,
                doc_id=doc_id,
                extracted_unit_id=extracted_unit_id,
                section_id=section_id,
                section_heading=section_heading,
                provision_index=idx,
                text=raw_text,
                context_text=context_text,
                doc_type=doc_type,
                element_type=element_type,
                condition_stack=condition_stack,
                chunk_flag=chunk_flag,
                jurisdiction=jurisdiction,
            )

            # Step 7b: resolve legal address (after provision written so we have provision_id)
            if legal_address_raw:
                parsed = _parse_legal_address(legal_address_raw)
                if parsed:
                    statute, section = parsed
                    legal_address_id = upsert_legal_address(conn, statute, section)
                    insert_provision_reference(conn, provision_id, legal_address_id, "references")

            # Accumulate summary counts
            summary["provisions_written"] += 1
            summary["chunk_flag_counts"][chunk_flag] = (
                summary["chunk_flag_counts"].get(chunk_flag, 0) + 1
            )
            summary["element_type_counts"][element_type] = (
                summary["element_type_counts"].get(element_type, 0) + 1
            )

        except Exception as exc:
            summary["errors"].append(
                f"extracted_unit id={extracted_unit_id} section={section_id}: {exc}"
            )

    return summary


# ── DB write helper ────────────────────────────────────────────────────────────

def _write_provision(
    conn,
    provision_id: str,
    doc_id: int,
    extracted_unit_id: int,
    section_id: str,
    section_heading: Optional[str],
    provision_index: int,
    text: str,
    context_text: str,
    doc_type: str,
    element_type: str,
    condition_stack: list[dict],
    chunk_flag: str,
    jurisdiction: str,
) -> None:
    """
    Upsert a provision record.
    ON CONFLICT (doc_id, section_id, provision_index) DO UPDATE
    ensures idempotent re-runs safely overwrite existing records.
    """
    import json

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO provisions (
                id, doc_id, extracted_unit_id,
                section_id, section_heading, provision_index,
                text, context_text, doc_type, element_type,
                condition_stack, chunk_flag, jurisdiction
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id, section_id, provision_index) DO UPDATE SET
                extracted_unit_id = EXCLUDED.extracted_unit_id,
                section_heading    = EXCLUDED.section_heading,
                text               = EXCLUDED.text,
                context_text       = EXCLUDED.context_text,
                doc_type           = EXCLUDED.doc_type,
                element_type       = EXCLUDED.element_type,
                condition_stack    = EXCLUDED.condition_stack,
                chunk_flag         = EXCLUDED.chunk_flag,
                jurisdiction       = EXCLUDED.jurisdiction
            """,
            (
                provision_id,
                doc_id,
                extracted_unit_id,
                section_id,
                section_heading,
                provision_index,
                text,
                context_text,
                doc_type,
                element_type,
                json.dumps(condition_stack),
                chunk_flag,
                jurisdiction,
            ),
        )


# ── Section path helpers ───────────────────────────────────────────────────────

def _section_id_from_path(section_path: list[str]) -> str:
    """
    Construct a human-readable section_id from section_path.
    Mirrors ExtractedUnit.section_id property.
    Example: ['Sec. 2', '(b)'] → 'Sec. 2(b)'
    Example: [] → 'root'
    """
    return "".join(section_path) if section_path else "root"


def _section_path_key(section_path: list[str]) -> str:
    """Stable string key for section_path list, for dict lookup."""
    return "|".join(section_path)


def _lookup_section_heading(
    section_path: list[str],
    heading_map: dict[str, str],
) -> Optional[str]:
    """
    Find the heading for this section_path by walking up the path hierarchy.
    Tries the full path first, then progressively shorter prefixes.
    Returns None if no heading found.
    """
    for length in range(len(section_path), 0, -1):
        key = _section_path_key(section_path[:length])
        if key in heading_map:
            return heading_map[key]
    return None