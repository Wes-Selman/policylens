import click
from policylens.db import get_pool
from policylens.db.extracted_units import (
    upsert_extracted_units,
    advance_doc_status,
    fetch_docs_by_status,
    fetch_doc_by_id,
)
from policylens.extractors.registry import get_extractor


# ── CLI group ──────────────────────────────────────────────────────────────

@click.group()
def cli():
    """PolicyLens data pipeline."""


# ── Ingestion commands ─────────────────────────────────────────────────────

@cli.command()
@click.option("--pages", default=1, help="Number of pages to fetch")
def ingest_fr(pages: int):
    """Ingest presidential documents from the Federal Register."""
    from policylens.sources import federal_register  # lazy: only needed at runtime
    pool = get_pool()
    inserted = 0
    errors = 0

    for page in range(1, pages + 1):
        docs = federal_register.fetch_documents(doc_type="PRESDOCU", page=page)
        click.echo(f"Page {page}: {len(docs)} documents fetched")

        for doc in docs:
            raw_text = None
            error_msg = None
            status = "raw"

            try:
                raw_text = federal_register.fetch_full_text(doc.get("full_text_xml_url"))
            except Exception as e:
                error_msg = str(e)
                status = "error"
                errors += 1

            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents
                            (source, doc_type, raw_format, status, external_id, title, date, url, raw_text, error_msg)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (external_id) DO NOTHING
                    """, (
                        "federal_register",
                        federal_register.map_doc_type(doc.get("subtype", "")),
                        "xml",
                        status,
                        doc["document_number"],
                        doc.get("title"),
                        doc.get("publication_date"),
                        doc.get("html_url"),
                        raw_text,
                        error_msg,
                    ))
                    inserted += cur.rowcount

    click.echo(f"Done. {inserted} new documents inserted, {errors} errors.")


@cli.command()
@click.option("--congress", "congress_num", default=119, help="Congress number")
@click.option("--limit", default=20, help="Number of bills to fetch")
@click.option("--offset", default=0, help="Pagination offset")
@click.option("--chamber", default="house",
              type=click.Choice(["house", "senate", "both"]),
              help="Chamber to ingest")
def ingest_congress(congress_num: int, limit: int, offset: int, chamber: str):
    """Ingest bills from Congress.gov."""
    from policylens.sources import congress as congress_src  # lazy: only needed at runtime
    pool = get_pool()
    inserted = 0
    errors = 0

    bill_types = []
    if chamber in ("house", "both"):
        bill_types += ["hr", "hjres", "hconres", "hres"]
    if chamber in ("senate", "both"):
        bill_types += ["s", "sjres", "sconres", "sres"]

    for bill_type in bill_types:
        bills = congress_src.fetch_bills_by_type(
            congress=congress_num, bill_type=bill_type,
            limit=limit, offset=offset,
        )
        click.echo(f"{bill_type.upper()}: {len(bills)} bills fetched")

        for bill in bills:
            actual_type = bill.get("type", "")
            bill_number = bill.get("number")
            raw_text = None
            raw_format = "text"
            error_msg = None
            status = "raw"

            try:
                raw_text, raw_format = congress_src.fetch_bill_text(
                    congress=congress_num,
                    bill_type=actual_type,
                    bill_number=bill_number,
                )
            except Exception as e:
                error_msg = str(e)
                status = "error"
                errors += 1

            external_id = f"{congress_num}-{actual_type}-{bill_number}"

            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents
                            (source, doc_type, raw_format, status, external_id, title, date, url, raw_text, error_msg)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (external_id) DO NOTHING
                    """, (
                        "congress",
                        congress_src.map_doc_type(actual_type),
                        raw_format,
                        status,
                        external_id,
                        bill.get("title"),
                        bill.get("updateDate", "")[:10] or None,
                        bill.get("url"),
                        raw_text,
                        error_msg,
                    ))
                    inserted += cur.rowcount

    click.echo(f"Done. {inserted} new documents inserted, {errors} errors.")


# ── Extraction command ─────────────────────────────────────────────────────

@cli.command("chunk-extract")
@click.option("--doc-id", "doc_id", default=None, type=int,
              help="Process a single document by id (for testing/debugging).")
def chunk_extract(doc_id):
    """
    Layer 2a: Extract raw documents into structured units.

    Queries documents with status='raw' (or the specified --doc-id),
    dispatches to the appropriate source extractor, writes to extracted_units,
    and advances document status to 'extracted'.

    Idempotent: re-running on an already-extracted document is a no-op
    (ON CONFLICT DO NOTHING on extracted_units; status only advances forward).
    """
    pool = get_pool()

    total_docs = 0
    total_units = 0
    total_errors = 0

    with pool.connection() as conn:
        # Fetch target documents
        if doc_id is not None:
            doc = fetch_doc_by_id(conn, doc_id)
            if doc is None:
                click.echo(f"Error: document id={doc_id} not found.", err=True)
                return
            docs = [doc]
        else:
            docs = fetch_docs_by_status(conn, "raw")

        if not docs:
            click.echo("No documents with status='raw' found. Nothing to do.")
            return

        click.echo(f"Processing {len(docs)} document(s)...")
        click.echo("")

        for doc in docs:
            doc_id_val = doc["id"]
            doc_type = doc.get("doc_type", "unknown")
            external_id = doc.get("external_id", "")

            try:
                extractor = get_extractor(doc)
                units = extractor.extract()
            except Exception as exc:
                click.echo(
                    f"  [{doc_id_val:>4}] {doc_type:<30} {external_id:<30} "
                    f"ERROR: {exc}",
                    err=True,
                )
                total_errors += 1
                continue

            # Count by element_type for the per-doc summary
            type_counts: dict[str, int] = {}
            for u in units:
                type_counts[u.element_type] = type_counts.get(u.element_type, 0) + 1

            # Persist
            try:
                inserted = upsert_extracted_units(conn, units)
                advance_doc_status(conn, doc_id_val, "extracted")
                conn.commit()
            except Exception as exc:
                conn.rollback()
                click.echo(
                    f"  [{doc_id_val:>4}] {doc_type:<30} {external_id:<30} "
                    f"DB ERROR: {exc}",
                    err=True,
                )
                total_errors += 1
                continue

            total_docs += 1
            total_units += len(units)

            type_summary = "  ".join(
                f"{k}={v}" for k, v in sorted(type_counts.items())
            )
            click.echo(
                f"  [{doc_id_val:>4}] {doc_type:<30} {external_id:<30} "
                f"units={len(units):>4}  ({type_summary})  "
                f"new_rows={inserted}"
            )

    click.echo("")
    click.echo(
        f"Done. {total_docs} documents processed, "
        f"{total_units} extracted_units written, "
        f"{total_errors} errors."
    )


if __name__ == "__main__":
    cli()
