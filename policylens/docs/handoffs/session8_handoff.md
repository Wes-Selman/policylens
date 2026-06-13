# PolicyLens — Session 8 Handoff
## Complete Decisions Log (Sessions 0–7) + Session 8 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 7)

**Annotation strategy:** Model-primary annotation. Human annotators
sample-check, with stratified sampling that oversamples structurally
complex and domain-ambiguous provisions (not random). The IRR pilot
(15 provisions) is a prompt calibration instrument, not a human annotator
training gate.

**Sequencing:** Phase 1 (Chunk & Store) is complete as of Session 7.
All 120 documents are at status='transformed'. 943 provision records
written. The project now moves to Phase 2 (front-end) — but a dedicated
security/legal scoping session is required before Phase 2 work begins.
Session 8 agenda is therefore the scoping session.

**Pipeline architecture:** Three-layer pipeline fully implemented through
Layer 2b. Layer 2a (extraction) complete Session 5. Layer 2b (normalization)
complete Session 7.

**Artifacts in repo:**
- provision_schema.yaml — full provision record schema (updated Session 6b)
- controlled_vocabulary.yaml — all enumerated field definitions + cross-rules
- baseline_doctrine.yaml — per-sub-domain constitutional baseline table
- decisions_log.md — rationale layer (updated Session 7)
- project_plan.md — phased project plan through Phase 5 (updated Session 7)

---

## Decisions Log — Sessions 0–6b

*(Full text in decisions_log.md in repo)*

**Sessions 0–4:** Provision definition, ontology, clustering mechanism,
constitutional baseline, annotation strategy, pipeline architecture,
ExtractedUnit as persisted intermediate, LegalAddress as first-class
entity, context_text, temporal fields, boilerplate classification,
doc_status enum, pipeline idempotency.

**Session 5:** Extractor dispatch registry, deferred psycopg import,
element_type assignment boundary, provision ID separator, proclamations
produce zero provisions (expected), bare noun phrase list items (Finding 4).

**Session 6b:** jurisdiction_scope field added to ExtractedUnit; two-layer
jurisdiction design (extractor coarse signal, normalizer refinement);
migrate_session6b.sql applied.

---

## Decisions Log — Session 7 (Summary)

Full rationale in decisions_log.md. Key decisions:

**Atomicity heuristic:** Three fragment patterns — em-dash stubs (ends with
U+2014), bare fragments (no legislative verb AND ≤15 words), definition
block intros (^In (this|the) [A-Za-z ]+[:—]). chunk_flag priority:
nested_conditional > cross_reference > boundary > clean.

**element_type override extension:** Normalizer may now override
provision_candidate → header for definition block intros (extends Session 5
sanction of provision_candidate → boilerplate). Both are semantic judgments;
lineage preserved in extracted_units.

**Boilerplate child inheritance:** Child units of a boilerplate parent
(detected via section_path prefix matching) inherit the boilerplate
classification regardless of their own text.

**context_text section_path fallback:** FR documents produce no header
units; section_path joined label used as fallback when no section_heading
available from extractor.

**Inline citation detection:** _CITATION_RE detects both short form
(N U.S.C.) and long form (section N of title N, United States Code).
Used as chunk_flag trigger when legal_address_raw is None (which is the
entire current corpus — citations appear in prose, not structured XML).

**jurisdiction_scope backfill:** migrate_session6b.sql defaulted all
existing extracted_units to 'federal_only' without re-applying the
_INVOLVES_STATES_PATTERN. 20 rows across 11 documents were manually
backfilled in Session 7. Affected documents re-normalized. New ingestion
is unaffected (pattern applied at extraction time).

---

## Session 7 Corpus Results (Final)

- Documents at status='transformed': 120/120, zero errors
- Total provisions: 943
- element_type: boilerplate=30, header=9, provision_candidate=904
- chunk_flag: clean=474, review_boundary=349, review_cross_reference=120,
  review_nested_conditional=0
- condition_stack: depth-0=862, depth-1=78, depth-2=3, depth-3+=0
- jurisdiction: federal_only=926, creates_floor=8, involves_states=5,
  preempts_state=3, defers_to_state=1
- context_text: 943/943 populated, 0 nulls

---

## Phase 1 Completion Checklist

- ✅ All 120 documents at status='transformed'
- ✅ Zero documents at status='raw' or 'extracted'
- ✅ context_text populated on all provision records
- ✅ chunk_flag populated on all provision records
- ✅ jurisdiction populated on all provision records
- ✅ Chunking report reviewed; edge case distribution understood
- ✅ All pipeline stages idempotent
- ✅ decisions_log.md updated through Session 7
- ⬜ migrate_session7_jurisdiction_backfill.sql committed to repo

---

## Session 8 Primary Agenda: Phase 2 Scoping Session

Phase 1 is complete. Session 8 is the dedicated scoping session that
defines Phase 2 and gates front-end work. No front-end code is written
this session.

**Agenda sequencing rationale:** Phase decomposition and technology
decisions come before security/legal review. The threat model, data
storage decisions, and API compliance review are most useful when there
is a concrete, sequenced plan to review against — the security surface
of a read-only document browser is materially different from that of a
semantic search tool with user accounts. Decompose first so the security
review has a specific target. Any blocking legal findings get incorporated
before the plan is finalised.

### 0. One carry-forward task from Session 7

**Commit migrate_session7_jurisdiction_backfill.sql.** This file documents
the one-time SQL backfill applied to correct jurisdiction_scope on 20
extracted_units rows that were incorrectly defaulted to 'federal_only'
by migrate_session6b.sql. Content:

```sql
-- migrate_session7_jurisdiction_backfill.sql
-- One-time backfill: applies _INVOLVES_STATES_PATTERN retroactively to
-- extracted_units rows that were inserted before Session 6b and therefore
-- defaulted to 'federal_only' without pattern matching.
-- Applied manually in Session 7. Committed here for audit trail only.
-- Safe to re-run (idempotent — pattern match on already-updated rows
-- that are already 'involves_states' is a no-op).
UPDATE extracted_units
SET jurisdiction_scope = 'involves_states'
WHERE jurisdiction_scope = 'federal_only'
AND raw_text ~* 'State government|States? may|States? shall|States? must
|State law|State laws|preempt|supersede|displace|occupy the field
|no State may|State law is preempted|subject to State law
|as determined by the State|minimum standard|not less than
|may provide greater|more protective';
```

### 1. Phase decomposition

"Phase 2" as currently described contains multiple distinct product
surfaces. Assign phase numbers and sequence explicitly before any other
decisions are made.

**Candidate sub-phases (to be numbered in session):**

A. **Document browser (Mode A)** — read-only provision display, no
   annotation required, no vector search. Ships earliest. Requires:
   basic web framework decision, DB connection from web tier, provision
   card component, section hierarchy display.

B. **Keyword search** — full-text search on provisions.text using existing
   tsvector infrastructure. Requires: search UI, result ranking. Can ship
   without annotation.

C. **Embedding pipeline + semantic search (Mode B)** — requires pgvector
   installation, embedding model selection, context_text embedding job,
   vector similarity search. Significant infrastructure addition.

D. **Annotation-aware filtering** — filter by domain, valence, modality.
   Requires Phase 3 (annotation) to be complete first.

E. **2D ideological visualization** — requires annotation + clustering.
   Requires Phases 3 and 5.

F. **Temporal traversal (Mode C)** — requires temporal chain populated
   (effective_date, superseded_by). Currently nullable; population is
   opportunistic.

G. **Legislator profiling / says-vs-does** — requires legislator data
   joins. Feasibility explicitly unvalidated. Validate before sequencing.

**Decision needed:** Assign phase numbers to A–G, sequence dependencies,
identify which can ship in parallel.

### 2. Technology decisions (prerequisite for Phase 2 code)

These have not been decided and must be resolved before Phase 2 begins:

- **Web framework:** Python (FastAPI/Flask) vs. Node vs. other
- **Hosting:** self-hosted vs. managed (Railway, Render, Fly.io, etc.)
- **Frontend:** server-rendered vs. SPA; framework if SPA
- **DB connection from web tier:** direct psycopg vs. connection pooler
  (PgBouncer); resolve db/__init__.py singleton smell (flagged Session 5)
- **Deployment pipeline:** CI/CD, environment management

### 3. Legislator data feasibility check

Before sequencing any phase that depends on legislator joins, validate:
- What is the source for legislator vote records? (ProPublica Congress API,
  VoteSmart, GovTrack, congress.gov votes endpoint)
- Are vote records joinable to the bill corpus already ingested?
  (119th Congress bills — check vote record availability for HR/S bills)
- What is the schema for a legislator record and a vote record?
- Is the join feasible with the current data model, or does it require
  new tables?

Document findings and decide whether to include legislator features in
Phase 2 sequencing or push to a later phase.

### 4. Security and legal review

Conducted against the decomposed plan from items 1–3. Review each item
and record decisions or open questions:

**API terms of use:**
- Congress.gov API: check terms for derivative works, display rights,
  attribution requirements
- Federal Register API: check terms for commercial use, redistribution
- Decision needed: does serving parsed provision text to end users constitute
  a derivative work requiring attribution or licensing compliance?

**User data storage:**
- What user data will be collected at minimum viable launch?
  (session data, search queries, account info if any)
- Where will it be stored? What retention policy?
- GDPR/CCPA applicability if international users access the site
- Decision needed: anonymous-first vs. account-based architecture

**Advertising data flows:**
- Preferred model: contextual display advertising (Carbon Ads, Ethical Ads)
- Hard constraint: no behavioral or political advertising, no advertiser
  access to user data
- Decision needed: which ad network(s) are compatible with the constraint?
  Review Carbon Ads and Ethical Ads terms explicitly
- Decision needed: does serving ads on a site that scores legislation
  ideologically create any editorial independence concerns?

**Threat model:**
- PolicyLens scores legislation ideologically — this creates a target for:
  (a) political actors who disagree with the scoring methodology
  (b) adversarial corpus manipulation (submitting legislation designed
      to game the scoring)
  (c) reputational attacks if scoring is perceived as biased
- Decision needed: what is the public communication strategy for the
  scoring methodology? (full transparency vs. summary disclosure)
- Decision needed: what is the abuse/complaint handling process?

---

## Deferred (not Session 8)

- Front-end code (gates on scoping session completion)
- Post-pilot adjudication model
- Four Hohfeldian correlatives — second annotation pass
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale
- Clustering sensitivity analysis
- k-means parameter selection
- pgvector extension installation (Phase 3/4)
- Temporal field population (effective_date, superseded_by) — opportunistic
- State legislative ingestion (LegiScan/OpenStates) — separate source
  family, separate scoping session

---

## Standing Rules

- Every decision entry must include a rationale.
- Deferred items carry forward verbatim until decided or explicitly dropped.
- New open questions surfaced in a session are added to the next session's
  agenda before the session closes.
- The handoff document is the single source of truth.
- **Implementation review:** before any implementation decision, evaluate
  from the perspectives of data engineer, product manager, data scientist,
  UX, and user journey. Assess feasibility and testability explicitly.
- **Incremental test suite:** after each implementation change, write
  tests before moving to the next task. Tests are never deferred.
- **Security and legal:** a standing consideration at every session.