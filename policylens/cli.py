import click
from policylens.db import get_pool
from policylens.sources import federal_register
from policylens.sources import congress as congress_src

@click.group()
def cli():
    """PolicyLens data pipeline."""

@cli.command()
@click.option("--pages", default=1, help="Number of pages to fetch")
def ingest_fr(pages: int):
    """Ingest presidential documents from the Federal Register."""
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
@click.option("--chamber", default="house", type=click.Choice(["house", "senate", "both"]), help="Chamber to ingest")
def ingest_congress(congress_num: int, limit: int, offset: int, chamber: str):
    """Ingest bills from Congress.gov."""
    pool = get_pool()
    inserted = 0
    errors = 0

    bill_types = []
    if chamber in ("house", "both"):
        bill_types += ["hr", "hjres", "hconres", "hres"]
    if chamber in ("senate", "both"):
        bill_types += ["s", "sjres", "sconres", "sres"]

    for bill_type in bill_types:
        bills = congress_src.fetch_bills_by_type(congress=congress_num, bill_type=bill_type, limit=limit, offset=offset)
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

if __name__ == "__main__":
    cli()