# project_plan.md
# PolicyLens — Project Plan
# Last updated: Session 3

---

## Vision

A fully functional front-end that allows users to search, browse, and
interact with legislative and regulatory text chunked to the provision
level — where each provision is the minimal deontic unit (one subject,
one modality, one object). In later phases, provisions are labeled with
ideological scores and visualized on a two-axis liberty space, enabling
substantive analysis of how legislation positions itself across economic
and social liberty dimensions.

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

Tasks:
- Implement chunker at sentence/clause level
- Apply atomicity test: can this unit be split into two valid
  〈subject, modality, object〉 triples without loss of meaning?
  If yes, split. If no, it is a single provision.
- Populate structural fields on each provision record:
  id, doc_id, section_id, provision_index, text, doc_type
- Detect and encode nested conditionals → condition_stack
- Detect cross-reference objects → object_ref
- Set chunk_flag for any provision requiring human boundary review
- Store all provisions in the database
- Generate chunking report: total provisions, provisions by doc_type,
  chunk_flag distribution, condition_stack depth distribution

Success criteria:
- All 120 documents processed
- Chunking report reviewed; edge case distribution understood
- No silent omissions (every source sentence accounted for in at least
  one provision record or an explicit exclusion log)

Deferred to annotation phase (Phase 3):
- modality, object_class, domain, valence, subject_type, baseline_statement

---

## Phase 2 — Front-End: Browse & Search

**Goal:** A working interface that lets users navigate the chunked corpus,
read provision text in context, and search by keyword or structural filter.

Features:
- Provision browser: navigate by document → section → provision
- Full-text search across provision text
- Structural filters: document type, section, chunk_flag status
- Provision record display: text, source document, section reference,
  condition_stack (if any), object_ref (if any), chunk_flag
- Document-level view: all provisions in a document, reading order
  preserved
- Flagged provision queue: reviewers can see and resolve chunk_flag items

Success criteria:
- All stored provisions browsable and searchable
- Chunk_flag queue functional; reviewers can mark flags resolved
- No annotation fields visible in the UI yet (annotation phase is separate)

---

## Phase 3 — Annotation

**Goal:** Populate the normative and scoring fields on all provision records
using a model-primary pipeline with stratified human sample checking.

Tasks:
- Build annotation prompt: full rubric, cross-rules, few-shot examples
  drawn from corpus (8 worked examples + 2 adversarial), baseline doctrine
  table embedded or referenced
- Run pilot (15 provisions, two passes): measure model-human κ on valence,
  domain, subject_type, modality
- Tune prompt until κ ≥ 0.70 on valence and κ ≥ 0.80 on domain
- Run model annotation on full corpus
- Stratified sample check: oversample provisions with chunk_flag ≠ clean,
  domain = mixed, condition_stack depth > 0, modality = complex
- Log sample check results; trigger prompt revision if error rate exceeds
  threshold
- Populate pending_monitor on all domain:pending provisions
- Generate annotation report: coverage, κ by dimension, pending count,
  sample check result distribution

Success criteria:
- All non-pending provisions have domain, valence, subject_type, modality
  populated
- Annotation method and annotation_version recorded on every provision
- Pending provisions have pending_reason and pending_monitor populated
- Sample check error rate acceptable (defined at pilot completion)

---

## Phase 4 — Front-End: Search, Filter & Interact

**Goal:** Extend the front-end with annotation-aware search, filtering,
and visualization so users can interact with the ideological structure
of the corpus.

Features:
- Filter by annotation fields: domain, valence range, subject_type,
  modality
- Provision detail view: all annotation fields visible, baseline_statement
  displayed, cross-rules cited
- 2D axis visualization: provisions plotted in economic × social liberty
  space (valence_economic on x-axis, valence_social on y-axis)
- Document-level ideological profile: distribution of provision scores
  for a selected document
- Comparison view: two documents side by side, score distributions compared
- Pending provision indicator: domain:pending provisions visually flagged,
  excluded from visualization with count shown
- Chunk_flag review integrated: reviewers can update annotations inline

Success criteria:
- All annotation fields searchable and filterable
- 2D visualization renders correctly for single-axis and mixed provisions
- Document comparison functional for any two documents in the corpus
- Pending exclusion count visible in all visualization views

---

## Phase 5 — Clustering & Analysis

**Goal:** Run the clustering pipeline, validate against party alignment,
and produce exportable analysis outputs.

Tasks:
- Implement 2D projection from provision scores
- Run k-means or hierarchical clustering; determine k empirically
- Post-hoc axis interpretation: label axes based on cluster composition
- Party alignment validation: compare cluster membership to known party
  affiliation of sponsoring legislators
- Sensitivity analysis: run clustering with and without mixed provisions;
  measure centroid shift
- Pending provision analysis: check whether pending exclusions are
  systematically distributed
- Export: provision-level scores, document-level profiles, cluster
  assignments

Deferred items (not Phase 5):
- Four Hohfeldian correlatives (second annotation pass)
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale

Success criteria:
- Clusters are interpretable and stable across initialization seeds
- Party alignment validation produces a legible signal (not necessarily
  clean — ambiguity is a valid finding)
- Sensitivity analysis completed and documented
- All outputs exportable in machine-readable format

---

## Deferred (No Phase Assigned Yet)

- Four Hohfeldian correlatives: disability, liability, no_right, right_claim
  (second annotation pass; derivable from primary set)
- Graph promotion: typed metadata fields → graph edges
- Versioning and re-tagging strategy at scale (Dobbs-class doctrine shifts)
- Post-pilot adjudication model for full corpus scale-up