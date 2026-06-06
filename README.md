# PolicyLens

A legislative intelligence pipeline that parses bills, executive orders, and federal rules into atomic provisions, classified across philosophical, rights, moral, and societal dimensions. Party alignment is a derived output, not an input label.

---

## Architecture

The project is built in three layers, with Layer 2 split into two sub-stages:

**Layer 1 — Raw Source Aggregator** ✅
Ingests legislative documents from public APIs into PostgreSQL with full-text search. CLI-first, no frontend.

**Layer 2a — Extraction** 🔄
Source-specific extractors parse raw XML into a structured intermediate representation (`ExtractedUnit`). Each source schema has its own extractor that implements a common interface. New source = new extractor file; the normalizer is never touched. Current extractors: `FRPresdocuExtractor` (Federal Register PRESDOCU XML), `USLMExtractor` (Congressional USLM XML). Extracted units are persisted in the `extracted_units` table — the reprocessing boundary between raw documents and normalized provisions.

**Layer 2b — Normalization** 🔄
Source-agnostic normalizer reads `ExtractedUnit` records and produces provision records. Applies the atomicity test, detects nested conditionals, constructs `context_text` for future vector embedding, assigns `chunk_flag`, and writes to `provisions`, `legal_addresses`, and `provision_references`. Advances document status from `extracted` to `transformed`.

**Layer 3 — PolicyLens Proper** 🔲
Model-primary annotation of provisions across a controlled vocabulary (domain, valence, subject_type, modality). Provisions are scored on signed ordinal liberty axes (economic, social) and projected into 2D ideological space. Party alignment is derived from clustering output, not used as a training label. Human reviewers sample-check model annotations with stratified sampling weighted toward complex provisions.

---

## Stack

- **Language:** Python 3.9+
- **Database:** PostgreSQL 16 (Docker)
- **Key libraries:** httpx, psycopg, psycopg-pool, tenacity, click, python-dotenv, lxml

---

## Project Structure

```
policylens/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── docs/
│   ├── decisions_log.md           # Why the system is structured the way it is
│   ├── project_plan.md            # Phased plan, phases 0–5
│   ├── interpretation_notes.md    # Working notes seeding future user-facing training docs
│   └── handoffs/                  # Session handoff prompts, one per session
├── ontology/
│   ├── provision_schema.yaml      # Full provision record schema
│   ├── controlled_vocabulary.yaml # Enumerated values + cross-rules
│   └── baseline_doctrine.yaml     # Constitutional baseline table per sub-domain
└── policylens/
    ├── db/
    │   ├── __init__.py            # Connection pool
    │   └── schema.sql             # Table definitions and enums
    ├── sources/
    │   ├── federal_register.py    # FR API client
    │   └── congress.py            # Congress.gov API client
    ├── extractors/
    │   ├── base.py                # BaseExtractor interface
    │   ├── fr_presdocu.py         # Federal Register PRESDOCU XML extractor
    │   └── uslm.py                # Congressional USLM XML extractor
    ├── chunker/
    │   ├── types.py               # ExtractedUnit dataclass
    │   └── normalize.py           # Source-agnostic normalizer
    └── cli.py                     # Entry point for all pipeline commands
```

---

## Setup

**1. Clone and install**
```bash
git clone https://github.com/Wes-Selman/policylens.git
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
python3 -m policylens.cli ingest-fr --pages 1
```

**Ingest bills from Congress.gov**
```bash
python3 -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber house
python3 -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber senate
python3 -m policylens.cli ingest-congress --congress 119 --limit 20 --chamber both
```

Options:
- `--congress` — Congress number (default: 119)
- `--limit` — Documents per bill type (default: 20)
- `--offset` — Pagination offset for backfilling
- `--chamber` — `house`, `senate`, or `both`

**Extract raw documents into structured units**
```bash
python3 -m policylens.cli chunk-extract
```
Processes all documents with `status='raw'`. Writes to `extracted_units`. Advances status to `extracted`. Idempotent.

**Normalize extracted units into provisions**
```bash
python3 -m policylens.cli chunk-normalize
```
Processes all documents with `status='extracted'`. Writes to `provisions`, `legal_addresses`, `provision_references`. Advances status to `transformed`. Idempotent.

**Inspect corpus (development utility)**
```bash
python3 inspect_corpus.py
```
Dumps corpus overview, one sample document per (doc_type × format) combination, and null/error inventory to `corpus_samples/`.

---

## Database Schema

```sql
-- Layer 1: raw source documents
documents (
    id          SERIAL PRIMARY KEY,
    source      doc_source   -- 'federal_register' | 'congress'
    doc_type    doc_type     -- 'executive_order' | 'bill' | 'resolution' | ...
    raw_format  doc_format   -- 'xml' | 'json' | 'html' | 'text'
    status      doc_status   -- 'raw' | 'extracted' | 'transformed' | 'classified' | 'error'
    external_id TEXT UNIQUE
    title       TEXT
    date        DATE
    url         TEXT
    raw_text    TEXT
    error_msg   TEXT
    fetched_at  TIMESTAMPTZ
    fts         tsvector     -- generated, GIN indexed
)

-- Layer 2a: persisted extraction intermediate
extracted_units (
    id                SERIAL PRIMARY KEY,
    doc_id            INTEGER REFERENCES documents(id),
    source_schema     TEXT     -- 'fr_presdocu' | 'uslm' | ...
    source_element_id TEXT     -- XML id attribute or derived key
    element_type      TEXT     -- 'provision_candidate' | 'boilerplate' | 'preamble' | 'header'
    section_path      TEXT[]   -- hierarchy as extracted, e.g. ['Sec. 2', '(b)']
    raw_text          TEXT
    legal_address_raw TEXT     -- raw citation string if extractable, nullable
    nesting_depth     INTEGER
    extraction_notes  TEXT[]
    UNIQUE (doc_id, source_element_id)
)

-- Layer 2b: normalized provision records
provisions (
    id                  TEXT PRIMARY KEY,  -- doc_id:section_id:provision_index
    doc_id              INTEGER REFERENCES documents(id),
    extracted_unit_id   INTEGER REFERENCES extracted_units(id),
    section_id          TEXT,
    section_heading     TEXT,
    provision_index     INTEGER,
    text                TEXT,
    context_text        TEXT,   -- enriched string for vector embedding
    doc_type            TEXT,
    element_type        TEXT,
    condition_stack     JSONB,
    chunk_flag          TEXT,
    -- temporal (nullable; populated as data allows)
    legal_address_id    INTEGER REFERENCES legal_addresses(id),
    effective_date      DATE,
    superseded_by       TEXT REFERENCES provisions(id),
    superseded_date     DATE,
    -- annotation (populated in Phase 3)
    modality            TEXT,
    object_class        TEXT,
    domain              TEXT,
    valence             INTEGER,
    valence_economic    INTEGER,
    valence_social      INTEGER,
    subject_type        TEXT,
    baseline_statement  TEXT,
    pending_reason      TEXT,
    pending_monitor     JSONB,
    annotation_method   TEXT,
    annotation_version  TEXT,
    sample_check_flag   BOOLEAN DEFAULT false,
    sample_check_result TEXT,
    doctrine_version_date DATE,
    UNIQUE (doc_id, section_id, provision_index)
)

-- First-class legal location entities (graph node)
legal_addresses (
    id              SERIAL PRIMARY KEY,
    statute         TEXT,   -- e.g. '26 U.S.C.'
    section         TEXT,   -- e.g. '§ 7701'
    canonical_cite  TEXT,   -- normalized citation string
    UNIQUE (statute, section)
)

-- Typed edges: provision → legal_address (graph edge)
provision_references (
    provision_id      TEXT REFERENCES provisions(id),
    legal_address_id  INTEGER REFERENCES legal_addresses(id),
    ref_type          TEXT,  -- 'amends' | 'references' | 'implements' | 'supersedes' | 'enacts'
    PRIMARY KEY (provision_id, legal_address_id, ref_type)
)
```

The `status` column is the pipeline contract between layers:
- Layer 1 writes `raw`
- Layer 2a queries `raw`, writes extracted_units, advances to `extracted`
- Layer 2b queries `extracted`, writes provisions, advances to `transformed`
- Layer 3 queries `transformed`, annotates provisions, advances to `classified`

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

All 120 documents ingested with no null text and no errors.

---

## Ontology

The ontology lives in `ontology/`. Three files:

- `provision_schema.yaml` — every field on a provision record, its type, allowed values, and constraints
- `controlled_vocabulary.yaml` — enumerated value definitions and cross-rules; designed to load directly into model annotation prompts
- `baseline_doctrine.yaml` — per-sub-domain constitutional baseline table used to anchor valence scoring; versioned by controlling authority date

Design decisions and rationale are in `docs/decisions_log.md`.

---

## Source XML Schemas

**Federal Register (PRESDOCU)**
Root: `<PRESDOCU>` with doc-type child (`EXECORD`, `PROCLA`, `PRNOTICE`, `DETERM`).
Content: `<FP>` and `<P>` paragraph elements. Section boundaries detected by
`<E T="04">` (section number) inside `<FP>`. Sub-paragraphs text-prefixed
with `(a)`, `(b)`, etc.

**Congressional USLM**
Root: `<bill>` or `<resolution>`. Explicit hierarchy:
`<legis-body>` → `<section>` → `<subsection>` → `<paragraph>`.
Section IDs from `<enum>` elements; machine-readable IDs on `id` attributes.
Provision text in `<text>` elements.