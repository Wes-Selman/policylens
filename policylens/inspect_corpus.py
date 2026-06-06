#!/usr/bin/env python3
"""
inspect_corpus.py — Pull representative raw documents from the DB and dump
them to ./corpus_samples/ for inspection before writing the chunker.

Run from the repo root:
    python inspect_corpus.py

Requires POSTGRES_DSN in .env (same as the rest of the project).
"""

import os
import json
import pathlib
from dotenv import load_dotenv
import psycopg

load_dotenv()

DSN = os.environ["POSTGRES_DSN"]
OUT = pathlib.Path("corpus_samples")
OUT.mkdir(exist_ok=True)


def run():
    with psycopg.connect(DSN) as conn:

        # ── 1. Corpus overview ───────────────────────────────────────────────
        print("\n=== CORPUS OVERVIEW ===\n")
        rows = conn.execute("""
            SELECT
                source,
                doc_type,
                raw_format,
                COUNT(*)                                         AS total,
                COUNT(*) FILTER (WHERE raw_text IS NULL)        AS null_text,
                COUNT(*) FILTER (WHERE status = 'error')        AS errors,
                ROUND(AVG(length(raw_text)))::int               AS avg_chars,
                MIN(length(raw_text))                           AS min_chars,
                MAX(length(raw_text))                           AS max_chars
            FROM documents
            GROUP BY source, doc_type, raw_format
            ORDER BY source, doc_type
        """).fetchall()

        col_headers = [
            "source", "doc_type", "raw_format",
            "total", "null_text", "errors",
            "avg_chars", "min_chars", "max_chars"
        ]
        # Print as aligned table
        col_w = [max(len(h), max((len(str(r[i])) for r in rows), default=0))
                 for i, h in enumerate(col_headers)]
        header = "  ".join(h.ljust(col_w[i]) for i, h in enumerate(col_headers))
        print(header)
        print("-" * len(header))
        for row in rows:
            print("  ".join(str(v).ljust(col_w[i]) for i, v in enumerate(row)))

        # Save as JSON too
        overview = [dict(zip(col_headers, row)) for row in rows]
        (OUT / "00_corpus_overview.json").write_text(
            json.dumps(overview, indent=2, default=str)
        )
        print(f"\n  → saved corpus_samples/00_corpus_overview.json")

        # ── 2. Sample one document per (doc_type × raw_format) combination ──
        print("\n=== PULLING SAMPLES ===\n")

        # Pull the shortest non-null document for each type — shorter = easier
        # to read in full; we can pull longer ones if structure is ambiguous.
        samples_query = """
            SELECT DISTINCT ON (doc_type, raw_format)
                id,
                source,
                doc_type,
                raw_format,
                external_id,
                title,
                status,
                length(raw_text) AS char_count,
                raw_text
            FROM documents
            WHERE raw_text IS NOT NULL
              AND status != 'error'
            ORDER BY doc_type, raw_format, length(raw_text) ASC
        """
        samples = conn.execute(samples_query).fetchall()
        col_names = [
            "id", "source", "doc_type", "raw_format",
            "external_id", "title", "status", "char_count", "raw_text"
        ]

        for row in samples:
            r = dict(zip(col_names, row))
            slug = f"{r['doc_type']}__{r['raw_format']}__{r['external_id']}"
            slug = slug.replace("/", "-").replace(" ", "_")[:80]

            # Write the raw text (XML or HTML) as-is
            ext = r["raw_format"] if r["raw_format"] in ("xml", "html") else "txt"
            raw_path = OUT / f"{slug}.{ext}"
            raw_path.write_text(r["raw_text"], encoding="utf-8")

            # Write a metadata sidecar
            meta = {k: v for k, v in r.items() if k != "raw_text"}
            (OUT / f"{slug}.meta.json").write_text(
                json.dumps(meta, indent=2, default=str)
            )

            print(f"  {r['doc_type']:30s}  {r['raw_format']:5s}  "
                  f"{r['char_count']:>8,} chars  → corpus_samples/{slug}.{ext}")

        # ── 3. Null-text inventory ───────────────────────────────────────────
        print("\n=== NULL / ERROR DOCUMENTS ===\n")
        null_rows = conn.execute("""
            SELECT id, source, doc_type, external_id, status, error_msg
            FROM documents
            WHERE raw_text IS NULL OR status = 'error'
            ORDER BY source, doc_type
        """).fetchall()

        if null_rows:
            null_col = ["id", "source", "doc_type", "external_id", "status", "error_msg"]
            for row in null_rows:
                r = dict(zip(null_col, row))
                print(f"  [{r['status']:8s}]  {r['doc_type']:30s}  "
                      f"{r['external_id']}  {r['error_msg'] or ''}")
            (OUT / "01_null_error_inventory.json").write_text(
                json.dumps(
                    [dict(zip(null_col, row)) for row in null_rows],
                    indent=2, default=str
                )
            )
            print(f"\n  → saved corpus_samples/01_null_error_inventory.json")
        else:
            print("  None — all documents have raw_text and status != error")

        print(f"\nDone. Open corpus_samples/ to inspect.\n")


if __name__ == "__main__":
    run()