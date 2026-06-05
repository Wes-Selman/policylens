# PolicyLens

A legislative intelligence pipeline that parses bills, executive orders, and federal rules into atomic provisions, classified across philosophical, rights, moral, and societal dimensions. Party alignment is a derived output, not an input label.

---

## Architecture

The project is built in three layers:

**Layer 1 — Raw Source Aggregator** ✅
Ingests legislative documents from public APIs into PostgreSQL with full-text search. CLI-first, no frontend.

**Layer 2 — Text Transformation** 🔲
Chunks documents into discrete atomic provisions. A provision is the minimal deontic unit: one subject, one Hohfeldian modality (duty, permission, power, immunity), one object. Chunking operates at sentence/clause level; edge cases (nested conditionals, cross-references) are resolved empirically during implementation and flagged for review rather than deferred. Populates a `provisions` table; advances document status from `raw` to `transformed`.

**Layer 3 — PolicyLens Proper** 🔲
Model-primary annotation of provisions across a controlled vocabulary (domain, valence, subject_type, modality). Provisions are scored on signed ordinal liberty axes (economic, social) and projected into 2D ideological space. Party alignment is derived from clustering output, not used as a training label. Human reviewers sample-check model annotations with stratified sampling weighted toward complex provisions.

---

## Stack

- **Language:** Python 3.9+
- **Database:** PostgreSQL 16 (Docker)
- **Key libraries:** httpx, psycopg, psycopg-pool, tenacity, click, python-dotenv

---

## Project Structure

```
policylens/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── docs/
│   ├── decisions_log.md       # Why the ontology is structured the way it is
│   ├── project_plan.md        # Phased plan, phases 0–5
│   └── handoffs/              # Session handoff prompts, one per session
├── ontology/
│   ├── provision_schema.yaml      # Full provision record schema
│   ├── controlled_vocabulary.yaml # Enumerated values + cross-rules (load into model prompts)
│   └── baseline_doctrine.yaml     # Constitutional baseline table per sub-domain
└── policylens/
    ├── db/
    │   ├── __init__.py        # Connection pool
    │   └── schema.sql         # Table definitions and enums
    ├── sources/
    │   ├── federal_register.py
    │   └── congress.py
    └── cli.py                 # Entry point for all pipeline commands
```

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
```
postgresql://policylens:YOUR_PASSWORD@localhost:5432/policylens?gssencmode=disable
```

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
- Layer 2 queries for `raw`, chunks into provisions, advances to `transformed`
- Layer 3 queries for `transformed`, annotates provisions, advances to `classified`

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

## Ontology

The ontology lives in `ontology/`. Three files:

- `provision_schema.yaml` — every field on a provision record, its type, allowed values, and constraints
- `controlled_vocabulary.yaml` — enumerated value definitions and cross-rules; designed to load directly into model annotation prompts
- `baseline_doctrine.yaml` — per-sub-domain constitutional baseline table used to anchor valence scoring; versioned by controlling authority date

Design decisions and rationale are in `docs/decisions_log.md`.