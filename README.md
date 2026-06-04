# policylens
Legislative source aggregator and provision classifier
# PolicyLens

A legislative intelligence pipeline that parses bills, executive orders, and federal rules into atomic provisions, classified across philosophical, rights, moral, and societal dimensions. Party alignment is a derived output, not an input label.

---

## Architecture

The project is built in three layers:

**Layer 1 — Raw Source Aggregator** ✅
Ingests legislative documents from public APIs into PostgreSQL with full-text search. CLI-first, no frontend.

**Layer 2 — Text Transformation** 🔲
Chunks documents into discrete atomic provisions, resolves internal references inline, strips boilerplate, adds lightweight semantic tags. Serves both human readability and model digestibility.

**Layer 3 — PolicyLens Proper** 🔲
Provision extraction and classification. Moral ontology applied as analysis layer. Party alignment derived from classification output.

---

## Stack

- **Language:** Python 3.9+
- **Database:** PostgreSQL 16 (Docker)
- **Key libraries:** httpx, psycopg, psycopg-pool, tenacity, click, python-dotenv

---

## Project Structure
policylens/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── policylens/
│   ├── db/
│   │   ├── init.py        # Connection pool
│   │   └── schema.sql         # Table definitions and enums
│   ├── sources/
│   │   ├── federal_register.py
│   │   └── congress.py
│   └── cli.py                 # Entry point for all pipeline commands

---

## Setup

**1. Clone and install**
```bash
git clone https://github.com/YOUR_USERNAME/policylens.git
cd policylens
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Fill in POSTGRES_PASSWORD, POSTGRES_DSN, CONGRESS_API_KEY
```

DSN format:
postgresql://policylens:YOUR_PASSWORD@localhost:5432/policylens?gssencmode=disable

API key: https://api.congress.gov/sign-up/

**3. Start the database**
```bash
docker compose up -d
```

---

## CLI Commands

**Ingest presidential documents from the Federal Register**
```bash
python -m policylens.cli ingest-fr --pages 1
```

**Ingest bills from Congress.gov**
```bash
# House bills
python -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber house

# Senate bills
python -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber senate

# Both chambers
python -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber both
```

Options:
- `--congress` — Congress number (default: 119)
- `--limit` — Documents per bill type (default: 20)
- `--offset` — Pagination offset for backfilling
- `--chamber` — `house`, `senate`, or `both`

---

## Database Schema

```sql
documents (
    id          SERIAL PRIMARY KEY,
    source      doc_source   -- 'federal_register' | 'congress'
    doc_type    doc_type     -- 'executive_order' | 'bill' | 'resolution' | ...
    raw_format  doc_format   -- 'xml' | 'json' | 'html' | 'text'
    status      doc_status   -- 'raw' | 'transformed' | 'classified' | 'error'
    external_id TEXT UNIQUE  -- source's own identifier
    title       TEXT
    date        DATE
    url         TEXT
    raw_text    TEXT
    error_msg   TEXT
    fetched_at  TIMESTAMPTZ
    fts         tsvector     -- generated, GIN indexed for full-text search
)
```

The `status` column is the handoff contract between layers:
- Layer 1 writes `raw`
- Layer 2 queries for `raw`, processes, advances to `transformed`
- Layer 3 queries for `transformed`, advances to `classified`

---

## Current Data Sample

| Source | Doc Type | Count |
|--------|----------|-------|
| Federal Register | presidential_proclamation | 8 |
| Federal Register | executive_order | 5 |
| Federal Register | notice | 5 |
| Federal Register | other | 2 |
| Congress | resolution | 64 |
| Congress | bill | 36 |

---

## Next Up — Layer 2

Design decisions to make before starting:
- Chunking strategy: sentence boundary vs. section boundary vs. provision boundary
- How to handle XML structure from Federal Register vs. Congress.gov differently
- Reference resolution approach: inline expansion vs. linked provision graph
- Semantic tag vocabulary: define the ontology before tagging begins