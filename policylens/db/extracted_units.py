"""
policylens/db/extracted_units.py

Persistence helpers for the extracted_units table and for advancing
document status through the pipeline.
"""

from __future__ import annotations

from policylens.chunker.types import ExtractedUnit


def upsert_extracted_units(conn, units: list[ExtractedUnit]) -> int:
    """
    Upsert a list of ExtractedUnit records into extracted_units.
    Uses ON CONFLICT (doc_id, source_element_id) DO NOTHING for idempotency.

    Returns the number of rows actually inserted (0 if all were conflicts).
    """
    if not units:
        return 0

    inserted = 0
    with conn.cursor() as cur:
        for unit in units:
            cur.execute(
                """
                INSERT INTO extracted_units
                    (doc_id, source_schema, source_element_id, element_type,
                     section_path, raw_text, legal_address_raw,
                     nesting_depth, extraction_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id, source_element_id) DO NOTHING
                """,
                (
                    unit.source_doc_id,
                    unit.source_schema,
                    unit.source_element_id,
                    unit.element_type,
                    unit.section_path,
                    unit.raw_text,
                    unit.legal_address_raw,
                    unit.nesting_depth,
                    unit.extraction_notes,
                ),
            )
            inserted += cur.rowcount
    return inserted


def advance_doc_status(conn, doc_id: int, new_status: str) -> None:
    """
    Update a document's status column.  Only advances forward (raw → extracted
    → transformed → classified).  Does not downgrade.
    """
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET status = %s WHERE id = %s",
            (new_status, doc_id),
        )


def fetch_docs_by_status(conn, status: str) -> list[dict]:
    """
    Return all documents with the given status as a list of dicts.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source, doc_type, raw_format, external_id,
                   title, date, url, raw_text
            FROM documents
            WHERE status = %s
            ORDER BY id
            """,
            (status,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_doc_by_id(conn, doc_id: int) -> dict | None:
    """Return a single document row as a dict, or None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source, doc_type, raw_format, external_id,
                   title, date, url, raw_text
            FROM documents
            WHERE id = %s
            """,
            (doc_id,),
        )
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None
