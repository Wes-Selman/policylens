# project_plan.md
# PolicyLens — Project Plan
# Last updated: Session 7

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
- Session handoff documents (Sessions 0–7)

---

## Phase 1 — Chunk & Store ✅ Complete (Session 7)

**Goal:** Extract all provisions from the 120-document corpus, store them
with structural metadata, and surface ambiguous chunk boundaries for review.

### Architecture

Layer 2 is split into two sub-stages with a persisted intermediate:

**Layer 2a — Extraction** ✅ Complete (Session 5)
One extractor per source schema, each implementing a common interface.
Produces ExtractedUnit records stored in the extracted_units table.
Dispatch via `policylens/extractors/registry.py`.

Implemented extractors:
- FRPresdocuExtractor — handles Federal Register PRESDOCU XML
  (EXECORD, PROCLA, PRNOTICE, DETERM subtypes)
- USLMExtractor — handles Congressional USLM XML (bills, resolutions)

New source = new extractor file + one line in registry.py. Normalizer
and CLI are never touched.

**Layer 2b — Normalization** ✅ Complete (Session 7)
Source-agnostic normalizer reads extracted_units, applies atomicity
heuristics, detects nested conditionals, constructs context_text, assigns
chunk_flag, detects inline citations, refines jurisdiction, and writes
provision records. Also writes to legal_addresses and provision_references.

Normalizer decisions:
- element_type overrides: provision_candidate → boilerplate (General
  Provisions formulaic language); provision_candidate → header (definition
  block intros)
- Boilerplate child inheritance: child units of a boilerplate parent
  inherit the boilerplate classification
- chunk_flag priority: review_nested_conditional > review_cross_reference
  > review_boundary > clean
- Inline citation detection: both short form (N U.S.C.) and long form
  (section N of title N, United States Code)
- context_text: section_heading when available; section_path label as
  fallback for FR documents
- jurisdiction refinement: involves_states → preempts_state |
  defers_to_state | creates_floor via keyword heuristics

### Database tables added in Phase 1

- extracted_units — persisted intermediate; audit trail between raw
  documents and normalized provisions; reprocessing boundary
- provisions — normalized provision records with structural metadata
- legal_addresses — first-class legal location entities (USC citations,
  CFR sections, EO numbers); enables graph promotion and temporal queries
- provision_references — junction table: provision → legal_address with
  typed edges (amends | references | implements | supersedes | enacts)

doc_status enum extended: raw → extracted → transformed → classified → error

### Final corpus results (Session 7)

- Documents at status='transformed': 120/120
- Total provisions: 943
- By element_type: 682 provision_candidate (bill), 143 provision_candidate
  (resolution), 79 provision_candidate (EO), 30 boilerplate (EO), 9 header
  (bill)
- chunk_flag: clean=474, review_boundary=349, review_cross_reference=120,
  review_nested_conditional=0
- condition_stack: depth-0=862, depth-1=78, depth-2=3, depth-3+=0
- jurisdiction: federal_only=926, creates_floor=8, involves_states=5,
  preempts_state=3, defers_to_state=1
- context_text: 943/943 populated

### Phase 1 completion checklist

- ✅ All 120 documents at status='transformed'
- ✅ Zero documents at status='raw' or 'extracted'
- ✅ context_text populated on all 943 provision records
- ✅ chunk_flag populated on all 943 provision records
- ✅ jurisdiction populated on all 943 provision records
- ✅ Chunking report reviewed; edge case distribution understood
- ✅ All pipeline stages idempotent (verified by re-running on 5 documents)
- ✅ decisions_log.md updated through Session 7
- ⬜ migrate_session7_jurisdiction_backfill.sql committed to repo
  (documents the one-time backfill applied in Session 7; carry-forward
  to Session 8)

---

## Phase 2 — Front-End: Browse & Search

**Goal:** A working interface that lets users navigate the chunked corpus,
read provision text in context, and search by keyword or structural filter.

**Gate:** Requires dedicated security/legal scoping session before this
phase begins. Scope: user data storage, API terms of use (Congress.gov,
Federal Register), advertising data flows, threat model for a civic tech
tool that scores legislation ideologically.

**Phase decomposition required:** "Phase 2" contains multiple distinct
product surfaces that likely belong in separate phases:
- Mode A (document browser) — read-only, no annotation required, ships early
- Mode B (search) — requires pgvector and embedding pipeline
- Mode C (temporal traversal) — requires temporal chain populated
- Ideological visualization — requires Phase 3 annotation coverage
- Legislator profiling / says-vs-does — requires legislator data joins
  (feasibility not yet validated)

The scoping session assigns sub-phase numbers and sequences these explicitly.

Features (pending scoping):
- Mode A: Provision browser — navigate by document → section → provision;
  section headings visible; document title persistent in header
- Full-text search across provision text (existing tsvector on documents;
  add tsvector on provisions.text)
- Structural filters: document type, section, chunk_flag status, element_type
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
- 2D axis visualization: provisions plotted in economic × social liberty space
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
- Refactor db/__init__.py: replace global pool singleton with explicit
  create_pool(dsn) factory (flagged Session 5; needed before Phase 2)
- State legislative ingestion (LegiScan/OpenStates) — separate source
  family, separate baseline_doctrine supplement, separate scoping session;
  jurisdiction field is forward-compatible