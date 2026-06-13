# project_plan.md
# PolicyLens — Project Plan
# Last updated: Session 8

---

## Vision

A civic intelligence platform that gives every person direct access to
what the law actually says — at the provision level, without editorial
interpretation. The foundation is a corpus of federal legislative and
regulatory text parsed into atomic deontic provisions (one subject, one
modality, one object), stored with structural metadata, and made available
through a clean API and a trustworthy reading interface.

In later phases, provisions are labeled with ideological scores and
visualized on a two-axis liberty space, enabling substantive analysis of
how legislation positions itself across economic and social liberty
dimensions. Party alignment is derived from clustering output — never
used as a training label.

The provision-level foundation is designed to support civic accountability
features beyond document browsing, including: ideological profiling of
legislators and parties derived from the text of what they have sponsored
and voted for (not their stated positions); comparison of stated positions
against legislative action ("says vs. does"); and constituent engagement
tools that pre-load specific provisions and vote records as evidence for
contacting a representative. These features are sequenced after the core
annotation pipeline is stable.

Note on normative scoring: PolicyLens scores provisions on liberty axes
anchored to constitutional baselines. This is not an editorial judgment
about whether a provision is good or bad for any group. The product's
strength is that it shows what the law does without taking positions.
Features that would require PolicyLens to evaluate whether legislation
is beneficial for specific populations are out of scope — that judgment
belongs to users, informed by the evidence the system surfaces.

---

## Personas (defined Session 8)

**Persona 1 — The Overwhelmed Citizen**
Somewhere in the middle politically. Finds all available information
overwhelming. Wants a source of truth without bias. Does not do deep
research but wants to trust that someone has. Core problem is trust, not
access. Arrives with a vague topic after seeing something in the news,
has maybe 5 minutes. The editorial neutrality of PolicyLens is the entire
reason they would use it over anything else. Journey is pull, not push.

**Persona 2 — The Data Builder**
Builds on top of the corpus programmatically. Use cases include training
models, building prediction markets, simulating policy scenarios, joining
with external data, gamifying politics, building polls, automating social
content, powering policy newsletters, and constituent engagement tools.
Does not need a UI — needs reliable schema, stable identifiers, good
coverage, and terms of use that permit building on top. The API is their
entry point. The provision ID format, context_text field, and Hohfeldian
structure are the product for them.

**Persona 3 — The Researcher / Journalist**
Formal consumption. Tracks trends over time, informs studies, needs
citeable sources. Needs to trust the methodology, not just the output.
Uses both the UI and the API. Needs methodology disclosure rigorous enough
to reference in a footnote or a published study.

**Key relationship:** Persona 1 is an end user of what Persona 2 could
build on top of PolicyLens. PolicyLens building the Persona 1 UI directly
does not create debt for Persona 2 — as long as the API is the contract
and the UI is a consumer of it. The UI is also proof that the API works.

---

## Architectural principle: API-first (decided Session 8)

PolicyLens is a product, not purely a platform — but built API-first so
the UI is the first client of the API, not the other way around.

The API is the contract. The UI is a consumer of it. No UI decision drives
the data model. This means:
- Persona 2 builders can integrate against the API without being affected
  by UI changes.
- The reading experience can be redesigned, replaced, or extended without
  touching the corpus, the schema, or the provision identifiers.
- The Persona 1 UI is the proof that the API works, and provides the
  tangibility signal useful for early product development and attracting
  builders.

Technology decisions follow from user journey requirements. User journeys
are designed before technology is selected.

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
- Session handoff documents (Sessions 0–8)

---

## Phase 1 — Chunk & Store ✅ Complete (Session 7)

**Goal:** Extract all provisions from the seed corpus, store them with
structural metadata, and surface ambiguous chunk boundaries for review.

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
- ✅ migrate_session7_jurisdiction_backfill.sql committed (Session 9)

---

## Phase 2 — Pipeline Hardening + Corpus Expansion + Lightweight UI

**Goal:** Make the existing corpus trustworthy, expand it to meaningful
coverage, and ship a lightweight reading experience that proves the API
works and gives Persona 1 something real to use.

**Framing:** Phase 2 has three parallel workstreams with a clear dependency
order. The UI does not ship to real users until 2a is complete and 2b has
meaningful topic coverage. All three workstreams are built in parallel;
the dependency is on launch, not on build.

### Workstream 2a — chunk-resolve pipeline stage

**The problem:** 469 of 943 provisions (50%) carry chunk_flag ≠ 'clean'.
The normalizer flagged these correctly — the machinery worked as designed.
But an unresolved flag queue means the corpus is not yet trustworthy enough
to be the source of truth that Persona 1's value proposition requires.

**Resolution strategy — deterministic first, LLM agent on residual:**

Layer 1 — Deterministic fixes (implemented as a new `chunk-resolve`
pipeline stage, runs after `chunk-normalize`):

  Em-dash stubs (review_boundary): The USLM XML structure is known. The
  stub always has child nodes containing the operative content. Deterministic
  merger: concatenate the stub with its immediate children in order.
  Structural fix, no model needed.

  Bare noun phrase fragments (review_boundary): Walk up section_path until
  a unit with a finite verb and modality is found. Attach fragment as a
  list item under that parent. USLM nesting makes this traversal
  well-defined. Structural fix, no model needed.

  Inline cross-references (review_cross_reference): These are not chunking
  problems — the provision text is correctly bounded. Resolution is
  reference extraction: parse the USC citation, upsert to legal_addresses,
  insert provision_references junction record. Flag clears when reference
  is resolved. Deterministic extraction task.

Layer 2 — LLM agent pass: Whatever remains genuinely ambiguous after
deterministic fixes is the correct input for an LLM agent review pass.
This residual set is expected to be small. This is chunk boundary
validation, not annotation work (Phase 3).

**Output:** Corpus where chunk_flag='clean' is genuinely earned.

**Implementation note:** Design the deterministic merge pass before writing
any code. Inspect the actual flagged provisions in the DB to confirm merge
heuristics are correct before implementing. Empirical grounding first —
same sequencing discipline as the Session 7 atomicity heuristic.

**doc_status:** A new status value `resolved` may be needed between
`transformed` and `classified` to distinguish provisions that have passed
the chunk-resolve stage. Decide at implementation time.

### Workstream 2b — Corpus expansion

**Decision: ingest everything.**

Full Federal Register PRESDOCU back catalog (all executive orders, notices,
proclamations, determinations going back decades) and full Congressional
USLM back catalog (all bills and resolutions from the 93rd Congress onward).
Both sources are already wired. No new extractors required.

**Rationale:**
- API rate limits are an engineering throttle, not a scope constraint.
- Storage cost is negligible.
- Full back catalog makes the temporal chain meaningful — legal address
  evolution across administrations becomes queryable.
- Full coverage is what makes RAG and agent use cases genuinely valuable.
  context_text was designed for embedding stability; no rethinking needed.
- The major policy domains Persona 1 arrives with (immigration, healthcare,
  taxation, education, firearms) need meaningful result sets before the
  UI is useful. Full coverage achieves this.

**Sequencing constraint:** Run after chunk-resolve is proven stable at the
120-document scale. Stress test at ~500 documents before opening the
throttle to the full back catalog. This surfaces extractor edge cases
that did not appear at 120 documents before they multiply.

### Workstream 2c — Lightweight UI

A search and provision reading experience. Built as a clean consumer of
the API — no UI decision drives the data model. Can be built in parallel
with 2a and 2b but does not ship to real users until 2a is complete and
2b has meaningful topic coverage in the major policy domains.

**Launch threshold:** Not a document count. Coverage of the major policy
domains Persona 1 arrives with: immigration, healthcare, taxation,
education, firearms. Search on any of those topics must return a
meaningful, trustworthy result set.

**UI design principles:**
- Editorial neutrality is the trust signal. No commentary, no spin.
  Direct provision text with source links to the government document.
- The absence of provisions (proclamations, ceremonial resolutions) is
  displayed transparently as informative, not as a failure state.
- Boilerplate provisions are visible in document reading view but visually
  distinguished; excluded from search results by default.
- Methodology disclosure is load-bearing for Persona 1 trust and Persona 3
  citability. A public methodology page is required at launch.

**Technology decisions:** Resolved in Session 9, after Persona 1 user
journey is mapped. Technology serves the user experience, not the reverse.

**Prerequisites before Phase 2c ships:**
- db/__init__.py singleton refactor: replace global pool with explicit
  create_pool(dsn) factory (flagged Session 5; required for web tier
  concurrency)
- Security and legal review: API terms of use (Congress.gov, Federal
  Register), user data storage, advertising data flows, threat model
- User journey mapping for Persona 1 (Session 9 agenda item 1)

**Success criteria for Phase 2:**
- All provisions at chunk_flag='clean' after chunk-resolve pass
- Full Federal Register PRESDOCU and Congressional USLM back catalogs
  ingested and normalized
- Major policy domain topic coverage confirmed via search result sampling
- Lightweight UI live with search and provision reading experience
- API documented and accessible to Persona 2 builders
- Methodology page live

---

## Phase 3 — Annotation Pipeline

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

## Phase 4 — Semantic Search

**Goal:** Add vector search on context_text embeddings. Significant
infrastructure addition — its own phase.

Tasks:
- Install pgvector extension
- Select embedding model
- Run embedding job on context_text for all provisions
- Implement vector similarity search endpoint
- Surface semantic search in UI

**Note:** context_text was designed for embedding stability from the start.
No schema changes required. Expanding the corpus in Phase 2 does not
require rethinking the embedding strategy — context_text is already
designed for it.

---

## Phase 5 — Annotation-Aware Filtering + Ideological Visualization

**Goal:** Extend the UI with annotation-aware search, filtering, and the
2D liberty-space visualization. Requires Phase 3 complete.

Features:
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
- All annotation fields searchable and filterable
- 2D visualization correct for single-axis and mixed provisions
- Mode C functional for legal addresses with multiple provision versions
- Pending exclusion count visible in all visualization views

---

## Phase 6 — Clustering and Analysis

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

- Temporal traversal (Mode C display) — opportunistic; populate
  effective_date / superseded_by as data allows; surface in UI when
  chains exist; not its own phase
- Legislator profiling / says-vs-does — House roll call votes available
  via Congress.gov API beta (118th Congress onward); Senate requires
  separate source; sequence after Phase 3; House-only at launch acceptable;
  feasibility partially validated Session 8
- State legislative ingestion (LegiScan/OpenStates) — separate source
  family, separate baseline_doctrine supplement, separate scoping session;
  jurisdiction field is forward-compatible
- Four Hohfeldian correlatives: disability, liability, no_right, right_claim
  — second annotation pass, derivable from primary set
- Graph promotion: typed metadata fields → graph edges (legal_addresses
  and provision_references tables already structured for this)
- Versioning and re-tagging strategy at scale (Dobbs-class doctrine shifts)
- Post-pilot adjudication model for full corpus scale-up
- k-means parameter selection
- Clustering sensitivity analysis (mixed-provision centroid distortion)
- Constituent support / dissension at provision level — integrity challenges
  (fraud prevention, identity verification) significant; noted to preserve
  the option without committing