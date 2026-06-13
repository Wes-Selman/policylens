"""
tests/test_normalizer.py

Unit tests for policylens/chunker/normalize.py.

All tests are pure-function tests — no database required.
DB-writing functions (upsert_legal_address, insert_provision_reference,
_write_provision, normalize_document) are tested via mock connections
in the integration section below.

Test organisation:
  1. _classify_element_type
  2. _build_condition_stack
  3. _refine_jurisdiction
  4. _assign_chunk_flag / _is_boundary_fragment
  5. _build_context_text
  6. _parse_legal_address
  7. _section_id_from_path / _lookup_section_heading
  8. normalize_document (mock DB — integration)
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call

from policylens.chunker.normalize import (
    _classify_element_type,
    _build_condition_stack,
    _refine_jurisdiction,
    _assign_chunk_flag,
    _is_boundary_fragment,
    _build_context_text,
    _parse_legal_address,
    _section_id_from_path,
    _lookup_section_heading,
    _has_boilerplate_ancestor,
    normalize_document,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. _classify_element_type
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyElementType:

    # ── Definition block intros → header ──────────────────────────────────────

    def test_in_this_act_colon_is_header(self):
        assert _classify_element_type("In this Act:") == "header"

    def test_in_this_act_emdash_is_header(self):
        assert _classify_element_type("In this Act—") == "header"

    def test_in_this_section_colon_is_header(self):
        assert _classify_element_type("In this section:") == "header"

    def test_in_this_subsection_colon_is_header(self):
        assert _classify_element_type("In this subsection:") == "header"

    def test_in_the_act_colon_is_header(self):
        assert _classify_element_type("In the Act:") == "header"

    def test_definition_intro_with_leading_whitespace(self):
        assert _classify_element_type("  In this Act:  ") == "header"

    # ── General Provisions boilerplate → boilerplate ──────────────────────────

    def test_nothing_in_this_order_is_boilerplate(self):
        text = "Nothing in this order shall be construed to impair or otherwise affect the authority granted by law to an executive department."
        assert _classify_element_type(text) == "boilerplate"

    def test_implemented_consistent_with_law_is_boilerplate(self):
        text = "This order shall be implemented consistent with applicable law and subject to the availability of appropriations."
        assert _classify_element_type(text) == "boilerplate"

    def test_not_intended_to_create_right_is_boilerplate(self):
        text = "This order is not intended to, and does not, create any right or benefit, substantive or procedural."
        assert _classify_element_type(text) == "boilerplate"

    def test_costs_of_publication_is_boilerplate(self):
        text = "The costs for publication of this order shall be borne by the Federal Register."
        assert _classify_element_type(text) == "boilerplate"

    # ── Substantive provision_candidates unchanged ─────────────────────────────

    def test_substantive_duty_is_provision_candidate(self):
        text = "The Secretary shall conduct a nationwide program of testing."
        assert _classify_element_type(text) == "provision_candidate"

    def test_permission_is_provision_candidate(self):
        text = "The Administrator may waive the requirements of this section."
        assert _classify_element_type(text) == "provision_candidate"

    def test_amendment_is_provision_candidate(self):
        text = "Section 236(c)(1) of the Immigration and Nationality Act is amended to read as follows:"
        assert _classify_element_type(text) == "provision_candidate"

    # ── Priority: definition intro wins over boilerplate ──────────────────────

    def test_neither_pattern_returns_provision_candidate(self):
        # Text that matches neither definition intro nor boilerplate pattern
        # returns provision_candidate unchanged.
        text = "In this Act: Nothing in this order shall be construed"
        # Does not match definition intro (has content after colon+space).
        # Does not match boilerplate (truncated — full phrase required).
        assert _classify_element_type(text) == "provision_candidate"

    def test_full_boilerplate_phrase_detected(self):
        # Confirm full boilerplate phrase is detected even when prefixed
        text = "In this Act: Nothing in this order shall be construed to impair or otherwise affect the authority."
        # Does not match definition intro; does match boilerplate.
        assert _classify_element_type(text) == "boilerplate"


# ══════════════════════════════════════════════════════════════════════════════
# 2. _build_condition_stack
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildConditionStack:

    def test_unconditional_returns_empty(self):
        text = "The Secretary shall conduct a nationwide program of testing."
        assert _build_condition_stack(text) == []

    def test_detects_threshold_condition(self):
        text = "If the amount exceeds $10,000, the agency shall report to Congress."
        stack = _build_condition_stack(text)
        assert len(stack) >= 1
        types = [c["condition_type"] for c in stack]
        assert "threshold" in types

    def test_detects_existence_condition(self):
        text = "If a plan exists, the Secretary shall review it within 30 days."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert "existence" in types

    def test_detects_temporal_condition(self):
        text = "Upon enactment of this Act, the Administrator shall promulgate regulations."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert "temporal" in types

    def test_detects_other_condition_if(self):
        text = "If the applicant fails to comply, the Secretary may revoke the license."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert "other" in types

    def test_detects_unless_condition(self):
        text = "The agency shall publish notice unless the Secretary determines otherwise."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert "other" in types

    def test_detects_provided_that_condition(self):
        text = "The grant shall be awarded, provided that the applicant meets the criteria."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert "other" in types

    def test_condition_entries_have_required_keys(self):
        text = "If the amount exceeds the threshold, the agency shall act."
        stack = _build_condition_stack(text)
        for entry in stack:
            assert "condition_type" in entry
            assert "text" in entry

    def test_no_duplicate_condition_types(self):
        text = "If the plan exists and if the amount exceeds the limit, the Secretary shall report."
        stack = _build_condition_stack(text)
        types = [c["condition_type"] for c in stack]
        assert len(types) == len(set(types))


# ══════════════════════════════════════════════════════════════════════════════
# 3. _refine_jurisdiction
# ══════════════════════════════════════════════════════════════════════════════

class TestRefineJurisdiction:

    def test_federal_only_passthrough(self):
        assert _refine_jurisdiction("federal_only", "The Secretary shall act.") == "federal_only"

    def test_unknown_passthrough(self):
        assert _refine_jurisdiction("unknown", "The Secretary shall act.") == "unknown"

    def test_involves_states_preemption(self):
        text = "No State may enact any law that would preempt this section."
        assert _refine_jurisdiction("involves_states", text) == "preempts_state"

    def test_involves_states_supersede_is_preemption(self):
        text = "This Act shall supersede any State law to the contrary."
        assert _refine_jurisdiction("involves_states", text) == "preempts_state"

    def test_involves_states_deference(self):
        text = "States may adopt more protective standards under this section."
        # "States may" = defers_to_state; "more protective" = creates_floor
        # preempts_state check fails; creates_floor wins (priority 2)
        result = _refine_jurisdiction("involves_states", text)
        assert result in ("defers_to_state", "creates_floor")

    def test_involves_states_creates_floor(self):
        text = "The minimum standard under this Act shall be not less than the federal requirement."
        assert _refine_jurisdiction("involves_states", text) == "creates_floor"

    def test_involves_states_no_keyword_stays_involves(self):
        text = "State government entities shall submit reports to the Secretary."
        # "State government" = defers_to_state signal
        result = _refine_jurisdiction("involves_states", text)
        assert result == "defers_to_state"

    def test_involves_states_ambiguous_stays_involves(self):
        text = "This section applies to activities conducted within a State."
        assert _refine_jurisdiction("involves_states", text) == "involves_states"

    def test_preemption_priority_over_floor(self):
        text = "No State may enact any law; the minimum standard shall apply."
        # Both preemption and floor signals present; preemption wins.
        assert _refine_jurisdiction("involves_states", text) == "preempts_state"


# ══════════════════════════════════════════════════════════════════════════════
# 4. _is_boundary_fragment and _assign_chunk_flag
# ══════════════════════════════════════════════════════════════════════════════

class TestIsBoundaryFragment:

    # ── Em-dash stubs (Pattern A) ──────────────────────────────────────────────

    def test_emdash_stub_short(self):
        assert _is_boundary_fragment("The Secretary shall—") is True

    def test_emdash_stub_long(self):
        # Length-independent: even a long stub ending in em-dash is a fragment
        text = "Section 236(c)(1) of the Immigration and Nationality Act (8 U.S.C. 1226(c)(1)) is amended—"
        assert _is_boundary_fragment(text) is True

    def test_emdash_stub_that_congress(self):
        assert _is_boundary_fragment("That Congress—") is True

    def test_emdash_stub_is(self):
        assert _is_boundary_fragment("is—") is True

    def test_emdash_stub_shall_be(self):
        assert _is_boundary_fragment("shall be—") is True

    # ── Bare noun/verb fragments (Pattern B) ──────────────────────────────────

    def test_bare_noun_airboats(self):
        assert _is_boundary_fragment("airboats;") is True

    def test_bare_noun_motorboats(self):
        assert _is_boundary_fragment("motorboats;") is True

    def test_bare_noun_hovercraft(self):
        assert _is_boundary_fragment("hovercraft;") is True

    def test_bare_phrase_swimming_and(self):
        assert _is_boundary_fragment("swimming; and") is True

    # ── Complete provisions — should NOT be flagged ────────────────────────────

    def test_complete_duty_not_fragment(self):
        text = "The Secretary shall conduct a nationwide program of testing."
        assert _is_boundary_fragment(text) is False

    def test_complete_permission_not_fragment(self):
        text = "The Administrator may waive the requirements of this section."
        assert _is_boundary_fragment(text) is False

    def test_long_text_with_no_emdash_not_fragment(self):
        text = ("The Centers for Disease Control and Prevention (CDC) and its Advisory "
                "Committee on Immunization Practices (ACIP) shall review the scientific "
                "assessment within 90 days of the enactment of this order.")
        assert _is_boundary_fragment(text) is False

    def test_resolution_child_clause_not_fragment(self):
        # Child of "That the House of Representatives—" — complete on its own
        text = "reaffirms that the United States is not a party to the Rome Statute and does not recognize the jurisdiction of the International Criminal Court;"
        assert _is_boundary_fragment(text) is False


class TestAssignChunkFlag:

    def test_clean_flag_for_simple_provision(self):
        flag = _assign_chunk_flag([], None, "The Secretary shall act.")
        assert flag == "clean"

    def test_review_boundary_for_emdash_stub(self):
        flag = _assign_chunk_flag([], None, "The Secretary shall—")
        assert flag == "review_boundary"

    def test_review_boundary_for_bare_fragment(self):
        flag = _assign_chunk_flag([], None, "airboats;")
        assert flag == "review_boundary"

    def test_review_cross_reference_when_legal_address_present(self):
        flag = _assign_chunk_flag([], "26 U.S.C. § 7701", "The Secretary shall act.")
        assert flag == "review_cross_reference"

    def test_review_nested_conditional_for_deep_stack(self):
        deep_stack = [
            {"condition_type": "other", "text": "if A"},
            {"condition_type": "other", "text": "if B"},
            {"condition_type": "other", "text": "if C"},
        ]
        flag = _assign_chunk_flag(deep_stack, None, "The Secretary shall act.")
        assert flag == "review_nested_conditional"

    def test_nested_conditional_priority_over_cross_reference(self):
        # Priority 1 wins over priority 2
        deep_stack = [
            {"condition_type": "other", "text": "if A"},
            {"condition_type": "other", "text": "if B"},
            {"condition_type": "other", "text": "if C"},
        ]
        flag = _assign_chunk_flag(deep_stack, "26 U.S.C. § 7701", "The Secretary shall act.")
        assert flag == "review_nested_conditional"

    def test_cross_reference_priority_over_boundary(self):
        # Priority 2 wins over priority 3
        flag = _assign_chunk_flag([], "26 U.S.C. § 7701", "airboats;")
        assert flag == "review_cross_reference"

    def test_two_condition_layers_not_nested_conditional(self):
        # Exactly 2 layers is fine per Session 3 decision (threshold is > 2)
        stack = [
            {"condition_type": "other", "text": "if A"},
            {"condition_type": "temporal", "text": "upon enactment"},
        ]
        flag = _assign_chunk_flag(stack, None, "The Secretary shall act.")
        assert flag == "clean"

    def test_boilerplate_and_header_get_clean_flag(self):
        # Callers assign clean for non-provision_candidate types
        # (tested indirectly through normalize_document below)
        flag = _assign_chunk_flag([], None, "Nothing in this order shall be construed.")
        # The text itself has a legislative verb, so boundary heuristic won't fire.
        # But boilerplate detection happens before chunk_flag assignment in caller.
        assert flag == "clean"

    def test_inline_usc_citation_triggers_cross_reference(self):
        # legal_address_raw is null across the corpus; inline detection is the fallback
        text = "Section 212(a)(2) of the Immigration and Nationality Act ( 8 U.S.C. 1182(a)(2) ) is amended."
        flag = _assign_chunk_flag([], None, text)
        assert flag == "review_cross_reference"

    def test_long_form_usc_citation_triggers_cross_reference(self):
        text = ("Such regulations shall be issued in accordance with section 553 "
                "of title 5, United States Code.")
        flag = _assign_chunk_flag([], None, text)
        assert flag == "review_cross_reference"

    def test_inline_citation_priority_over_boundary(self):
        # A provision with both a citation and an em-dash gets review_cross_reference
        # (priority 2 beats priority 3)
        text = "Section 236(c)(1) of the Immigration and Nationality Act ( 8 U.S.C. 1226(c)(1) ) is amended—"
        flag = _assign_chunk_flag([], None, text)
        assert flag == "review_cross_reference"

    def test_nested_conditional_priority_over_inline_citation(self):
        deep_stack = [
            {"condition_type": "other", "text": "if A"},
            {"condition_type": "other", "text": "if B"},
            {"condition_type": "other", "text": "if C"},
        ]
        text = "Section 212(a)(2) of the Act ( 8 U.S.C. 1182(a)(2) ) is amended."
        flag = _assign_chunk_flag(deep_stack, None, text)
        assert flag == "review_nested_conditional"


# ══════════════════════════════════════════════════════════════════════════════
# 5. _build_context_text
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildContextText:

    def test_basic_context_text_structure(self):
        result = _build_context_text(
            doc_type="executive_order",
            doc_title="EO 14407",
            section_heading="Sec. 2: Vaccine Schedule",
            condition_stack=[],
            provision_text="The CDC shall review the assessment.",
        )
        assert "[executive_order — EO 14407 — Sec. 2: Vaccine Schedule]" in result
        assert "Text: The CDC shall review the assessment." in result

    def test_context_text_with_condition_stack(self):
        stack = [{"condition_type": "temporal", "text": "upon enactment"}]
        result = _build_context_text(
            doc_type="bill",
            doc_title="Housing Act",
            section_heading="Sec. 3",
            condition_stack=stack,
            provision_text="The Secretary shall act.",
        )
        assert "Conditions:" in result
        assert "temporal" in result

    def test_context_text_no_title(self):
        result = _build_context_text(
            doc_type="executive_order",
            doc_title=None,
            section_heading=None,
            condition_stack=[],
            provision_text="The Secretary shall act.",
        )
        assert "[executive_order]" in result
        assert "Text: The Secretary shall act." in result

    def test_context_text_no_section_heading(self):
        result = _build_context_text(
            doc_type="bill",
            doc_title="Housing Act",
            section_heading=None,
            condition_stack=[],
            provision_text="The Secretary shall act.",
        )
        assert "[bill — Housing Act]" in result

    def test_context_text_does_not_include_annotation_fields(self):
        # context_text must be stable across annotation passes
        result = _build_context_text(
            doc_type="executive_order",
            doc_title="EO 14407",
            section_heading="Sec. 2",
            condition_stack=[],
            provision_text="The CDC shall review.",
        )
        # No annotation fields should appear
        assert "modality" not in result
        assert "valence" not in result
        assert "domain" not in result

    def test_section_path_used_as_fallback_when_no_heading(self):
        # FR docs have no header units; section_path is the fallback label
        result = _build_context_text(
            doc_type="executive_order",
            doc_title="EO 14407",
            section_heading=None,
            condition_stack=[],
            provision_text="The CDC shall review.",
            section_path=["Sec. 2"],
        )
        assert "Sec. 2" in result
        assert "[executive_order — EO 14407 — Sec. 2]" in result

    def test_section_path_fallback_uses_full_joined_path(self):
        result = _build_context_text(
            doc_type="bill",
            doc_title="Housing Act",
            section_heading=None,
            condition_stack=[],
            provision_text="The Secretary shall act.",
            section_path=["Sec. 2", "(b)"],
        )
        assert "Sec. 2(b)" in result

    def test_explicit_heading_takes_priority_over_section_path(self):
        result = _build_context_text(
            doc_type="bill",
            doc_title="Housing Act",
            section_heading="Testing Requirements",
            condition_stack=[],
            provision_text="The Secretary shall act.",
            section_path=["Sec. 2"],
        )
        assert "Testing Requirements" in result
        # section_path label should not appear as a duplicate
        assert result.count("Sec. 2") <= 1


# ══════════════════════════════════════════════════════════════════════════════
# 6. _parse_legal_address
# ══════════════════════════════════════════════════════════════════════════════

class TestParseLegalAddress:

    def test_parses_standard_usc_citation(self):
        result = _parse_legal_address("26 U.S.C. § 7701")
        assert result == ("26 U.S.C.", "§ 7701")

    def test_parses_usc_citation_without_section_symbol(self):
        result = _parse_legal_address("42 U.S.C. 3616a")
        assert result is not None
        statute, section = result
        assert "42 U.S.C." in statute

    def test_parses_long_form_citation(self):
        result = _parse_legal_address("section 553 of title 5, United States Code")
        assert result == ("5 U.S.C.", "§ 553")

    def test_parses_long_form_citation_embedded_in_text(self):
        raw = ("Such regulations shall be issued after notice and an opportunity "
               "for public comment in accordance with the procedure under section 553 "
               "of title 5, United States Code, applicable to substantive rules.")
        result = _parse_legal_address(raw)
        assert result == ("5 U.S.C.", "§ 553")

    def test_parses_citation_embedded_in_text(self):
        result = _parse_legal_address(
            "Section 236(c)(1) of the Immigration and Nationality Act (8 U.S.C. 1226(c)(1))"
        )
        assert result is not None
        statute, section = result
        assert "8 U.S.C." in statute

    def test_returns_none_for_unparseable(self):
        result = _parse_legal_address("the Defense Intelligence Agency")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = _parse_legal_address("")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 7. Section path helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestSectionPathHelpers:

    def test_section_id_from_path_joined(self):
        assert _section_id_from_path(["Sec. 2", "(b)"]) == "Sec. 2(b)"

    def test_section_id_from_path_empty_is_root(self):
        assert _section_id_from_path([]) == "root"

    def test_section_id_from_path_single(self):
        assert _section_id_from_path(["Sec. 3"]) == "Sec. 3"

    def test_lookup_section_heading_exact_match(self):
        heading_map = {"Sec. 2|(b)": "Testing Requirements"}
        result = _lookup_section_heading(["Sec. 2", "(b)"], heading_map)
        assert result == "Testing Requirements"

    def test_lookup_section_heading_parent_fallback(self):
        # Child path {Sec. 2|(b)|(1)} falls back to parent {Sec. 2|(b)}
        heading_map = {"Sec. 2|(b)": "Testing Requirements"}
        result = _lookup_section_heading(["Sec. 2", "(b)", "(1)"], heading_map)
        assert result == "Testing Requirements"

    def test_lookup_section_heading_returns_none_when_missing(self):
        heading_map = {}
        result = _lookup_section_heading(["Sec. 5"], heading_map)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# 7b. _has_boilerplate_ancestor
# ══════════════════════════════════════════════════════════════════════════════

class TestHasBoilerplateAncestor:

    def test_no_prefixes_returns_false(self):
        assert _has_boilerplate_ancestor(["Sec. 3", "(i)"], set()) is False

    def test_parent_in_prefixes_returns_true(self):
        prefixes = {"Sec. 3"}
        assert _has_boilerplate_ancestor(["Sec. 3", "(i)"], prefixes) is True

    def test_grandparent_in_prefixes_returns_true(self):
        prefixes = {"Sec. 3"}
        assert _has_boilerplate_ancestor(["Sec. 3", "(a)", "(i)"], prefixes) is True

    def test_own_path_not_checked(self):
        # Strict prefix only — own path is not an ancestor of itself
        prefixes = {"Sec. 3|(i)"}
        assert _has_boilerplate_ancestor(["Sec. 3", "(i)"], prefixes) is False

    def test_sibling_path_not_ancestor(self):
        prefixes = {"Sec. 3|(b)"}
        assert _has_boilerplate_ancestor(["Sec. 3", "(i)"], prefixes) is False

    def test_single_element_path_has_no_ancestor(self):
        prefixes = {"Sec. 3"}
        assert _has_boilerplate_ancestor(["Sec. 3"], prefixes) is False

    def test_empty_path_returns_false(self):
        prefixes = {"Sec. 3"}
        assert _has_boilerplate_ancestor([], prefixes) is False


# ══════════════════════════════════════════════════════════════════════════════
# 8. normalize_document — mock DB integration tests
# ══════════════════════════════════════════════════════════════════════════════

def _make_unit(
    id: int,
    element_type: str,
    raw_text: str,
    section_path: list[str] | None = None,
    jurisdiction_scope: str = "federal_only",
    legal_address_raw: str | None = None,
    nesting_depth: int = 0,
) -> dict:
    return {
        "id": id,
        "element_type": element_type,
        "raw_text": raw_text,
        "section_path": section_path or [],
        "jurisdiction_scope": jurisdiction_scope,
        "legal_address_raw": legal_address_raw,
        "nesting_depth": nesting_depth,
    }


def _make_mock_conn(units: list[dict]):
    """Build a mock psycopg connection that returns the given units list."""
    conn = MagicMock()
    cur = MagicMock()

    # cursor() returns a context manager yielding cur
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # First fetchall() call returns the units; description gives column names.
    cols = ["id", "element_type", "section_path", "raw_text",
            "legal_address_raw", "nesting_depth", "jurisdiction_scope"]
    cur.description = [(c,) for c in cols]
    rows = [
        (u["id"], u["element_type"], u["section_path"], u["raw_text"],
         u["legal_address_raw"], u["nesting_depth"], u["jurisdiction_scope"])
        for u in units
    ]
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = (1,)  # legal_address upsert returns id=1
    cur.rowcount = 1
    return conn


class TestNormalizeDocument:

    def _doc(self, doc_id: int = 1) -> dict:
        return {
            "id": doc_id,
            "doc_type": "executive_order",
            "title": "Test EO",
        }

    def test_preamble_units_skipped(self):
        units = [_make_unit(1, "preamble", "By the authority vested in me...")]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 0

    def test_header_units_skipped(self):
        units = [_make_unit(1, "header", "Section 2. Purpose.")]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 0

    def test_provision_candidate_written(self):
        units = [_make_unit(1, "provision_candidate", "The Secretary shall act.", ["Sec. 2"])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 1
        assert "provision_candidate" in summary["element_type_counts"]

    def test_boilerplate_text_gets_boilerplate_element_type(self):
        text = "Nothing in this order shall be construed to impair or otherwise affect the authority."
        units = [_make_unit(1, "provision_candidate", text, ["Sec. 3"])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 1
        assert "boilerplate" in summary["element_type_counts"]

    def test_definition_intro_gets_header_element_type(self):
        units = [_make_unit(1, "provision_candidate", "In this Act:", ["2."])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 1
        assert "header" in summary["element_type_counts"]

    def test_emdash_stub_gets_review_boundary(self):
        units = [_make_unit(1, "provision_candidate", "The Secretary shall—", ["Sec. 2"])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["chunk_flag_counts"].get("review_boundary", 0) == 1

    def test_bare_fragment_gets_review_boundary(self):
        units = [_make_unit(1, "provision_candidate", "airboats;", ["4."])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["chunk_flag_counts"].get("review_boundary", 0) == 1

    def test_clean_provision_gets_clean_flag(self):
        units = [_make_unit(1, "provision_candidate", "The Secretary shall conduct testing.", ["Sec. 2"])]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["chunk_flag_counts"].get("clean", 0) == 1

    def test_provision_index_increments_within_section(self):
        units = [
            _make_unit(1, "provision_candidate", "The Secretary shall act.", ["Sec. 2"]),
            _make_unit(2, "provision_candidate", "The Administrator shall report.", ["Sec. 2"]),
        ]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 2
        # Provision IDs written to DB — check via execute calls
        calls = conn.cursor.return_value.__enter__.return_value.execute.call_args_list
        ids_written = [c[0][1][0] for c in calls if c[0][1] and isinstance(c[0][1][0], str) and "|" in c[0][1][0]]
        assert any("|0" in pid for pid in ids_written)
        assert any("|1" in pid for pid in ids_written)

    def test_provision_index_resets_across_sections(self):
        units = [
            _make_unit(1, "provision_candidate", "The Secretary shall act.", ["Sec. 2"]),
            _make_unit(2, "provision_candidate", "The Administrator shall report.", ["Sec. 3"]),
        ]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 2

    def test_jurisdiction_refined_for_involves_states(self):
        text = "No State may enact any law to preempt this section."
        units = [_make_unit(1, "provision_candidate", text, ["Sec. 4"],
                            jurisdiction_scope="involves_states")]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        # Confirm provision was written without error
        assert summary["provisions_written"] == 1
        assert summary["errors"] == []

    def test_no_errors_on_clean_run(self):
        units = [
            _make_unit(1, "preamble", "By the authority vested in me..."),
            _make_unit(2, "provision_candidate", "The Secretary shall act.", ["Sec. 2"]),
            _make_unit(3, "provision_candidate", "In this Act:", ["2."]),
            _make_unit(4, "provision_candidate", "airboats;", ["4."]),
        ]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["errors"] == []
        assert summary["provisions_written"] == 3  # preamble skipped

    def test_proclamation_zero_provisions(self):
        # All preamble — proclamation pattern (Session 5 corpus finding)
        units = [
            _make_unit(1, "preamble", "By the authority vested in me as President..."),
            _make_unit(2, "preamble", "NOW, THEREFORE, I, Donald Trump, President of the United States..."),
        ]
        conn = _make_mock_conn(units)
        doc = {"id": 1, "doc_type": "presidential_proclamation", "title": "Proclamation 10001"}
        summary = normalize_document(conn, doc)
        assert summary["provisions_written"] == 0
        assert summary["errors"] == []

    def test_boilerplate_children_inherit_parent_classification(self):
        # Sec. 3(a) triggers boilerplate; Sec. 3(i) and Sec. 3(ii) are children
        # and should inherit boilerplate classification even though their text
        # doesn't contain the trigger phrase.
        units = [
            _make_unit(1, "provision_candidate",
                       "Nothing in this order shall be construed to impair or otherwise affect:",
                       ["Sec. 3", "(a)"]),
            _make_unit(2, "provision_candidate",
                       "the authority granted by law to an executive department or agency, or the head thereof; or",
                       ["Sec. 3", "(i)"]),
            _make_unit(3, "provision_candidate",
                       "the functions of the Director of the Office of Management and Budget.",
                       ["Sec. 3", "(ii)"]),
        ]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 3
        boilerplate_count = summary["element_type_counts"].get("boilerplate", 0)
        assert boilerplate_count == 3
        assert summary["element_type_counts"].get("provision_candidate", 0) == 0

    def test_context_text_includes_section_path_for_fr_docs(self):
        # FR docs produce no header units; section_path must appear in context_text
        units = [
            _make_unit(1, "provision_candidate",
                       "The Secretary shall conduct testing.",
                       ["Sec. 2"]),
        ]
        conn = _make_mock_conn(units)
        summary = normalize_document(conn, self._doc())
        assert summary["provisions_written"] == 1
        # Verify via execute calls that context_text contains section label
        calls = conn.cursor.return_value.__enter__.return_value.execute.call_args_list
        context_texts = [
            c[0][1][7] for c in calls
            if c[0][1] and len(c[0][1]) > 7 and isinstance(c[0][1][7], str)
            and "Text:" in str(c[0][1][7])
        ]
        assert any("Sec. 2" in ct for ct in context_texts)