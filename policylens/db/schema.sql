CREATE TYPE doc_source AS ENUM (
    'federal_register',
    'congress'
);

CREATE TYPE doc_type AS ENUM (
    'executive_order',
    'presidential_proclamation',
    'presidential_memorandum',
    'rule',
    'proposed_rule',
    'notice',
    'bill',
    'resolution',
    'hearing_transcript',
    'congressional_record',
    'other'
);

CREATE TYPE doc_format AS ENUM (
    'xml',
    'json',
    'html',
    'text'
);

CREATE TYPE doc_status AS ENUM (
    'raw',
    'transformed',
    'classified',
    'error'
);

CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    source      doc_source  NOT NULL,
    doc_type    doc_type    NOT NULL,
    raw_format  doc_format  NOT NULL,
    status      doc_status  NOT NULL DEFAULT 'raw',
    external_id TEXT        UNIQUE NOT NULL,
    title       TEXT,
    date        DATE,
    url         TEXT,
    raw_text    TEXT,
    error_msg   TEXT,
    fetched_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_source   ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_date     ON documents(date);
CREATE INDEX IF NOT EXISTS idx_documents_status   ON documents(status);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title,'') || ' ' || coalesce(raw_text,''))
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_documents_fts ON documents USING GIN(fts);