# PolicyLens

A civic intelligence platform that gives every person direct access to
what the law actually says — at the provision level, without editorial
interpretation. The foundation is a corpus of federal legislative and
regulatory text parsed into atomic deontic provisions (one subject, one
modality, one object), stored with structural metadata, and available
through a clean API and a trustworthy reading interface.

Party alignment is a derived output, not an input label.

---

## Architecture

The project is built in three layers, with Layer 2 split into two sub-stages:

**Layer 1 — Raw Source Aggregator** ✅ Complete
Ingests legislative documents from public APIs into PostgreSQL. CLI-first,
no frontend. Current corpus: 120 documents (Federal Register PRESDOCU +
Congressional USLM XML).

**Layer 2a — Extraction** ✅ Complete (Session 5)
Source-specific extractors parse raw XML into a structured intermediate
representation (`ExtractedUnit`). Each source schema has its own extractor
implementing a common interface. New source = new extractor file; the
normalizer is never touched. Current extractors: `FRPresdocuExtractor`
(Federal Register PRESDOCU XML), `USLMExtractor` (Congressional USLM XML).
Extracted units are persisted in the `extracted_units` table — the
reprocessing boundary between raw documents and normalized provisions.

**Layer 2b — Normalization** ✅ Complete (Session 7)
Source-agnostic normalizer reads `ExtractedUnit` records and produces
provision records. Applies the atomicity heuristic, detects nested
conditionals, constructs `context_text` for vector embedding, assigns
`chunk_flag`, detects inline citations, refines jurisdiction, and writes
to `provisions`, `legal_addresses`, and `provision_references`. Advances
document status from `extracted` to `transformed`. 943 provisions written
from 120 documents.

**Layer 2c — chunk-resolve** 🔲 Phase 2 (next)
Deterministic merge pass resolves em-dash stubs, bare fragment list items,
and inline cross-references. LLM agent pass on residual ambiguous cases.
Output: corpus where `chunk_flag='clean'` is genuinely earned. Prerequisite
before UI ships to real users.

**Layer 3 — PolicyLens Proper** 🔲 Phase 3
Model-primary annotation of provisions across a controlled vocabulary
(domain, valence, subject_type, modality). Provisions are scored on signed
ordinal liberty axes (economic, social) and projected into 2D ideological
space. Party alignment is derived from clustering output, not used as a
training label. Human reviewers sample-check model annotations with
stratified sampling weighted toward complex provisions.

---

## Stack

- **Language:** Python 3.9+
- **Database:** PostgreSQL 16 (Docker)
- **Key libraries:** httpx, lxml, psycopg, psycopg-pool, tenacity, click,
  python-dotenv

---

## Project Structure

```
policylens/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── docs/
│   ├── decisions_log.md           # Why the system is structured the way it is
│   ├── project_plan.md            # Phased plan through Phase 6
│   ├── interpretation_notes.md    # Working notes seeding future user-facing docs
│   └── handoffs/                  # Session handoff prompts, one per session
├── ontology/
│   ├── provision_schema.yaml      # Full provision record schema
│   ├── controlled_vocabulary.yaml # Enumerated values + cross-rules
│   └── baseline_doctrine.yaml     # Constitutional baseline table per sub-domain
├── tests/
│   ├── test_extractors.py         # Extractor unit tests (46 tests, no DB required)
│   └── test_normalizer.py         # Normalizer unit tests (no DB required)
└── policylens/
    ├── db/
    │   ├── __init__.py            # Connection pool (get_pool)
    │   ├── schema.sql             # Layer 1 table definitions and enums
    │   ├── migrate_session5.sql   # Session 5: 4 new tables + enum extension
    │   ├── migrate_session6b.sql  # Session 6b: jurisdiction fields
    │   ├── migrate_session7_jurisdiction_backfill.sql  # One-time backfill audit trail
    │   └── extracted_units.py     # DB persistence helpers for extraction pipeline
    ├── sources/
    │   ├── federal_register.py    # FR API client
    │   └── congress.py            # Congress.gov API client
    ├── extractors/
    │   ├── base.py                # BaseExtractor abstract interface
    │   ├── registry.py            # Extractor dispatch registry (get_extractor)
    │   ├── fr_presdocu.py         # Federal Register PRESDOCU XML extractor
    │   └── uslm.py                # Congressional USLM XML extractor
    ├── chunker/
    │   ├── types.py               # ExtractedUnit dataclass
    │   └── normalize.py           # Source-agnostic normalizer (Layer 2b)
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

**4. Apply migrations in order**
```bash
# ALTER TYPE ADD VALUE cannot run inside a transaction; use psql directly
psql $POSTGRES_DSN -f policylens/db/migrate_session5.sql
psql $POSTGRES_DSN -f policylens/db/migrate_session6b.sql
# migrate_session7_jurisdiction_backfill.sql is audit-trail only;
# only needed when restoring from a pre-Session-6b backup
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
python3 -m policylens.cli chunk-extract --doc-id 42   # single document
```
Processes all documents with `status='raw'`. Dispatches to the correct
extractor via `extractors/registry.py`. Writes to `extracted_units`.
Advances status to `extracted`. Idempotent.

**Normalize extracted units into provisions**
```bash
python3 -m policylens.cli chunk-normalize
python3 -m policylens.cli chunk-normalize --doc-id 42
```
Processes all documents with `status='extracted'`. Writes to `provisions`,
`legal_addresses`, `provision_references`. Advances status to `transformed`.
Idempotent.

**Run tests (no database required)**
```bash
python3 -m pytest tests/ -v
```

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
    source_schema     TEXT     -- 'fr_presdocu' | 'uslm'
    source_element_id TEXT     -- XML id attribute or derived deterministic key
    element_type      TEXT     -- 'provision_candidate' | 'preamble' | 'header'
    section_path      TEXT[]   -- hierarchy as extracted, e.g. ['Sec. 2', '(b)']
    raw_text          TEXT
    legal_address_raw TEXT     -- raw citation string if extractable, nullable
    nesting_depth     INTEGER
    jurisdiction_scope TEXT    -- 'federal_only' | 'involves_states' | 'unknown'
    extraction_notes  TEXT[]
    created_at        TIMESTAMPTZ
    UNIQUE (doc_id, source_element_id)
)

-- Layer 2b: normalized provision records
provisions (
    id                  TEXT PRIMARY KEY,  -- {doc_id}|{section_id}|{provision_index}
    doc_id              INTEGER REFERENCES documents(id),
    extracted_unit_id   INTEGER REFERENCES extracted_units(id),
    section_id          TEXT,
    section_heading     TEXT,
    provision_index     INTEGER,
    text                TEXT,
    context_text        TEXT,   -- enriched string for vector embedding (RAG)
    doc_type            TEXT,
    element_type        TEXT,   -- 'provision_candidate' | 'boilerplate' | 'header'
    condition_stack     JSONB,
    chunk_flag          TEXT,   -- 'clean' | 'review_nested_conditional' | ...
    jurisdiction        TEXT,   -- 'federal_only' | 'preempts_state' | ...
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
    canonical_cite  TEXT,
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

## Corpus Results (Session 7)

| Source | Doc Type | Count |
|--------|----------|-------|
| Federal Register | presidential_proclamation | 8 |
| Federal Register | executive_order | 5 |
| Federal Register | notice | 5 |
| Federal Register | other | 2 |
| Congress | resolution | 64 |
| Congress | bill | 36 |

**Provisions:** 943 total across 120 documents
**chunk_flag:** clean=474, review_boundary=349, review_cross_reference=120
**context_text:** 943/943 populated
**Documents at status='transformed':** 120/120

Phase 2 (chunk-resolve) will resolve the 469 non-clean provisions before
the UI ships.

---

## Ontology

The ontology lives in `ontology/`. Three files:

- `provision_schema.yaml` — every field on a provision record, its type,
  allowed values, and constraints
- `controlled_vocabulary.yaml` — enumerated value definitions and cross-rules;
  designed to load directly into model annotation prompts
- `baseline_doctrine.yaml` — per-sub-domain constitutional baseline table
  used to anchor valence scoring; versioned by controlling authority date

Design decisions and rationale are in `docs/decisions_log.md`.

---

## Extractor Architecture

New sources are added by creating a new file in `policylens/extractors/`
that subclasses `BaseExtractor` and registering it in
`policylens/extractors/registry.py`. The CLI and normalizer are never
modified for new sources.

```python
# policylens/extractors/registry.py — add one line per new source
register("new_source_name", NewSourceExtractor)
```

The extractor contract enforced by `BaseExtractor` and `ExtractedUnit.validate()`:
- `element_type` values from extractors: `provision_candidate` | `preamble` | `header`
- `element_type = boilerplate` is assigned by the normalizer only (semantic judgment)
- `source_element_id` must be unique within a document and deterministic across re-runs
- `extract()` is pure: same input always produces same output

---

## Source XML Schemas

**Federal Register (PRESDOCU)**
Root: `<PRESDOCU>` with doc-type child (`EXECORD`, `PROCLA`, `PRNOTICE`, `DETERM`).
Content: `<FP>` and `<P>` paragraph elements. Section boundaries detected by
`<E T="04">` (section number) inside `<FP>`. Sub-paragraphs text-prefixed
with `(a)`, `(b)`, etc. Boilerplate metadata tags stripped before extraction:
`PRTPAGE`, `GPH`, `PSIG`, `PLACE`, `DATE`, `FRDOC`, `FILED`, `BILCOD`, `TITLE3`, `PRES`.

**Congressional USLM**
Root: `<bill>` or `<resolution>`. Explicit hierarchy:
`<legis-body>` → `<section>` → `<subsection>` → `<paragraph>`.
Section IDs from `<enum>` elements; machine-readable IDs on `id` attributes.
Provision text in `<text>` elements. Nesting reaches depth 6 in complex bills.