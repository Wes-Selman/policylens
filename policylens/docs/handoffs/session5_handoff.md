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
(Chunk & Store), Layer 2a (Extraction).

**Edge cases:** Handled empirically during chunker implementation as they
surface in the corpus, not deferred to a separate scheduled effort.
Genuinely ambiguous boundaries are flagged with chunk_flag for human
review; they are not excluded from the corpus.

**Pipeline architecture (decided Session 4):**
Layer 2 is split into Layer 2a (extraction, source-specific) and Layer 2b
(normalization, source-agnostic) with a persisted intermediate table
(extracted_units). New source = new extractor file. Normalizer is never
touched for new sources.

**Session sequencing (decided Session 5 planning):**
Session 5 covers DDL + extraction only. Normalization is Session 6.
Rationale: the normalizer's heuristics (atomicity test, boilerplate
detection, condition_stack construction) should be designed against real
extracted_units output, not hypothetical output. Inspecting extraction
results before writing the normalizer is strictly better than designing
both in the abstract.

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

## Decisions Log — Session 5 Planning

**DECIDED: Session 5 scoped to DDL + extraction only**
Normalization moved to Session 6.

Rationale: the normalizer's heuristics (atomicity test, boilerplate
detection, condition_stack construction) are semantic judgments that
should be designed against real extracted_units output. Running extraction
first and inspecting results before writing the normalizer produces better
heuristics and catches extractor design problems before they propagate
into the provision table. The architectural split between 2a and 2b exists
precisely to support this workflow.

**OPEN: Normalizer atomicity heuristic**
Deferred to Session 6. Will be decided after inspecting real
extracted_units output from the corpus. Candidate approach documented
in Session 6 handoff for review at session start.

---

## Session 5 Primary Agenda

### 1. DDL — four new tables + enum extension

Write and apply to the live database:

```sql
-- Must run outside a transaction or with AUTOCOMMIT
ALTER TYPE doc_status ADD VALUE 'extracted' AFTER 'raw';

CREATE TABLE extracted_units ( ... );
CREATE TABLE provisions ( ... );
CREATE TABLE legal_addresses ( ... );
CREATE TABLE provision_references ( ... );
```

Include all UNIQUE constraints, FK constraints, and indexes listed in
the DB engineer notes below. Verify with \d in psql after applying.

**Additional indexes beyond handoff spec (add now):**
- provisions(doc_id, provision_index) — Mode A reading order queries
- provisions(chunk_flag) — review queue queries
- provisions(element_type) — boilerplate exclusion filter

**DB engineer note on legal_addresses upsert:**
ON CONFLICT DO NOTHING does not return the existing id on conflict.
Use: INSERT ... ON CONFLICT (statute, section) DO UPDATE SET statute =
EXCLUDED.statute RETURNING id — this always returns the id regardless
of whether insert or conflict path was taken.

**DB engineer note on section_id separator:**
The provisions primary key format is doc_id:section_id:provision_index.
Use | as separator (not colon) to avoid ambiguity if section_id ever
contains a colon. Enforce in the id constructor in types.py.

### 2. ExtractedUnit dataclass
File: policylens/chunker/types.py

Fields:
- source_doc_id: int
- source_schema: str  — 'fr_presdocu' | 'uslm'
- raw_text: str
- section_path: list[str]  — hierarchy as extracted, e.g. ['Sec. 2', '(b)']
- legal_address_raw: str | None  — raw citation string if extractable
- element_type: str  — 'provision_candidate' | 'preamble' | 'header'
- nesting_depth: int
- source_element_id: str  — XML id attribute or derived deterministic key
- extraction_notes: list[str]

Note: element_type 'boilerplate' is assigned by the normalizer, not
the extractor. Extractors produce 'provision_candidate', 'preamble',
or 'header' only.

### 3. BaseExtractor interface
File: policylens/extractors/base.py

Abstract class with:
- __init__(self, doc: dict) — doc is a row from the documents table
- extract(self) -> list[ExtractedUnit]
- source_schema property (abstract) -> str

### 4. FRPresdocuExtractor
File: policylens/extractors/fr_presdocu.py

Handle: EXECORD, PROCLA, PRNOTICE, DETERM subtypes (detect from child
element tag under <PRESDOCU>).

Section boundary detection:
- <FP> containing an <E T="04"> child = new section
- Section number: text of the <E T="04"> element
- Section heading: text of the <E T="03"> element in the same <FP>,
  if present

Sub-paragraph detection:
- <P> or <FP SOURCE="FP1"> elements whose text begins with ^\([a-z0-9]+\)
- Sub-paragraph label extracted as part of section_path

Preamble detection:
- Opening <FP> elements before the first section boundary that contain
  the formula "By the authority vested in me" or "by virtue of the
  authority vested in me" → element_type: preamble

Boilerplate tag stripping (strip before text extraction):
PRTPAGE, GPH, PSIG, PLACE, DATE, FRDOC, FILED, BILCOD, TITLE3, PRES

source_element_id derivation:
- Use XML id attribute if present; otherwise derive as
  {subtype}:{section_path_joined}:{paragraph_index}

Test targets: EO 14407 (2026-11180), at least one proclamation (2026-09506).

### 5. USLMExtractor
File: policylens/extractors/uslm.py

Walk hierarchy: <legis-body> → <section> → <subsection> → <paragraph>
(and deeper if present: <subparagraph>, <clause>).

For each node at any level that has a <text> child:
- section_path: list of <enum> text values from root to this node
  e.g. ['1.', '(a)'] for section 1, subsection (a)
- source_element_id: id attribute on the node (always present on
  <section>/<subsection>; derive for deeper levels if absent)
- element_type: 'provision_candidate' for all <text>-bearing nodes
- header: <header> child of <section> → element_type: 'header'

Preamble: <legis-body> may have introductory text before the first
<section>; if present, tag element_type: preamble.

Test targets: 119-S-31 (bill), 119-SRES-7 (resolution).

### 6. CLI — chunk-extract command
Add to policylens/cli.py:

```
python3 -m policylens.cli chunk-extract [--doc-id N]
```

Behavior:
- Without --doc-id: queries all documents with status='raw'
- With --doc-id: processes single document (useful for testing)
- Dispatches to correct extractor based on source field:
  'federal_register' → FRPresdocuExtractor
  'congress' → USLMExtractor
- Writes extracted_units rows (ON CONFLICT DO NOTHING)
- Advances document status to 'extracted'
- Idempotent: re-running on an already-extracted document is a no-op

Output: per-document summary (doc_id, doc_type, units extracted,
element_type breakdown). Final summary: total documents processed,
total extracted_units written, any errors.

### 7. Corpus run + inspection
After chunk-extract runs successfully on all 120 documents:

Run this inspection query and record results in the handoff:
```sql
SELECT
    source_schema,
    element_type,
    COUNT(*) as count,
    AVG(nesting_depth) as avg_depth,
    MAX(nesting_depth) as max_depth,
    COUNT(*) FILTER (WHERE legal_address_raw IS NOT NULL) as with_citation
FROM extracted_units
GROUP BY source_schema, element_type
ORDER BY source_schema, element_type;
```

Also record: total extracted_units, distribution by doc_type, any
documents that errored during extraction. This output seeds Session 6's
normalizer design.

---

## Deferred to Session 6 (Normalization)

- Normalizer atomicity heuristic design (after inspecting extraction output)
- policylens/chunker/normalize.py
- CLI chunk-normalize command
- context_text construction (including preamble query pattern)
- condition_stack detection and encoding
- chunk_flag assignment logic
- provision_references population
- Chunking report generation

---

## Deferred (not Sessions 5 or 6)

- Post-pilot adjudication model
- Front-end scope (Phase 2) — technology and hosting decisions
- Four Hohfeldian correlatives — second annotation pass
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale
- Clustering sensitivity analysis
- k-means parameter selection
- pgvector extension installation (Phase 3/4)
- Temporal field population (effective_date, superseded_by) — opportunistic
- **Security/legal scoping session** — required before Phase 2 (front-end)
  begins. Scope: user data storage, API terms of use (Congress.gov,
  Federal Register), advertising data flows, threat model for a civic
  tech tool that scores legislation ideologically.

---

## Standing Rules

- Every decision entry must include a rationale. A decision without
  rationale is not a valid log entry.
- Deferred items carry forward verbatim until decided or explicitly dropped.
- New open questions surfaced in a session are added to the next session's
  agenda before the session closes.
- The handoff document is the single source of truth. Anything not in
  the handoff did not happen.
- **Implementation review:** before any implementation decision, evaluate
  from the perspectives of data engineer, product manager, data scientist,
  UX, and user journey. Assess feasibility and testability explicitly.
- **Incremental test suite:** after each implementation change, write
  tests before moving to the next task. Tests are never deferred to end
  of session or end of phase.
- **Security and legal:** a standing consideration at every session.
  Flag anything that touches user data, external API terms, or public
  exposure before implementation proceeds.