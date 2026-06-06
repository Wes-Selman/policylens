# PolicyLens — Session 5 Handoff
## Complete Decisions Log (Sessions 0–4) + Session 5 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 4)

**Annotation strategy:** Model-primary annotation. Human annotators
sample-check, with stratified sampling that oversamples structurally
complex and domain-ambiguous provisions (not random). The IRR pilot
(15 provisions) is a prompt calibration instrument, not a human annotator
training gate.

**Sequencing:** Chunking first. Annotation fields are not populated at
chunking time. The taxonomy exists and is fully specified; it is not
needed until Phase 3 (Annotation). The project is currently in Phase 1
(Chunk & Store).

**Edge cases:** Handled empirically during chunker implementation as they
surface in the corpus, not deferred to a separate scheduled effort.
Genuinely ambiguous boundaries are flagged with chunk_flag for human
review; they are not excluded from the corpus.

**Pipeline architecture (decided Session 4):**
Layer 2 is split into Layer 2a (extraction, source-specific) and Layer 2b
(normalization, source-agnostic) with a persisted intermediate table
(extracted_units). New source = new extractor file. Normalizer is never
touched for new sources.

**Artifacts in repo:**
- provision_schema.yaml — full provision record schema (updated Session 4)
- controlled_vocabulary.yaml — all enumerated field definitions + cross-rules
- baseline_doctrine.yaml — per-sub-domain constitutional baseline table
- decisions_log.md — rationale layer for all major design decisions (updated Session 4)
- project_plan.md — phased project plan through Phase 5 (updated Session 4)

---

## Decisions Log — Sessions 0–3

*(Full text preserved — see prior handoff or decisions_log.md in repo)*

**Session 0:** Provision definition (Hohfeldian triple); top-level structure
(multi-dimensional taxonomy, graph-promotable).

**Session 1:** Clustering mechanism (signed ordinal → 2D projection →
k-means, party as post-hoc validation); required tag space structure;
minimum dimensions for axis separability (economic × social liberty,
four ideological quadrants).

**Session 2:** Constitutional baseline (post-New Deal economic, current
doctrine per sub-domain social); controlled vocabulary three minimum tags
(domain, valence, subject_type); normative layer vocabulary (Hohfeldian
primary set); independence assumption pilot design.

**Session 3:** Nested conditional rule (2-layer collapse, condition_stack);
cross-reference provisions (reference as object); domain:pending workflow;
annotation strategy (model-primary, stratified); adjudication procedure
(pilot phase); κ failure protocol; dimension-specific κ targets;
domain:mixed projection Option B; baseline doctrine table; chunking approach.

---

## Decisions Log — Session 4

**DECIDED: Pipeline architecture — extractor/normalizer split**
Layer 2 split into Layer 2a (source-specific extractors) and Layer 2b
(source-agnostic normalizer). Extractor interface defined in
policylens/extractors/base.py. Two extractors needed for current corpus:
FRPresdocuExtractor (policylens/extractors/fr_presdocu.py) and
USLMExtractor (policylens/extractors/uslm.py).

Rationale: new source = new extractor file, normalizer untouched.
Monolithic chunker requires surgery on shared code for every new source.

**DECIDED: ExtractedUnit as persisted intermediate**
extracted_units table added. ExtractedUnit records are stored, not held
in memory. Provides: reprocessing isolation (re-run normalizer without
re-running extractor), debugging (boundary decisions auditable), lineage
(provision → extracted_unit → document chain).

**DECIDED: LegalAddress as first-class entity**
legal_addresses table (id, statute, section, canonical_cite).
provision_references junction table (provision_id, legal_address_id,
ref_type) replaces object_ref embedded JSON struct from Sessions 0–3.

ref_type values: amends | references | implements | supersedes | enacts

Rationale: embedded struct buries LegalAddress — no deduplication, no
queryability, migration required for graph promotion. Junction table makes
graph promotion a query, not a migration.

**DECIDED: context_text field on provisions**
Normalizer constructs context_text at storage time from: document title,
doc type, section heading, condition_stack summary, provision text.
Used as input to vector embedding for semantic search (RAG).
Stored separately from raw text so embedding input is auditable and stable.
Does not change when annotation fields change — embeddings valid across
annotation passes.

**DECIDED: Temporal fields added (nullable)**
Four fields added to provisions, all nullable in Phase 1:
- legal_address_id (FK to legal_addresses — provision's own legal home)
- effective_date (when this version became operative)
- superseded_by (self-referential FK to superseding provision)
- superseded_date (when this version was superseded)

Rationale: schema migration after thousands of provisions are stored is
expensive. Nullable columns now cost nothing. Point-in-time query:
SELECT * FROM provisions WHERE legal_address_id = X
AND effective_date <= :date
AND (superseded_date IS NULL OR superseded_date > :date)

**DECIDED: Boilerplate classification**
Preamble ("By the authority vested in me..."): tagged element_type:preamble
by extractor. Not stored as provision record. Retained in extracted_units
for context_text construction.

General Provisions boilerplate (EO Sec. 3): tagged element_type:boilerplate
by normalizer. Stored as provision record. Annotated domain:governmental_structure.
Visible in document-reading UX (Mode A); excluded from search and temporal
traversal (Modes B, C).

Rationale: preamble has no deontic content. General Provisions boilerplate
does (immunities, limitations) — stripping it would silently omit real
legal content. Classification, not omission. Boilerplate detection is a
semantic judgment → belongs to normalizer, not extractor.

**DECIDED: doc_status enum extension**
Added 'extracted' between 'raw' and 'transformed'.
Full flow: raw → extracted → transformed → classified → error
'extracted' = extracted_units populated, provisions not yet written.

**DECIDED: Pipeline idempotency**
All stages must be safely re-runnable. UNIQUE constraints required:
- extracted_units: (doc_id, source_element_id)
- provisions: (doc_id, section_id, provision_index)
- provision_references: (provision_id, legal_address_id, ref_type)
- legal_addresses: (statute, section)
All inserts use ON CONFLICT DO NOTHING or DO UPDATE.

**DECIDED: Storage layer**
Postgres only. No separate vector store at current scale (120 docs, ~10k
future). pgvector extension added when embedding begins (Phase 3/4).
legal_addresses and provision_references structured for graph promotion
as relational tables; no graph DB needed until recursive traversal queries
become common.

**DECIDED: Source XML structure (corpus inspection)**
Two schemas confirmed in corpus:

FR PRESDOCU (federal_register source):
- Root: <PRESDOCU> with doc-type child (EXECORD, PROCLA, PRNOTICE, DETERM)
- Content elements: <FP> (full paragraph), <P> (paragraph)
- Section boundary: <FP> containing <E T="04"> child
- Section heading: <E T="03"> following the section number in same <FP>
- Sub-paragraphs (a), (b), (i): text-prefixed inside <P> or <FP SOURCE="FP1">
- Boilerplate tags to strip: PRTPAGE, GPH, PSIG, PLACE, DATE, FRDOC,
  FILED, BILCOD, TITLE3, PRES

USLM (congress source):
- Root: <bill> or <resolution>
- Content hierarchy: <legis-body> → <section> → <subsection> → <paragraph>
- Section ID: id attribute on <section>/<subsection> elements
- Display section number: <enum> child element
- Section heading: <header> child element
- Provision text: <text> element at each hierarchy level

**DECIDED: Three UX modes drive context requirements**
Mode A (read a document): section headings visible, document title
persistent, boilerplate provisions visually distinguished.
Mode B (search across documents): semantic search on context_text embeddings;
each result card must show text + section_heading + doc title + doc type +
date + source link.
Mode C (traverse time): legal_address page showing version chain ordered
by effective_date; supersession chain visible.

---

## Session 5 Primary Agenda

### 1. DDL — four new tables + enum extension
Write and apply:
- ALTER TYPE doc_status ADD VALUE 'extracted' (between raw and transformed)
- CREATE TABLE extracted_units
- CREATE TABLE provisions
- CREATE TABLE legal_addresses
- CREATE TABLE provision_references
Include all UNIQUE constraints, FK constraints, and indexes.
Verify with \d in psql.

### 2. ExtractedUnit dataclass and extractor interface
Write policylens/chunker/types.py — ExtractedUnit dataclass.
Write policylens/extractors/base.py — BaseExtractor abstract class.
Fields needed on ExtractedUnit: source_doc_id, source_schema,
raw_text, section_path, legal_address (nullable raw citation string),
element_type, nesting_depth, source_element_id, extraction_notes.

### 3. FRPresdocuExtractor
Implement policylens/extractors/fr_presdocu.py.
Handle: EXECORD, PROCLA, PRNOTICE, DETERM subtypes.
Section boundary detection: <FP> containing <E T="04">.
Sub-paragraph detection: regex on leading text ^\([a-z0-9]+\).
Boilerplate tag stripping: PRTPAGE, GPH, PSIG, PLACE, DATE, FRDOC,
FILED, BILCOD, TITLE3, PRES.
Preamble detection: opening formula paragraphs → element_type:preamble.
Test against EO 14407 and at least one proclamation.

### 4. USLMExtractor
Implement policylens/extractors/uslm.py.
Walk <section> → <subsection> → <paragraph> hierarchy.
section_id from <enum> values joined hierarchically (e.g. "§ 1(a)").
Preserve source_element_id from id attribute on section elements.
Test against 119-S-31 (bill) and 119-SRES-7 (resolution).

### 5. Wire CLI
Add chunk-extract and chunk-normalize commands to cli.py.
chunk-extract: queries for status='raw', dispatches to correct extractor
  by source field, writes extracted_units, advances to status='extracted'.
chunk-normalize: queries for status='extracted', runs normalizer,
  writes provisions + legal_addresses + provision_references,
  advances to status='transformed'.
Both commands idempotent.

---

## Deferred (not Session 5)

- Post-pilot adjudication model
- Front-end scope (Phase 2) — technology and hosting decisions
- Four Hohfeldian correlatives — second annotation pass
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale
- Clustering sensitivity analysis
- k-means parameter selection
- pgvector extension installation (Phase 3/4)
- Temporal field population (effective_date, superseded_by) — opportunistic

---

## Standing Rules

- Every decision entry must include a rationale. A decision without
  rationale is not a valid log entry.
- Deferred items carry forward verbatim until decided or explicitly dropped.
- New open questions surfaced in a session are added to the next session's
  agenda before the session closes.
- The handoff document is the single source of truth. Anything not in
  the handoff did not happen.