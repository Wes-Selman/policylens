# project_plan.md
# PolicyLens — Project Plan
# Last updated: Session 4

---

## Vision

A fully functional front-end that allows users to search, browse, and
interact with legislative and regulatory text chunked to the provision
level — where each provision is the minimal deontic unit (one subject,
one modality, one object). In later phases, provisions are labeled with
ideological scores and visualized on a two-axis liberty space, enabling
substantive analysis of how legislation positions itself across economic
and social liberty dimensions.

The provision-level foundation is designed to support civic accountability
features beyond document browsing, including: ideological profiling of
legislators and parties derived from the text of what they have sponsored
and voted for (not their stated positions); comparison of stated positions
against legislative action ("says vs. does"); and constituent engagement
tools that pre-load specific provisions and vote records as evidence for
contacting a representative. These features are sequenced after the core
annotation pipeline is stable and depend on legislator data joins whose
feasibility has not yet been validated.

A further potential direction — not yet scoped — is a public record of
constituent support or dissension at the provision level, giving citizens
a way to signal alignment with or opposition to specific legal statements.
The integrity challenges of such a feature (fraud prevention, identity
verification) are significant and would need to be resolved before
implementation. This is noted here to preserve the option without
committing to it.

Note on normative scoring: PolicyLens scores provisions on liberty axes
anchored to constitutional baselines. This is not an editorial judgment
about whether a provision is good or bad for any group. The product's
strength is that it shows what the law does without taking positions.
Features that would require PolicyLens to evaluate whether legislation
is beneficial for specific populations are out of scope — that judgment
belongs to users, informed by the evidence the system surfaces.

Users can navigate three modes:
- Mode A: Read a document as provisions, hierarchy preserved
- Mode B: Search across documents by concept or structured filter
- Mode C: Traverse a legal address across time (point-in-time state)

---

## Phase 0 — Foundations ✅ Complete

**Goal:** Define what a provision is, how it will be classified, and how
the system will be built and validated.

Completed:
- Provision definition: Hohfeldian 〈subject, modality, object〉 atomicity
- Ontology design: tag space, controlled vocabulary, baseline doctrine table
- Chunking strategy: sentence/clause level; edge cases resolved empirically
  during implementation, not deferred
- Annotation strategy: model-primary, stratified sample checking
- Scoring geometry: 2D signed ordinal projection (economic × social liberty)
- Constitutional baseline: post-New Deal (economic), current doctrine
  per sub-domain (social)
- IRR protocol: κ ≥ 0.70 on valence; pilot = 15 provisions, prompt
  calibration instrument
- Schema and controlled vocabulary: fully specified (see YAML files)

Artifacts:
- provision_schema.yaml
- controlled_vocabulary.yaml
- baseline_doctrine.yaml
- decisions_log.md (rationale layer)
- Session handoff documents (Sessions 0–4)

---

## Phase 1 — Chunk & Store 🔄 Current

**Goal:** Extract all provisions from the 120-document corpus, store them
with structural metadata, and surface ambiguous chunk boundaries for review.

### Architecture

Layer 2 is split into two sub-stages with a persisted intermediate:

**Layer 2a — Extraction** (source-specific)
One extractor per source schema, each implementing a common interface.
Produces ExtractedUnit records stored in the extracted_units table.
Current extractors needed:
- FRPresdocuExtractor — handles Federal Register PRESDOCU XML
  (EXECORD, PROCLA, PRNOTICE, DETERM subtypes)
- USLMExtractor — handles Congressional USLM XML (bills, resolutions)

New source = new extractor file. Normalizer is never touched.

**Layer 2b — Normalization** (source-agnostic)
Reads extracted_units, applies atomicity test, detects nesting,
constructs context_text, assigns chunk_flag, writes provision records.
Also writes to legal_addresses and provision_references as citations
are identified.

### Database tables added in Phase 1

- extracted_units — persisted intermediate; audit trail between raw
  documents and normalized provisions; reprocessing boundary
- provisions — normalized provision records with structural metadata
- legal_addresses — first-class legal location entities (USC citations,
  CFR sections, EO numbers); enables graph promotion and temporal queries
- provision_references — junction table: provision → legal_address with
  typed edges (amends | references | implements | supersedes | enacts)

doc_status enum extended: raw → extracted → transformed → classified → error

### Tasks

- Write DDL for extracted_units, provisions, legal_addresses,
  provision_references; extend doc_status enum
- Define ExtractedUnit dataclass (policylens/chunker/types.py)
- Define extractor interface (policylens/extractors/base.py)
- Implement FRPresdocuExtractor (policylens/extractors/fr_presdocu.py)
- Implement USLMExtractor (policylens/extractors/uslm.py)
- Implement normalizer (policylens/chunker/normalize.py)
- Wire CLI commands: chunk-extract, chunk-normalize (or combined chunk)
- Apply atomicity test: can this unit be split into two valid
  〈subject, modality, object〉 triples without loss of meaning?
- Detect and encode nested conditionals → condition_stack
- Detect cross-reference objects → provision_references rows
- Construct context_text for each provision (for future embedding)
- Set chunk_flag for provisions requiring human boundary review
- Generate chunking report: total provisions, by doc_type, chunk_flag
  distribution, condition_stack depth distribution, element_type breakdown

### Success criteria

- All 120 documents processed (status = transformed)
- Chunking report reviewed; edge case distribution understood
- No silent omissions (every source element accounted for in at least
  one extracted_unit record or explicit exclusion log)
- context_text populated on all provision records
- All pipeline stages idempotent: safe to re-run without duplication

### Deferred to annotation phase (Phase 3)

modality, object_class, domain, valence, subject_type, baseline_statement

### Deferred temporal fields (nullable in Phase 1; populated as data allows)

effective_date, superseded_by, superseded_date, legal_address_id
(on provisions — the legal_addresses table is created in Phase 1 but
population is opportunistic, not required for Phase 1 completion)

---

## Phase 2 — Front-End: Browse & Search

**Goal:** A working interface that lets users navigate the chunked corpus,
read provision text in context, and search by keyword or structural filter.

Features:
- Mode A: Provision browser — navigate by document → section → provision;
  section headings visible; document title persistent in header
- Full-text search across provision text (existing tsvector on documents;
  add tsvector on provisions.text)
- Structural filters: document type, section, chunk_flag status,
  element_type
- Provision card display: text, section_heading, document title, doc type,
  date, source link (deep link via url + section_id)
- Document-level view: all provisions in reading order, section hierarchy
  preserved
- Flagged provision queue: reviewers can see and resolve chunk_flag items
- Boilerplate provisions visible in document view but visually distinguished;
  excluded from search results by default (toggle available)

Success criteria:
- All stored provisions browsable and searchable
- Chunk_flag queue functional; reviewers can mark flags resolved
- Source deep links functional for all provision types
- No annotation fields visible in UI yet

---

## Phase 3 — Annotation

**Goal:** Populate the normative and scoring fields on all provision records
using a model-primary pipeline with stratified human sample checking.

Tasks:
- Build annotation prompt: full rubric, cross-rules, few-shot examples
  drawn from corpus (8 worked examples + 2 adversarial), baseline doctrine
  table embedded or referenced; context_text used as model input (not
  raw text) so model has full structural context
- Run pilot (15 provisions, two passes): measure model-human κ on valence,
  domain, subject_type, modality
- Tune prompt until κ ≥ 0.70 on valence and κ ≥ 0.80 on domain
- Run model annotation on full corpus
- Stratified sample check: oversample provisions with chunk_flag ≠ clean,
  domain = mixed, condition_stack depth > 0, modality = complex,
  element_type = boilerplate
- Log sample check results; trigger prompt revision if error rate exceeds
  threshold
- Populate pending_monitor on all domain:pending provisions
- Generate annotation report: coverage, κ by dimension, pending count,
  sample check result distribution

Success criteria:
- All non-pending provisions (element_type = provision_candidate) have
  domain, valence, subject_type, modality populated
- Annotation method and annotation_version recorded on every provision
- Pending provisions have pending_reason and pending_monitor populated
- Sample check error rate acceptable (defined at pilot completion)
- boilerplate provisions tagged domain:governmental_structure

---

## Phase 4 — Front-End: Search, Filter & Interact

**Goal:** Extend the front-end with annotation-aware search, filtering,
and visualization. Implements Modes B and C fully.

Features:
- Mode B: Semantic search using vector embeddings on context_text;
  each result card shows text + section_heading + doc title + doc type + date
- Filter by annotation fields: domain, valence range, subject_type, modality
- Provision detail view: all annotation fields, baseline_statement,
  cross-rules cited; provision_references displayed as linked legal addresses
- 2D axis visualization: provisions plotted in economic × social liberty
  space
- Document-level ideological profile: score distribution for selected document
- Comparison view: two documents side by side
- Mode C: Legal address page — all provision versions at a legal_address,
  ordered by effective_date; supersession chain visible
- Pending provision indicator: excluded from visualization with count shown

Success criteria:
- Semantic search functional on context_text embeddings
- All annotation fields searchable and filterable
- 2D visualization correct for single-axis and mixed provisions
- Mode C (temporal traversal) functional for legal addresses with multiple
  provision versions
- Pending exclusion count visible in all visualization views

---

## Phase 5 — Clustering & Analysis

**Goal:** Run the clustering pipeline, validate against party alignment,
and produce exportable analysis outputs.

Tasks:
- Implement 2D projection from provision scores
- Run k-means or hierarchical clustering; determine k empirically
- Post-hoc axis interpretation
- Party alignment validation
- Sensitivity analysis: with and without mixed provisions
- Pending provision analysis: check for systematic distribution
- Export: provision-level scores, document-level profiles, cluster assignments

Success criteria:
- Clusters interpretable and stable across initialization seeds
- Party alignment validation produces legible signal
- Sensitivity analysis completed and documented
- All outputs exportable in machine-readable format

---

## Deferred (No Phase Assigned Yet)

- Four Hohfeldian correlatives: disability, liability, no_right, right_claim
- Graph promotion: typed metadata fields → graph edges (legal_addresses
  and provision_references tables already structured for this)
- Versioning and re-tagging strategy at scale (Dobbs-class doctrine shifts)
- Post-pilot adjudication model for full corpus scale-up
- k-means parameter selection
- Clustering sensitivity analysis (mixed-provision centroid distortion)