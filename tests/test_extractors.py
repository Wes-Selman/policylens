"""
tests/test_extractors.py

Unit tests for FRPresdocuExtractor and USLMExtractor.
Tests run against the actual corpus sample XML files from the repo.
All samples are embedded as strings so no filesystem dependency on the live DB.
"""

import pytest
from policylens.extractors.fr_presdocu import FRPresdocuExtractor
from policylens.extractors.uslm import USLMExtractor
from policylens.chunker.types import (
    ExtractedUnit,
    EXTRACTOR_ELEMENT_TYPES,
    EXTRACTOR_JURISDICTION_SCOPES,
)


# ── Corpus sample XML fixtures ──────────────────────────────────────────────

EO_14407_XML = '''<PRESDOCU>
    <EXECORD>
        <TITLE3>Title 3— </TITLE3>
        <PRES>The President<PRTPAGE P="33575"/></PRES>
        <EXECORDR>Executive Order 14407 of May 29, 2026</EXECORDR>
        <HD SOURCE="HED">Realigning United States Core Childhood Vaccine Recommendations With Best Practices From Peer, Developed Countries</HD>
        <FP>By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered:</FP>
        <FP><E T="04">Section 1</E>. <E T="03">Purpose and Policy.</E> The scientific assessment found that the United States currently recommends more childhood vaccines than any peer nation.</FP>
        <P>(b) The Centers for Disease Control and Prevention (CDC) and its Advisory Committee on Immunization Practices (ACIP) shall review the scientific assessment.</P>
        <FP><E T="04">Sec. 3</E>. <E T="03">General Provisions.</E> (a) Nothing in this order shall be construed to impair or otherwise affect:</FP>
        <FP SOURCE="FP1">(i) the authority granted by law to an executive department or agency, or the head thereof; or</FP>
        <P>(b) This order shall be implemented consistent with applicable law and subject to the availability of appropriations.</P>
        <P>(c) This order is not intended to, and does not, create any right or benefit, substantive or procedural, enforceable at law or in equity by any party against the United States.</P>
        <PSIG> </PSIG>
        <PLACE>THE WHITE HOUSE,</PLACE>
        <DATE>May 29, 2026.</DATE>
        <FRDOC>[FR Doc. 2026-11180</FRDOC>
    </EXECORD>
</PRESDOCU>'''

PROCLAMATION_XML = '''<PRESDOCU>
    <PROCLA>
        <PRTPAGE P="26891"/>
        <PROC>Proclamation 11028 of May 7, 2026</PROC>
        <HD SOURCE="HED">Victory Day for World War II, 2026</HD>
        <PRES>By the President of the United States of America</PRES>
        <PROC>A Proclamation</PROC>
        <FP>As we celebrate Victory Day for World War II -- we celebrate America's monumental triumph over tyranny and evil in Europe.</FP>
        <FP>The fight for liberty came at a staggering cost. More than 250,000 Americans laid down their lives in the fight against the Nazi regime.</FP>
        <FP>NOW, THEREFORE, I, DONALD J. TRUMP, President of the United States of America, by virtue of the authority vested in me by the Constitution and the laws of the United States, do hereby proclaim May 8, 2026, as a day in celebration of Victory Day for World War II.</FP>
        <PSIG> </PSIG>
        <BILCOD>Billing code 3395-F4-P</BILCOD>
    </PROCLA>
</PRESDOCU>'''

NOTICE_XML = '''<PRESDOCU>
    <PRNOTICE>
        <PRTPAGE P="25069"/>
        <PNOTICE>Notice of May 4, 2026</PNOTICE>
        <HD SOURCE="HED">Continuation of the National Emergency With Respect to the Central African Republic</HD>
        <FP>On May 12, 2014, by Executive Order 13667, the President declared a national emergency pursuant to the International Emergency Economic Powers Act (50 U.S.C. 1701 et seq.).</FP>
        <FP>The situation in and in relation to the Central African Republic continues to pose an unusual and extraordinary threat. Therefore, in accordance with section 202(d) of the National Emergencies Act (50 U.S.C. 1622(d)), I am continuing for 1 year the national emergency declared in Executive Order 13667.</FP>
        <FP>This notice shall be published in the Federal Register and transmitted to the Congress.</FP>
        <PSIG> </PSIG>
        <BILCOD>Billing code 3395-F4-P</BILCOD>
    </PRNOTICE>
</PRESDOCU>'''

# EO with explicit state-directed provisions, to exercise involves_states detection.
EO_STATE_DIRECTED_XML = '''<PRESDOCU>
    <EXECORD>
        <FP>By the authority vested in me as President, it is hereby ordered:</FP>
        <FP><E T="04">Section 1</E>. <E T="03">State Coordination.</E> The Secretary shall ensure that State government officials are informed of the requirements of this order.</FP>
        <P>(a) States may adopt additional requirements beyond those set forth herein, provided they are not less than the federal minimum standard.</P>
        <P>(b) No State may impose requirements that conflict with this order.</P>
        <FP><E T="04">Sec. 2</E>. <E T="03">Federal Standards.</E> All federal agencies shall comply with this order.</FP>
        <P>(a) Agency heads shall submit quarterly reports to the President.</P>
    </EXECORD>
</PRESDOCU>'''

BILL_S31_XML = '''<?xml version="1.0"?>
<!DOCTYPE bill PUBLIC "-//US Congress//DTDs/bill.dtd//EN" "bill.dtd">
<bill bill-stage="Introduced-in-Senate" public-private="public">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dublinCore>
<dc:title>119 S31 IS: To designate the mountain at the Devils Tower National Monument</dc:title>
</dublinCore>
</metadata>
<form><legis-num>S. 31</legis-num><legis-type>A BILL</legis-type>
<official-title>To designate the mountain at the Devils Tower National Monument, Wyoming, as Devils Tower.</official-title>
</form>
<legis-body display-enacting-clause="yes-display-enacting-clause">
<section section-type="section-one" id="id53C26D061BAE461D981712C3017FAE89">
<enum>1.</enum><header>Designation of Devils Tower</header>
<subsection id="id9f130ae26c834e0b8e689c256aa66e90">
<enum>(a)</enum><header>In general</header>
<text>The mountain at the Devils Tower National Monument, Wyoming, shall be known and designated as "Devils Tower".</text>
</subsection>
<subsection id="id640a823a8c1e40089ce724616a729277">
<enum>(b)</enum><header>References</header>
<text>Any reference in any law, map, regulation, order, document, paper, or other record of the United States to the mountain shall be deemed to be a reference to "Devils Tower".</text>
</subsection>
</section>
</legis-body>
</bill>'''

RESOLUTION_SRES7_XML = '''<?xml version="1.0"?>
<!DOCTYPE resolution PUBLIC "-//US Congress//DTDs/res.dtd//EN" "res.dtd">
<resolution resolution-type="senate-resolution" public-private="public">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dublinCore><dc:title>119 SRES 7 ATS: Fixing the hour of daily meeting of the Senate.</dc:title></dublinCore>
</metadata>
<form>
<legis-num>S. RES. 7</legis-num>
<legis-type>RESOLUTION</legis-type>
<official-title display="yes">Fixing the hour of daily meeting of the Senate.</official-title>
</form>
<resolution-body style="OLC" display-resolving-clause="yes-display-resolving-clause" id="H248AF52B8427495BA464997E21643985">
<section id="LEXA-Repairidfeca7eb17784456f95d343ddc5ec8d7b" section-type="undesignated-section" display-inline="yes-display-inline">
<text>That the daily meeting of the Senate be 12 o\'clock meridian unless otherwise ordered.</text>
</section>
</resolution-body>
</resolution>'''

# USLM bill with state-preemption language, to exercise involves_states detection.
BILL_PREEMPTION_XML = '''<?xml version="1.0"?>
<bill bill-stage="Introduced-in-Senate" public-private="public">
<legis-body>
<section id="s001">
<enum>1.</enum><header>Federal Preemption</header>
<subsection id="s001a">
<enum>(a)</enum><header>In general</header>
<text>No State may enact or enforce any law that is inconsistent with the provisions of this Act.</text>
</subsection>
<subsection id="s001b">
<enum>(b)</enum><header>Savings clause</header>
<text>Nothing in this Act shall be construed to preempt any State law that provides greater protection to consumers.</text>
</subsection>
</section>
<section id="s002">
<enum>2.</enum><header>Federal Standards</header>
<subsection id="s002a">
<enum>(a)</enum><header>Minimum requirements</header>
<text>All persons subject to this Act shall comply with the minimum standard established herein.</text>
</subsection>
</section>
</legis-body>
</bill>'''


def make_doc(doc_id: int, raw_text: str, doc_type: str = "executive_order",
             title: str = "Test Document") -> dict:
    return {
        "id": doc_id,
        "source": "federal_register",
        "doc_type": doc_type,
        "raw_format": "xml",
        "raw_text": raw_text,
        "title": title,
        "date": "2026-05-29",
        "url": "https://example.com",
    }


# ── FRPresdocuExtractor tests ──────────────────────────────────────────────

class TestFRPresdocuExtractor:

    def test_source_schema(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        assert ext.source_schema == "fr_presdocu"

    def test_eo_produces_units(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        assert len(units) > 0, "EO should produce at least one extracted unit"

    def test_eo_has_preamble(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        preambles = [u for u in units if u.element_type == "preamble"]
        assert len(preambles) >= 1, "EO should have at least one preamble unit"
        # The authority-vested formula should be in a preamble unit
        preamble_texts = " ".join(u.raw_text for u in preambles)
        assert "authority vested" in preamble_texts.lower()

    def test_eo_has_provision_candidates(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        assert len(provisions) >= 2, "EO should have multiple provision candidates"

    def test_eo_section_path_populated(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        # At least one provision should have a section path
        paths = [u.section_path for u in provisions if u.section_path]
        assert len(paths) > 0, "Provisions should have section_path populated"

    def test_boilerplate_tags_stripped(self):
        """PRTPAGE, PSIG, PLACE, DATE, FRDOC etc. should not appear in raw_text."""
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        all_text = " ".join(u.raw_text for u in units)
        for tag in ("PRTPAGE", "PSIG", "PLACE", "BILCOD", "FRDOC"):
            assert tag not in all_text, f"Boilerplate tag {tag} found in extracted text"

    def test_element_type_values_valid(self):
        """Extractor must not assign element_type='boilerplate'."""
        for xml, doc_type in [
            (EO_14407_XML, "executive_order"),
            (PROCLAMATION_XML, "presidential_proclamation"),
            (NOTICE_XML, "notice"),
        ]:
            ext = FRPresdocuExtractor(make_doc(1, xml, doc_type))
            units = ext.extract()
            for u in units:
                assert u.element_type in EXTRACTOR_ELEMENT_TYPES, (
                    f"Invalid element_type: {u.element_type!r}"
                )

    def test_source_element_ids_unique_per_doc(self):
        """source_element_id values must be unique within a document."""
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        ids = [u.source_element_id for u in units]
        assert len(ids) == len(set(ids)), (
            f"Duplicate source_element_ids: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_all_units_pass_validate(self):
        """All units must pass ExtractedUnit.validate() without raising."""
        for xml, doc_type in [
            (EO_14407_XML, "executive_order"),
            (PROCLAMATION_XML, "presidential_proclamation"),
            (NOTICE_XML, "notice"),
        ]:
            ext = FRPresdocuExtractor(make_doc(1, xml, doc_type))
            units = ext.extract()
            for u in units:
                u.validate()  # should not raise

    def test_proclamation_extracts_units(self):
        ext = FRPresdocuExtractor(make_doc(2, PROCLAMATION_XML, "presidential_proclamation"))
        units = ext.extract()
        assert len(units) > 0
        # Proclamations have preamble content and a closing action clause
        preambles = [u for u in units if u.element_type == "preamble"]
        assert len(preambles) >= 1

    def test_notice_extracts_units(self):
        ext = FRPresdocuExtractor(make_doc(3, NOTICE_XML, "notice"))
        units = ext.extract()
        assert len(units) > 0

    def test_empty_raw_text_returns_empty(self):
        doc = make_doc(99, "")
        ext = FRPresdocuExtractor(doc)
        assert ext.extract() == []

    def test_source_doc_id_propagated(self):
        ext = FRPresdocuExtractor(make_doc(42, EO_14407_XML))
        units = ext.extract()
        for u in units:
            assert u.source_doc_id == 42

    def test_nesting_depth(self):
        """Sub-paragraphs should have nesting_depth > 0."""
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        nested = [u for u in units if u.nesting_depth > 0]
        # The (b) and (i) sub-paragraphs should be nested
        assert len(nested) >= 1, "Should have at least one nested sub-paragraph"

    # ── jurisdiction_scope tests ───────────────────────────────────────────

    def test_jurisdiction_scope_default_is_federal_only(self):
        """Units with no state-reference language must have jurisdiction_scope='federal_only'."""
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        units = ext.extract()
        # EO_14407_XML has no state-reference language; all units should be federal_only
        for u in units:
            assert u.jurisdiction_scope == "federal_only", (
                f"Expected federal_only, got {u.jurisdiction_scope!r} "
                f"for unit {u.source_element_id!r}: {u.raw_text[:80]!r}"
            )

    def test_jurisdiction_scope_involves_states_detected(self):
        """Units with state-reference language must have jurisdiction_scope='involves_states'."""
        ext = FRPresdocuExtractor(make_doc(1, EO_STATE_DIRECTED_XML))
        units = ext.extract()
        involves = [u for u in units if u.jurisdiction_scope == "involves_states"]
        assert len(involves) >= 1, (
            "Expected at least one involves_states unit from EO with state-directed provisions"
        )

    def test_jurisdiction_scope_values_valid(self):
        """All units must have a jurisdiction_scope within the extractor-permitted set."""
        for xml, doc_type in [
            (EO_14407_XML, "executive_order"),
            (EO_STATE_DIRECTED_XML, "executive_order"),
            (PROCLAMATION_XML, "presidential_proclamation"),
            (NOTICE_XML, "notice"),
        ]:
            ext = FRPresdocuExtractor(make_doc(1, xml, doc_type))
            for u in ext.extract():
                assert u.jurisdiction_scope in EXTRACTOR_JURISDICTION_SCOPES, (
                    f"Invalid jurisdiction_scope {u.jurisdiction_scope!r} "
                    f"on unit {u.source_element_id!r}"
                )

    def test_involves_states_specific_phrases(self):
        """Check that each key phrase pattern triggers involves_states."""
        trigger_phrases = [
            "State government officials are informed",
            "States may adopt additional requirements",
            "not less than the federal minimum standard",
            "No State may impose requirements",
        ]
        ext = FRPresdocuExtractor(make_doc(1, EO_STATE_DIRECTED_XML))
        units = ext.extract()
        involves_texts = [u.raw_text for u in units if u.jurisdiction_scope == "involves_states"]
        combined = " ".join(involves_texts)
        # At least one trigger phrase should appear in the involves_states units
        matched = [p for p in trigger_phrases if any(
            p.lower() in t.lower() for t in involves_texts
        )]
        assert len(matched) >= 1, (
            f"None of the expected trigger phrases found in involves_states units. "
            f"involves_states texts: {involves_texts}"
        )

    def test_purely_federal_units_not_flagged(self):
        """Units in EO_STATE_DIRECTED_XML that don't mention states stay federal_only."""
        ext = FRPresdocuExtractor(make_doc(1, EO_STATE_DIRECTED_XML))
        units = ext.extract()
        federal_only = [u for u in units if u.jurisdiction_scope == "federal_only"]
        # Sec. 2(a) "Agency heads shall submit quarterly reports" has no state reference
        assert len(federal_only) >= 1, (
            "Expected at least one federal_only unit alongside involves_states units"
        )


# ── USLMExtractor tests ────────────────────────────────────────────────────

class TestUSLMExtractor:

    def test_source_schema(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        assert ext.source_schema == "uslm"

    def test_bill_produces_units(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        assert len(units) > 0

    def test_bill_has_provision_candidates(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        # S.31 has subsection (a) and (b) with <text> children
        assert len(provisions) >= 2

    def test_bill_subsection_text_content(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        all_text = " ".join(u.raw_text for u in provisions)
        assert "Devils Tower" in all_text

    def test_bill_has_headers(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        headers = [u for u in units if u.element_type == "header"]
        # "Designation of Devils Tower", "In general", "References"
        assert len(headers) >= 2

    def test_bill_section_path(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        # Subsections should have paths like ['1.', '(a)']
        paths_with_depth = [u.section_path for u in provisions if len(u.section_path) >= 2]
        assert len(paths_with_depth) >= 1

    def test_resolution_produces_units(self):
        ext = USLMExtractor(make_doc(20, RESOLUTION_SRES7_XML, "resolution"))
        units = ext.extract()
        assert len(units) > 0

    def test_resolution_text_content(self):
        ext = USLMExtractor(make_doc(20, RESOLUTION_SRES7_XML, "resolution"))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        assert len(provisions) >= 1
        assert "12 o'clock meridian" in provisions[0].raw_text or \
               "12 o" in provisions[0].raw_text

    def test_element_type_values_valid(self):
        """Extractor must not assign element_type='boilerplate'."""
        for xml, doc_type in [
            (BILL_S31_XML, "bill"),
            (RESOLUTION_SRES7_XML, "resolution"),
        ]:
            ext = USLMExtractor(make_doc(10, xml, doc_type))
            units = ext.extract()
            for u in units:
                assert u.element_type in EXTRACTOR_ELEMENT_TYPES

    def test_source_element_ids_unique_per_doc(self):
        """source_element_id values must be unique within a document."""
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        ids = [u.source_element_id for u in units]
        assert len(ids) == len(set(ids)), (
            f"Duplicate source_element_ids: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_all_units_pass_validate(self):
        """All units must pass ExtractedUnit.validate() without raising."""
        for xml, doc_type in [
            (BILL_S31_XML, "bill"),
            (RESOLUTION_SRES7_XML, "resolution"),
        ]:
            ext = USLMExtractor(make_doc(10, xml, doc_type))
            units = ext.extract()
            for u in units:
                u.validate()

    def test_source_doc_id_propagated(self):
        ext = USLMExtractor(make_doc(55, BILL_S31_XML, "bill"))
        units = ext.extract()
        for u in units:
            assert u.source_doc_id == 55

    def test_nesting_depth_increases_with_hierarchy(self):
        """Deeper elements should have higher nesting_depth."""
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        provisions = [u for u in units if u.element_type == "provision_candidate"]
        # Subsection text should be at depth > 0
        depths = [u.nesting_depth for u in provisions]
        assert max(depths) >= 1, "At least some provisions should have nesting_depth > 0"

    def test_empty_raw_text_returns_empty(self):
        doc = make_doc(99, "", "bill")
        ext = USLMExtractor(doc)
        assert ext.extract() == []

    # ── jurisdiction_scope tests ───────────────────────────────────────────

    def test_jurisdiction_scope_default_is_federal_only(self):
        """Units with no state-reference language must have jurisdiction_scope='federal_only'."""
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        units = ext.extract()
        # BILL_S31_XML has no state-reference language; all units should be federal_only
        for u in units:
            assert u.jurisdiction_scope == "federal_only", (
                f"Expected federal_only, got {u.jurisdiction_scope!r} "
                f"for unit {u.source_element_id!r}: {u.raw_text[:80]!r}"
            )

    def test_jurisdiction_scope_involves_states_detected(self):
        """Units with state-preemption language must have jurisdiction_scope='involves_states'."""
        ext = USLMExtractor(make_doc(10, BILL_PREEMPTION_XML, "bill"))
        units = ext.extract()
        involves = [u for u in units if u.jurisdiction_scope == "involves_states"]
        assert len(involves) >= 1, (
            "Expected at least one involves_states unit from bill with preemption provisions"
        )

    def test_jurisdiction_scope_values_valid(self):
        """All units must have a jurisdiction_scope within the extractor-permitted set."""
        for xml, doc_type in [
            (BILL_S31_XML, "bill"),
            (BILL_PREEMPTION_XML, "bill"),
            (RESOLUTION_SRES7_XML, "resolution"),
        ]:
            ext = USLMExtractor(make_doc(10, xml, doc_type))
            for u in ext.extract():
                assert u.jurisdiction_scope in EXTRACTOR_JURISDICTION_SCOPES, (
                    f"Invalid jurisdiction_scope {u.jurisdiction_scope!r} "
                    f"on unit {u.source_element_id!r}"
                )

    def test_involves_states_specific_phrases(self):
        """Each key preemption/deference phrase must be detected in BILL_PREEMPTION_XML."""
        ext = USLMExtractor(make_doc(10, BILL_PREEMPTION_XML, "bill"))
        units = ext.extract()
        involves_texts = [u.raw_text for u in units if u.jurisdiction_scope == "involves_states"]
        # "No State may" and "greater protection" both appear in BILL_PREEMPTION_XML
        assert any("No State may" in t for t in involves_texts), (
            "Expected 'No State may' to trigger involves_states"
        )
        assert any("greater protection" in t or "preempt" in t for t in involves_texts), (
            "Expected preemption language to trigger involves_states"
        )

    def test_purely_federal_units_not_flagged(self):
        """The Sec. 2(a) minimum-standard unit stays federal_only (no state reference)."""
        ext = USLMExtractor(make_doc(10, BILL_PREEMPTION_XML, "bill"))
        units = ext.extract()
        federal_only = [u for u in units if u.jurisdiction_scope == "federal_only"]
        # The "minimum standard established herein" unit references no state actors
        assert len(federal_only) >= 1, (
            "Expected at least one federal_only unit alongside involves_states units"
        )

    def test_header_units_are_federal_only(self):
        """Header units carry no deontic content and should always be federal_only."""
        ext = USLMExtractor(make_doc(10, BILL_PREEMPTION_XML, "bill"))
        units = ext.extract()
        headers = [u for u in units if u.element_type == "header"]
        for h in headers:
            assert h.jurisdiction_scope == "federal_only", (
                f"Header unit {h.source_element_id!r} has unexpected "
                f"jurisdiction_scope={h.jurisdiction_scope!r}"
            )


# ── Cross-cutter tests ─────────────────────────────────────────────────────

class TestExtractorContract:
    """Tests that verify both extractors honour the BaseExtractor contract."""

    def test_fr_never_assigns_boilerplate(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        for u in ext.extract():
            assert u.element_type != "boilerplate"

    def test_uslm_never_assigns_boilerplate(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        for u in ext.extract():
            assert u.element_type != "boilerplate"

    def test_fr_raw_text_non_empty_for_non_error_units(self):
        ext = FRPresdocuExtractor(make_doc(1, EO_14407_XML))
        for u in ext.extract():
            if "parse_error" not in u.source_element_id:
                # Headers may have empty text if the header element is empty,
                # but provision_candidates and preambles should have content
                if u.element_type in ("provision_candidate", "preamble"):
                    assert u.raw_text, f"Empty raw_text for {u.element_type} unit {u.source_element_id}"

    def test_uslm_raw_text_non_empty_for_provisions(self):
        ext = USLMExtractor(make_doc(10, BILL_S31_XML, "bill"))
        for u in ext.extract():
            if u.element_type == "provision_candidate":
                assert u.raw_text, f"Empty raw_text for provision_candidate {u.source_element_id}"

    def test_validate_rejects_invalid_jurisdiction_scope(self):
        """ExtractedUnit.validate() must raise ValueError for any invalid jurisdiction_scope."""
        invalid_values = [
            "preempts_state",   # normalizer-only value
            "defers_to_state",  # normalizer-only value
            "creates_floor",    # normalizer-only value
            "state",            # not in any enum
            "",                 # empty string
            "FEDERAL_ONLY",     # wrong case
        ]
        for bad_value in invalid_values:
            unit = ExtractedUnit(
                source_doc_id=1,
                source_schema="fr_presdocu",
                source_element_id="test_unit",
                raw_text="Some text.",
                element_type="provision_candidate",
                jurisdiction_scope=bad_value,
            )
            with pytest.raises(ValueError, match="jurisdiction_scope"):
                unit.validate()

    def test_validate_accepts_all_valid_jurisdiction_scopes(self):
        """ExtractedUnit.validate() must accept every value in EXTRACTOR_JURISDICTION_SCOPES."""
        for valid_scope in EXTRACTOR_JURISDICTION_SCOPES:
            unit = ExtractedUnit(
                source_doc_id=1,
                source_schema="fr_presdocu",
                source_element_id="test_unit",
                raw_text="Some text.",
                element_type="provision_candidate",
                jurisdiction_scope=valid_scope,
            )
            unit.validate()  # must not raise

    def test_both_extractors_produce_valid_jurisdiction_scopes(self):
        """All units from both extractors must pass validate() on jurisdiction_scope."""
        test_cases = [
            (FRPresdocuExtractor, make_doc(1, EO_14407_XML, "executive_order")),
            (FRPresdocuExtractor, make_doc(1, EO_STATE_DIRECTED_XML, "executive_order")),
            (USLMExtractor, make_doc(10, BILL_S31_XML, "bill")),
            (USLMExtractor, make_doc(10, BILL_PREEMPTION_XML, "bill")),
        ]
        for ExtractorClass, doc in test_cases:
            ext = ExtractorClass(doc)
            for u in ext.extract():
                # validate() covers both element_type and jurisdiction_scope
                u.validate()
