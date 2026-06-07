-- Session 5 migration
-- Adds: 'extracted' to doc_status enum, extracted_units, provisions,
--       legal_addresses, provision_references tables.
-- Must be run with AUTOCOMMIT on (psql \set AUTOCOMMIT on) because
-- ALTER TYPE ADD VALUE cannot run inside a transaction block.

-- ── 1. Extend doc_status enum ─────────────────────────────────────────────
-- ALTER TYPE ADD VALUE is idempotent in Postgres 14+ via IF NOT EXISTS;
-- Postgres 16 supports this.
ALTER TYPE doc_status ADD VALUE IF NOT EXISTS 'extracted' AFTER 'raw';

-- ── 2. legal_addresses ────────────────────────────────────────────────────
-- First-class legal location entities. Graph node in future promotion.
CREATE TABLE IF NOT EXISTS legal_addresses (
    id              SERIAL PRIMARY KEY,
    statute         TEXT        NOT NULL,
    section         TEXT        NOT NULL,
    canonical_cite  TEXT,
    UNIQUE (statute, section)
);

-- ── 3. extracted_units ────────────────────────────────────────────────────
-- Persisted intermediate between raw documents and normalized provisions.
-- Reprocessing boundary: re-run normalizer without re-running extractor.
CREATE TABLE IF NOT EXISTS extracted_units (
    id                SERIAL PRIMARY KEY,
    doc_id            INTEGER     NOT NULL REFERENCES documents(id),
    source_schema     TEXT        NOT NULL,  -- 'fr_presdocu' | 'uslm'
    source_element_id TEXT        NOT NULL,  -- XML id attr or derived key
    element_type      TEXT        NOT NULL,  -- 'provision_candidate' | 'preamble' | 'header'
    section_path      TEXT[]      NOT NULL DEFAULT '{}',
    raw_text          TEXT,
    legal_address_raw TEXT,                  -- raw citation string if extractable
    nesting_depth     INTEGER     NOT NULL DEFAULT 0,
    extraction_notes  TEXT[]      NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doc_id, source_element_id)
);

CREATE INDEX IF NOT EXISTS idx_extracted_units_doc_id
    ON extracted_units(doc_id);
CREATE INDEX IF NOT EXISTS idx_extracted_units_element_type
    ON extracted_units(element_type);
CREATE INDEX IF NOT EXISTS idx_extracted_units_source_schema
    ON extracted_units(source_schema);

-- ── 4. provisions ─────────────────────────────────────────────────────────
-- Normalized provision records. Annotation fields nullable (Phase 3).
-- Temporal fields nullable (populated as data allows).
CREATE TABLE IF NOT EXISTS provisions (
    id                  TEXT        PRIMARY KEY,  -- {doc_id}|{section_id}|{provision_index}
    doc_id              INTEGER     NOT NULL REFERENCES documents(id),
    extracted_unit_id   INTEGER     NOT NULL REFERENCES extracted_units(id),
    section_id          TEXT        NOT NULL,
    section_heading     TEXT,
    provision_index     INTEGER     NOT NULL,
    text                TEXT        NOT NULL,
    context_text        TEXT        NOT NULL,
    doc_type            TEXT        NOT NULL,
    element_type        TEXT        NOT NULL DEFAULT 'provision_candidate',
    condition_stack     JSONB       NOT NULL DEFAULT '[]',
    chunk_flag          TEXT        NOT NULL DEFAULT 'clean',
    -- temporal (nullable; populated as data allows)
    legal_address_id    INTEGER     REFERENCES legal_addresses(id),
    effective_date      DATE,
    superseded_by       TEXT        REFERENCES provisions(id),
    superseded_date     DATE,
    -- annotation (populated in Phase 3)
    modality            TEXT,
    object_class        TEXT,
    domain              TEXT,
    valence             INTEGER     CHECK (valence BETWEEN -2 AND 2),
    valence_economic    INTEGER     CHECK (valence_economic BETWEEN -2 AND 2),
    valence_social      INTEGER     CHECK (valence_social BETWEEN -2 AND 2),
    subject_type        TEXT,
    baseline_statement  TEXT,
    pending_reason      TEXT,
    pending_monitor     JSONB,
    annotation_method   TEXT,
    annotation_version  TEXT,
    sample_check_flag   BOOLEAN     NOT NULL DEFAULT false,
    sample_check_result TEXT,
    doctrine_version_date DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (doc_id, section_id, provision_index)
);

CREATE INDEX IF NOT EXISTS idx_provisions_doc_id
    ON provisions(doc_id);
CREATE INDEX IF NOT EXISTS idx_provisions_doc_id_provision_index
    ON provisions(doc_id, provision_index);
CREATE INDEX IF NOT EXISTS idx_provisions_chunk_flag
    ON provisions(chunk_flag);
CREATE INDEX IF NOT EXISTS idx_provisions_element_type
    ON provisions(element_type);
CREATE INDEX IF NOT EXISTS idx_provisions_domain
    ON provisions(domain);

-- ── 5. provision_references ───────────────────────────────────────────────
-- Junction table: typed edges provision → legal_address.
-- Graph-promotable without schema migration.
CREATE TABLE IF NOT EXISTS provision_references (
    provision_id        TEXT        NOT NULL REFERENCES provisions(id),
    legal_address_id    INTEGER     NOT NULL REFERENCES legal_addresses(id),
    ref_type            TEXT        NOT NULL,  -- 'amends'|'references'|'implements'|'supersedes'|'enacts'
    PRIMARY KEY (provision_id, legal_address_id, ref_type)
);

CREATE INDEX IF NOT EXISTS idx_provision_references_provision_id
    ON provision_references(provision_id);
CREATE INDEX IF NOT EXISTS idx_provision_references_legal_address_id
    ON provision_references(legal_address_id);
