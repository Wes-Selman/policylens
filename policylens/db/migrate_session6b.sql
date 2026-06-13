-- migrate_session6b.sql
-- Adds: jurisdiction_scope to extracted_units,
--       jurisdiction to provisions.
--
-- Run after migrate_session5.sql.
-- Safe to run multiple times (all statements are idempotent).

-- ── 1. extracted_units: jurisdiction_scope ────────────────────────────────
-- Coarse signal set by the extractor.
-- Valid values: 'federal_only' | 'involves_states' | 'unknown'
-- Default: 'federal_only' — all existing rows are federal corpus documents.
ALTER TABLE extracted_units
    ADD COLUMN IF NOT EXISTS jurisdiction_scope TEXT NOT NULL DEFAULT 'federal_only';

CREATE INDEX IF NOT EXISTS idx_extracted_units_jurisdiction_scope
    ON extracted_units(jurisdiction_scope);

-- ── 2. provisions: jurisdiction ───────────────────────────────────────────
-- Refined jurisdiction classification assigned by the normalizer.
-- Valid values:
--   'federal_only'    — operates only at the federal level
--   'preempts_state'  — explicitly displaces state law
--   'defers_to_state' — explicitly grants states discretion
--   'creates_floor'   — sets a federal minimum; states may exceed
--   'involves_states' — involves states but relationship not yet classified
--   'unknown'         — could not be determined
-- Default: 'federal_only' — all existing rows are federal corpus documents.
ALTER TABLE provisions
    ADD COLUMN IF NOT EXISTS jurisdiction TEXT NOT NULL DEFAULT 'federal_only';

CREATE INDEX IF NOT EXISTS idx_provisions_jurisdiction
    ON provisions(jurisdiction);
