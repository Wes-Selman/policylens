"""
tests/test_cli_dispatch.py

Tests for the extractor dispatch logic in cli.py.
Also tests the persistence helper functions with a mock connection.
No live database required.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from policylens.chunker.types import ExtractedUnit
from policylens.db.extracted_units import upsert_extracted_units, advance_doc_status


# ── Extractor dispatch tests ───────────────────────────────────────────────

class TestExtractorDispatch:
    """Tests that get_extractor routes to the correct class."""

    def _dispatch(self, doc: dict):
        from policylens.extractors.registry import get_extractor
        return get_extractor(doc)

    def test_federal_register_dispatches_to_fr_extractor(self):
        from policylens.extractors.fr_presdocu import FRPresdocuExtractor
        doc = {"id": 1, "source": "federal_register", "doc_type": "executive_order",
               "raw_text": "", "title": "T", "date": None, "url": None, "raw_format": "xml"}
        extractor = self._dispatch(doc)
        assert isinstance(extractor, FRPresdocuExtractor)

    def test_congress_dispatches_to_uslm_extractor(self):
        from policylens.extractors.uslm import USLMExtractor
        doc = {"id": 2, "source": "congress", "doc_type": "bill",
               "raw_text": "", "title": "T", "date": None, "url": None, "raw_format": "xml"}
        extractor = self._dispatch(doc)
        assert isinstance(extractor, USLMExtractor)

    def test_unknown_source_raises(self):
        from policylens.extractors.registry import get_extractor
        doc = {"id": 3, "source": "unknown_source", "doc_type": "bill",
               "raw_text": "", "title": "T", "date": None, "url": None, "raw_format": "xml"}
        with pytest.raises(ValueError, match="No extractor registered"):
            get_extractor(doc)


# ── Persistence helper tests ───────────────────────────────────────────────

class TestUpsertExtractedUnits:
    """Tests for upsert_extracted_units using a mock connection."""

    def _make_unit(self, doc_id=1, eid="sec1:0", element_type="provision_candidate"):
        return ExtractedUnit(
            source_doc_id=doc_id,
            source_schema="fr_presdocu",
            source_element_id=eid,
            raw_text="The Secretary shall comply.",
            element_type=element_type,
            section_path=["Sec. 1"],
            nesting_depth=0,
        )

    def test_empty_list_returns_zero(self):
        conn = MagicMock()
        result = upsert_extracted_units(conn, [])
        assert result == 0
        conn.cursor.assert_not_called()

    def test_single_unit_executes_insert(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.rowcount = 1
        conn.cursor.return_value = cur

        unit = self._make_unit()
        result = upsert_extracted_units(conn, [unit])

        assert result == 1
        assert cur.execute.called
        # Verify the SQL contains the expected table name
        sql = cur.execute.call_args[0][0]
        assert "extracted_units" in sql
        assert "ON CONFLICT" in sql

    def test_multiple_units_all_inserted(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.rowcount = 1
        conn.cursor.return_value = cur

        units = [self._make_unit(eid=f"sec{i}:0") for i in range(5)]
        result = upsert_extracted_units(conn, units)

        assert result == 5
        assert cur.execute.call_count == 5

    def test_conflict_returns_zero_for_that_row(self):
        """If ON CONFLICT DO NOTHING fires, rowcount = 0 for that row."""
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.rowcount = 0  # conflict
        conn.cursor.return_value = cur

        unit = self._make_unit()
        result = upsert_extracted_units(conn, [unit])
        assert result == 0

    def test_correct_fields_passed_to_execute(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.rowcount = 1
        conn.cursor.return_value = cur

        unit = ExtractedUnit(
            source_doc_id=42,
            source_schema="uslm",
            source_element_id="sec1_a",
            raw_text="Provision text.",
            element_type="provision_candidate",
            section_path=["1.", "(a)"],
            legal_address_raw="26 U.S.C. § 7701",
            nesting_depth=1,
            extraction_notes=["note1"],
        )
        upsert_extracted_units(conn, [unit])

        args = cur.execute.call_args[0][1]  # positional params tuple
        assert args[0] == 42          # doc_id
        assert args[1] == "uslm"      # source_schema
        assert args[2] == "sec1_a"    # source_element_id
        assert args[3] == "provision_candidate"  # element_type
        assert args[4] == ["1.", "(a)"]  # section_path
        assert args[5] == "Provision text."  # raw_text
        assert args[6] == "26 U.S.C. § 7701"  # legal_address_raw
        assert args[7] == 1           # nesting_depth
        assert args[8] == ["note1"]   # extraction_notes


class TestAdvanceDocStatus:

    def test_execute_called_with_correct_params(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur

        advance_doc_status(conn, doc_id=7, new_status="extracted")

        cur.execute.assert_called_once()
        sql, params = cur.execute.call_args[0]
        assert "UPDATE documents" in sql
        assert params == ("extracted", 7)
