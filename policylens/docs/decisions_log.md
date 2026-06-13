# decisions_log.md
# PolicyLens — Decisions Log (Rationale Layer)
#
# This document records WHY the ontology is structured the way it is.
# It is separate from the session handoff (which is operational) and from
# the YAML schema files (which record what the structure is).
# Intended audience: anyone who inherits this project and needs to understand
# a design choice, or anyone reconsidering a decision.

---

## Provision Definition

**Decision:** A provision is a single deontic proposition of the form
〈subject, modality, object〉.

**Why not sentence or clause?**
Drafting conventions do not track legal meaning. A single sentence in
legislative text can contain two or three independent legal obligations
with different subjects and different modalities. A single clause can be
a fragment of one obligation. Syntactic units produce inconsistent chunk
boundaries that are drafting-style artifacts, not legal-meaning artifacts.

**Why Hohfeld?**
Hohfeld's 1913 framework is the standard formal vocabulary for legal
relations in jurisprudence. It gives the chunker an implementable rule
(what is the modality? who is the subject? what is the object?) and it
maps directly to what the ontology's normative layer is designed to
classify. No bespoke theory was needed.

**Why not finer than atomic triples?**
Going finer destroys the legal meaning of joint obligations and conditioned
permissions. A duty to do X if Y has occurred is one legal operation, not
two. Splitting it loses the conditionality that defines the duty.

---

## Top-Level Structure: Taxonomy, Not Graph

**Decision:** Multi-dimensional tagging taxonomy, graph-promotable.
Graph edges are metadata fields, not actual edges, in the initial
implementation.

**Why not start with a graph?**
Graph embedding requires machinery (graph neural networks, or explicit
relational queries) that adds complexity and assumptions before the core
ontology has been validated on real corpus data. The taxonomy is
implementable immediately and compatible with vector embedding for
clustering. The relational information is preserved in typed metadata
fields and can be promoted to graph edges post-validation.

**Why not a flat taxonomy?**
The provisions have multiple independent analytical dimensions —
structural, normative, topical, rights-based. Flattening them into a
single dimension produces categories that are not mutually exclusive and
forces false classification. Multi-dimensional tagging lets each
dimension be developed and validated independently.

---

## Clustering Mechanism: DW-NOMINATE Geometry, CMP Scoring

**Decision:** Signed ordinal scoring → 2D geometric projection → clustering,
with party alignment as post-hoc validation.

**What was borrowed from DW-NOMINATE:**
Two-axis geometry. Party affiliation as a validation signal rather than
a training label. Post-hoc axis interpretation (you label the axes after
seeing where clusters fall, not before).

**What was discarded from DW-NOMINATE:**
The cutting-plane / revealed-preference framework. That framework requires
roll-call vote data — legislators revealing preferences through votes.
PolicyLens works from statutory text, not votes. The framework does not
transfer.

**What was borrowed from CMP (Comparative Manifesto Project):**
Signed category scoring. Provision-as-unit of analysis.
Position-as-weighted-distribution (a document's ideological position
is a function of the distribution of its provision scores, not a single
label).

**What was discarded from CMP:**
Topic-semantic categories. CMP categories are defined by subject matter
(welfare, environment, law and order). Those categories conflate what
a provision is about with what it does to liberty. A welfare provision
can expand or contract liberty depending on how it is structured.
Deontic categories (Hohfeld) replace topic-semantic categories.

**Why signed ordinal (−2 to +2) rather than binary or continuous?**
Binary (expand / contract) loses intensity information that is meaningful
for axis placement. Continuous scoring exceeds inter-rater reliability
for human annotators and introduces false precision in model output.
Signed ordinal is the coarsest scale that preserves intensity while
remaining reliably scorable.

---

## Constitutional Baseline Choice

**Decision:**
- Economic axis: Post-New Deal baseline (West Coast Hotel, 1937).
- Social axis: Current doctrine as of corpus collection date, per sub-domain.

**Why post-New Deal for economic?**
This is the operational legal baseline that courts and legislators use
when drafting. Using a pre-Lochner baseline would sign-flip most of the
corpus (regulations that currently score as contractions would score as
expansions relative to a Lochner baseline where freedom of contract was
the default). That reduces discriminative power and produces ideologically
incoherent clusters.

**Why current doctrine for social?**
The social axis has no equivalent foundational settlement date. Doctrine
has shifted significantly across sub-domains (Dobbs for abortion, Kennedy
for establishment clause, Carpenter for digital surveillance). A single
cutoff date would either miss major shifts or use a baseline that does not
reflect what legislators are actually working against. Per-sub-domain
doctrine entries with version dates handle this more accurately.

---

## Dual-Axis Provisions: Option B (Dual Fields, Single Record)

**Decision:** Mixed provisions carry valence_economic and valence_social
as separate fields on a single provision record. Not split into two records.

**Why not split (Option A)?**
Splitting a mixed provision into two records creates phantom duplication
in document-level provision counts. It breaks traceability: a provision
that simultaneously expands economic liberty and contracts social liberty
carries substantive meaning in that dependency. Splitting loses it.

**Why Option B does not break the projection geometry:**
A mixed provision with (valence_economic, valence_social) is simply a
fully specified point in 2D projection space. Single-axis provisions
project as (valence, 0) or (0, valence) — the zero is structural, not
a scored neutral. The k-means algorithm treats them identically.

**Known limitation:**
k-means treats the two valence dimensions as independent. The dependency
between valence_economic and valence_social on a mixed provision is
preserved in the record but not used in the initial clustering. If the
independence assumption fails, this needs to be revisited.

---

## Agency-Delegated Provisions: domain:pending

**Decision:** Provisions that delegate to agency rulemaking are tagged
domain:pending until the final rule is published. Excluded from clustering
runs, included in corpus statistics. Never silently omitted.

**Why not tag at NPRM stage?**
A proposed rule does not have legal effect. Annotating on the basis of
an NPRM could produce tags that are invalidated when the final rule
differs. More importantly, NPRM-based tags would need to be re-tagged
anyway, creating double work.

**Why include in corpus statistics but exclude from clustering?**
Including in statistics preserves the accurate provision count for
structural analysis (how many provisions per document, per document type).
Excluding from clustering prevents distortion of ideological scores by
provisions whose axis placement is genuinely unknown.

**Why must pending exclusion counts be reported in every clustering run?**
Silent omission is the primary failure mode in corpus analysis pipelines.
Mandatory reporting forces the analyst to evaluate whether the pending
exclusions are systematically distributed (e.g. concentrated in one
document type) in a way that would bias the clustering.

---

## Cross-Reference Provisions: Reference as Object

**Decision:** The cross-reference itself is the object specification.
External definitions are metadata, not inline expansion.

**Why not inline the external definition?**
Inlining makes provision boundaries corpus-dependent. If the external
statute is amended, the inlined definition changes and the provision's
object changes retroactively. The provision's legal operation is defined
by the reference; interpretation of what that reference means is a
separate analytical layer.

---

## Nested Conditional Rule: 2-Layer Collapse

**Decision:** Collapse up to 2 conditional layers into a single provision
with a condition_stack. Split at 3+ layers or when a new subject or
modality is introduced.

**Why 2 layers as the threshold?**
In legislative drafting, a 2-layer conditional ("if A, then if B, then
subject must do X") almost always represents a single duty with a compound
antecedent — the subject, modality, and object are stable throughout.
A 3-layer conditional almost always introduces an intermediate legal
operation (an agency power that triggers a downstream duty, for example),
which is a genuine provision split, not a scope qualification.
The 2-layer rule captures the empirical reality of drafting practice.

---

## Annotation Strategy: Model-Primary, Stratified Sample Check

**Decision:** Model does primary annotation. Human annotators sample-check,
with stratified sampling that oversamples structurally complex and
domain-ambiguous provisions.

**Why model-primary?**
The corpus is large. Human annotation at full corpus scale is expensive
and slow. Model annotation with human oversight is the practical path
to full coverage.

**Why stratified, not random, sampling?**
Random sampling will mostly surface the easy provisions the model annotates
correctly. Hard provisions — nested conditionals, mixed domain, government-
duty Cross-rule A cases — are rare in the corpus but are exactly where
model errors are most consequential for axis placement. Stratified sampling
concentrates human effort where error risk is highest.

**What the IRR protocol measures in this context:**
Not inter-annotator agreement (the traditional use), but model-human
agreement. The κ framework still applies. The pilot (15 provisions,
two passes) serves as prompt calibration: run a sample, check model
output against human judgment, tune the prompt, repeat until κ ≥ 0.70
on valence.

---

## condition_stack Schema: Structured Objects

**Decision:** condition_stack entries are structured objects
{condition_type, text}, not plain strings.

**Why structured?**
Plain strings would allow condition content to be stored and displayed
but not queried by condition type. Structured objects allow later analysis
of whether temporal conditions, existence conditions, and threshold
conditions cluster differently in the ideological space — a question that
may be worth asking once the corpus is annotated. The marginal complexity
of adding condition_type at schema-definition time is low; retrofitting
it onto 120 annotated documents is expensive.

---

## Session 4: Pipeline Architecture — Extractor/Normalizer Split

**Decision:** Layer 2 is split into two sub-stages:
- Layer 2a: Extractor — source-schema-specific, produces ExtractedUnit records
- Layer 2b: Normalizer — source-agnostic, produces provision records from
  ExtractedUnit records

**Why split rather than a single chunker?**
The corpus already contains two distinct XML schemas (FR PRESDOCU and
Congressional USLM). Future sources (eCFR, state legislatures, historical
Congress pre-USLM, court opinions) will add more. A monolithic chunker
with format-specific branches requires surgery on shared code for every
new source. The split means a new source = a new extractor file that
implements a common interface. The normalizer is never touched.

**Why not collapse to a single parser-per-source with no shared normalizer?**
The normalization logic — atomicity test, condition_stack detection,
chunk_flag assignment, context_text construction, temporal field
population — is source-agnostic. Duplicating it across per-source parsers
creates divergence risk and makes rubric changes expensive (N files to
update instead of one).

---

## Session 4: ExtractedUnit as Persisted Intermediate

**Decision:** ExtractedUnit records are stored in an extracted_units table,
not held in memory and discarded after normalization.

**Why persist?**
Three reasons: (1) Reprocessing isolation — if the normalizer logic
changes (new chunk_flag heuristic, new boilerplate detection rule), the
extractor does not need to re-run; the normalizer re-processes from stored
extracted_units. (2) Debugging — when a provision has a bad boundary,
the extracted_unit record shows exactly what the extractor produced before
normalization decisions were applied. (3) Lineage — the extracted_unit_id
FK on provisions completes the chain: provision → extracted_unit → document
→ raw API response.

**Storage cost?**
Negligible. At 120 documents averaging ~10k chars each, the full
extracted_units table is well under 10MB. At 10k documents it remains
under 1GB — trivial for Postgres.

---

## Session 4: LegalAddress as First-Class Entity

**Decision:** legal_addresses is a standalone table. object_ref (the
embedded JSON struct from Sessions 0–3) is replaced by a provision_references
junction table with a ref_type column.

**Why not keep object_ref as an embedded struct?**
The embedded struct buries LegalAddress as a blob. Every unique (statute,
section) pair that appears across provisions is a separate blob with no
shared identity. This means: (a) you cannot query "all provisions that
reference 26 U.S.C. § 7701" without a JSON text search; (b) graph
promotion requires a migration to extract the blobs into nodes; (c) there
is no deduplication — the same legal address appears N times as N separate
blobs.

**Why a junction table with ref_type?**
A provision can stand in multiple relationships to legal addresses:
it may AMEND one section, REFERENCE another as a definition, and
IMPLEMENT a third as its statutory authority. A junction table with
ref_type captures all of these as typed edges, which are the natural
representation in both relational and graph models. Graph promotion
becomes a query or materialized view, not a migration.

**ref_type values:** amends | references | implements | supersedes | enacts

---

## Session 4: context_text Field

**Decision:** Each provision record stores a context_text field
constructed by the normalizer at storage time. This is the input to
vector embedding for semantic search, not the raw provision text.

**Why not embed raw text?**
Many provisions are uninterpretable in isolation. "The Secretary shall
ensure compliance with subsection (a)(2)(B)" embedded as a vector carries
no useful semantic signal without knowing which Secretary, which document,
and what subsection (a)(2)(B) says. The embedding should be on a string
that includes enough context for the vector to carry meaning.

**What goes into context_text?**
Document title, doc type, section heading, condition_stack summary (if
any), and provision text. Example:
  "[Executive Order 14407 — Sec. 2: Updating the Childhood Vaccine Schedule]
   Text: The CDC and ACIP shall review the scientific assessment..."

**Why store it rather than generate at embedding time?**
Storing it makes the embedding input auditable and stable. If context_text
is generated on-the-fly at embedding time, embedding quality depends on
whatever generation logic runs at that moment — a silent source of
embedding drift. Stored context_text is versioned implicitly by the
provision record's update timestamp.

**When does context_text change?**
When structural metadata changes (section heading renamed, document title
corrected). It does not change when annotation fields change. This means
embeddings remain valid across annotation passes, which is the common
case.

**Corpus expansion note (Session 8):** Expanding the corpus to the full
Federal Register and Congressional back catalogs does not require
rethinking the embedding strategy. context_text was designed for stability
from the start. Full corpus coverage makes RAG and agent use cases
qualitatively more valuable — a RAG query can retrieve provisions across
the full legislative history, and an agent can traverse the temporal
chain via superseded_by across real version history.

---

## Session 4: Temporal Fields (effective_date, superseded_by)

**Decision:** Four temporal fields added to provisions, all nullable:
legal_address_id, effective_date, superseded_by (self-referential FK),
superseded_date.

**Why now rather than when temporal navigation is implemented?**
Schema migrations on a populated provisions table are expensive. Adding
nullable columns now costs nothing and preserves the option to populate
them incrementally as data supports it. The alternative — adding them
later — requires a migration after potentially thousands of provisions
are stored, plus a backfill pass.

**What does the version chain look like?**
Each provision record represents one version of a legal text at a legal
address. superseded_by points to the provision record that replaced it.
effective_date and superseded_date define the window during which that
version was operative. Point-in-time queries are: SELECT * FROM provisions
WHERE legal_address_id = X AND effective_date <= :date AND
(superseded_date IS NULL OR superseded_date > :date).

**When are these fields populated?**
Not in Phase 1. They are populated as temporal data becomes available —
either from document metadata (FR publication dates, enactment dates)
or from explicit amendment tracking in later corpus expansion.

---

## Session 4: Boilerplate Classification

**Decision:** Two categories of non-substantive text, handled differently.

Preamble ("By the authority vested in me..."): tagged element_type:preamble
by the extractor. Not stored as a provision record. Retained in
extracted_units and available for context_text construction for sibling
provisions in the same document.

General Provisions boilerplate (EO Sec. 3: "This order is not intended to
create any right or benefit..."): tagged element_type:boilerplate by the
normalizer. Stored as a provision record. Tagged domain:governmental_structure
at annotation. Excluded from ideological clustering. Visible in
document-reading UX (Mode A) but excluded from search and temporal
traversal (Modes B and C).

**Why the asymmetry?**
Preamble is not a provision — it has no deontic content. Storing it as a
provision record would inflate provision counts and introduce zero-content
records into the annotation pipeline. General Provisions boilerplate IS
a provision (it assigns immunities and limitations) — it just happens to
be formulaic. Stripping it would silently omit real legal content.
Classification, not omission.

**Why does boilerplate detection belong to the normalizer, not the extractor?**
What counts as boilerplate is a semantic judgment about legal content, not
a structural observation about XML tags. The extractor sees structure; the
normalizer sees meaning. Keeping semantic judgments in the normalizer
means the extractor can be swapped without re-litigating boilerplate rules.

---

## Session 4: doc_status Enum Extension

**Decision:** Add 'extracted' as an intermediate status between 'raw'
and 'transformed' in the doc_status enum.

**Status flow:**
raw → extracted → transformed → classified → error

raw:         Layer 1 complete; document in documents table; no extracted_units
extracted:   Layer 2a complete; extracted_units populated; provisions not yet written
transformed: Layer 2b complete; provisions populated; annotation fields empty
classified:  Layer 3 complete; annotation fields populated

**Why a separate 'extracted' status?**
Without it, a document that has been extracted but not yet normalized has
no distinguishable status. If the normalizer crashes mid-run, there is no
way to identify documents that need normalization without re-running
extraction. The 'extracted' status makes the reprocessing boundary
explicit and idempotent re-runs safe.

---

## Session 4: Pipeline Idempotency

**Decision:** Every pipeline stage must be safely re-runnable against
documents already at the target status. Re-running is a no-op or a safe
overwrite, never a duplication or corruption.

**Implementation requirements:**
- extracted_units: UNIQUE constraint on (doc_id, source_element_id);
  INSERT ... ON CONFLICT DO NOTHING or DO UPDATE
- provisions: UNIQUE constraint on (doc_id, section_id, provision_index);
  INSERT ... ON CONFLICT DO NOTHING or DO UPDATE
- provision_references: UNIQUE constraint on (provision_id, legal_address_id,
  ref_type); INSERT ... ON CONFLICT DO NOTHING
- legal_addresses: UNIQUE constraint on (statute, section);
  INSERT ... ON CONFLICT DO NOTHING, return existing id

**Why?**
Pipelines fail. Network errors, process kills, schema bugs. An idempotent
pipeline can be re-run from any checkpoint without manual cleanup. This
is especially important once the corpus grows beyond 120 documents where
manual recovery becomes infeasible.

---

## Session 5: Extractor Dispatch Registry

**Decision:** Extractor dispatch lives in `policylens/extractors/registry.py`
as a standalone module, not inline in `cli.py`.

**Why a separate registry module?**
Putting dispatch logic in `cli.py` creates a hard dependency: testing
dispatch requires importing the full CLI, which pulls in the DB connection
pool and API clients. With a standalone registry, dispatch tests run
without a database or API keys — the registry module has no such
dependencies. This is the standard plugin registry pattern (Open/Closed
Principle): the system is open to extension (new source = new extractor
file + one line in registry.py) but closed to modification (cli.py and
normalize.py are never touched when sources are added).

**How to add a new source:**
1. Create `policylens/extractors/new_source.py` implementing `BaseExtractor`.
2. Add one line to `registry.py`: `register("new_source", NewSourceExtractor)`.
Done. No other files change.

---

## Session 5: Deferred psycopg Import in db/__init__.py

**Decision:** The `psycopg_pool` import in `db/__init__.py` is deferred
inside `get_pool()` rather than executed at module load time.

**Why defer?**
The original implementation imported `ConnectionPool` at module load, which
required libpq (the PostgreSQL client library) to be present at import time.
This made any test that imported from `policylens.db.*` fail in environments
without a database client installed. Deferring the import to `get_pool()`
means the module can be imported freely; the DB dependency is only
instantiated when a connection is actually requested.

**Known limitation:**
This is a workaround for a deeper smell: `get_pool()` maintains a global
singleton `_pool`, which is a concurrency hazard in any async context and
makes dependency injection in tests unnecessarily indirect. The cleaner
long-term solution is an explicit `create_pool(dsn)` factory instantiated
by the CLI entry point, with the pool passed down explicitly. This must
be addressed before Phase 2 when the front-end introduces its own lifecycle
management needs. It is the first backend task of Phase 2.

---

## Session 5: element_type Assignment Boundary

**Decision:** Extractors may only assign `element_type` values from the set
`{provision_candidate, preamble, header}`. The value `boilerplate` may only
be assigned by the normalizer.

**Why enforce this at the type level?**
Boilerplate detection is a semantic judgment (does this text have deontic
content?), not a structural observation (is this element inside a `<PROCLA>`
tag?). Extractors only see XML structure; they cannot reliably make semantic
judgments. If an extractor assigned `boilerplate`, swapping the extractor
for a new version would require re-litigating boilerplate rules in the new
extractor — defeating the purpose of the normalizer having sole
responsibility. The `EXTRACTOR_ELEMENT_TYPES` frozenset in `types.py` and
the `validate()` method enforce this boundary programmatically, catching
violations before they reach the database.

---

## Session 5: Provision ID Separator

**Decision:** The provision primary key format is
`{doc_id}|{section_id}|{provision_index}`. Pipe character (`|`) used as
separator, not colon.

**Why not colon?**
Section IDs derived from legislative text can contain colons (e.g.
`Sec. 3: General Provisions` or citation-style references). A colon
separator would make the ID ambiguous to parse. Pipe is not a character
that appears in legislative section notation.

---

## Session 5: Proclamations Produce Zero Provisions (Expected)

**Observation from corpus run:** All 8 presidential proclamations in the
corpus extracted as preamble-only (118 preamble units, 0 provision_candidate
units for fr_presdocu as a whole — with the 109 provision_candidates coming
entirely from EOs and notices).

**Decision:** This is correct behavior, not a bug. No normalizer adjustment
required for proclamations.

**Why proclamations have no provisions:**
A provision is defined as a deontic proposition — a statement that assigns
a duty, permission, power, or immunity to a subject. Proclamations are
declaratory speech acts: "I hereby proclaim May 8 as Victory Day for World
War II." This sentence does not obligate or empower anyone. It performs a
declaration. There is no 〈subject, modality, object〉 triple to extract
because there is no modality — no one is being told to do anything, permitted
to do anything, or given any power or immunity.

**User-facing implication:**
In the document reading UX, a user navigating to a proclamation will see
the full text displayed as context/preamble with a clear indication that no
deontic provisions were identified. This is informative, not a failure state.
It correctly communicates something about the nature of the document that a
user might not otherwise know: proclamations are ceremonial and declaratory;
executive orders are directive. The distinction is meaningful to anyone
trying to understand what the President's office actually did versus what it
announced.

**What this means for corpus statistics:**
When reporting provision counts, the proclamation zero-provision outcome
must be explicitly noted, not silently omitted.

---

## Session 5: Bare Noun Phrase List Items (Corpus Inspection Finding)

**Observation:** Corpus inspection of depth-6 USLM extracted_units (bill
119-S-23) revealed units whose entire raw_text is a bare noun phrase —
e.g. "the Defense Intelligence Agency;" — with no finite verb, no
modality marker, and no self-contained legal meaning.

**Decision (Session 5):** Flag as chunk_flag = 'review_boundary'. No
auto-merge.

**Decision revised (Session 8):** The "no auto-merge" decision is reversed.
Deterministic merge is the correct resolution. See Session 8: chunk-resolve
Pipeline Stage below. The Session 5 decision was made before the full
chunk_flag picture was known; the Session 8 revision is grounded in the
complete corpus result (349 review_boundary flags, 50% of total).

---

## Session 6b: Jurisdiction Scope Field

**Decision:** Add a `jurisdiction` field to provisions and a coarse
`jurisdiction_scope` signal to `ExtractedUnit`. The extractor sets
`jurisdiction_scope` ('federal_only' | 'involves_states' | 'unknown');
the normalizer refines 'involves_states' into the full provision-level
enum ('preempts_state' | 'defers_to_state' | 'creates_floor' | 'involves_states').

**Why add this now (before Session 6 normalization)?**
The field must exist on `ExtractedUnit` before extractors run so that
the normalizer has the coarse signal available without re-extraction.
Adding it after extraction would require a full re-run of Layer 2a.
The migration (`migrate_session6b.sql`) is additive and idempotent;
existing rows default to 'federal_only', which is correct for the
current federal-only corpus.

**Why not detect jurisdiction in the extractor?**
Fine-grained classification (preemption vs. deference vs. floor) is a
semantic judgment requiring keyword recognition in running text — the same
class of judgment that boilerplate detection requires, and for the same
reason it belongs to the normalizer. The extractor only makes structural
observations. Setting 'federal_only' as the default and flagging
'involves_states' when state-reference patterns appear is a structural
observation (pattern present / absent), not a semantic classification.
This preserves the extractor/normalizer boundary established in Session 5.

**Why not ingest state legislation?**
Full state corpus ingestion is a significant product expansion: 50+
source schemas, inconsistent API coverage across states, and a separate
baseline_doctrine supplement for each jurisdiction. The federalism
dimension visible from federal documents already in the corpus — EOs
directing state agencies, preemption clauses in federal bills, deference
grants — is the higher-value capture with zero additional source work.
State legislation is deferred; the field design is forward-compatible
with it (the enum values are jurisdiction-agnostic) but does not require it.

**Detection signals for normalizer (textual heuristics):**
- preempts_state:  "preempt", "supersede", "displace", "occupy the field",
                   "no State may", "State law is preempted"
- defers_to_state: "State may", "States may", "subject to State law",
                   "as determined by the State", "State government"
                   (without preemption marker)
- creates_floor:   "minimum", "at least", "not less than",
                   "may provide greater", "more protective"

**Schema changes:**
- `policylens/chunker/types.py`: `jurisdiction_scope: str = 'federal_only'`
  added to `ExtractedUnit`; `EXTRACTOR_JURISDICTION_SCOPES` frozenset added;
  `validate()` extended to check it.
- `policylens/ontology/provision_schema.yaml`: `jurisdiction` field added
  after `doc_type` in the structural fields section.
- `policylens/extractors/fr_presdocu.py`: `_INVOLVES_STATES_PATTERN` regex
  and `_jurisdiction_scope()` helper added; `jurisdiction_scope` passed to
  all `ExtractedUnit` constructors.
- `policylens/extractors/uslm.py`: same pattern as fr_presdocu; header units
  hardcoded to 'federal_only' (headers carry no deontic content).
- `policylens/db/extracted_units.py`: `jurisdiction_scope` added to the
  upsert INSERT column list.
- `policylens/db/migrate_session6b.sql`: new migration adding
  `jurisdiction_scope` to `extracted_units` and `jurisdiction` to
  `provisions`, both defaulting to 'federal_only'.
- `tests/test_extractors.py`: 12 new tests added (5 per extractor class +
  3 cross-cutter); test suite grows from 34 to 46. Two new XML fixtures
  added: `EO_STATE_DIRECTED_XML` and `BILL_PREEMPTION_XML`.

**Deferred:** Full state legislative ingestion (LegiScan/OpenStates).
Separate source family, separate baseline_doctrine supplement, separate
scoping session. Not gated on this field design.

---

## Session 7: Normalizer Atomicity Heuristic

### Step 0 — Pre-implementation corpus review

**Status check:** All 120 documents confirmed at `status='extracted'`. Zero
documents at `status='raw'` or `status='error'`. Clean starting state.

**raw_text length distribution (extracted_units):**

| source_schema | element_type        | count | min_chars | avg_chars | max_chars | under_20 | over_2000 |
|---------------|---------------------|-------|-----------|-----------|-----------|----------|-----------|
| fr_presdocu   | preamble            | 118   | 50        | 489       | 1201      | 0        | 0         |
| fr_presdocu   | provision_candidate | 109   | 31        | 338       | 1258      | 0        | 0         |
| uslm          | header              | 349   | 4         | 26        | 136       | 189      | 0         |
| uslm          | provision_candidate | 834   | 3         | 137       | 1465      | 49       | 0         |

No boundary errors in FR corpus. The 49 USLM provision_candidates under 20
chars and the 189 USLM headers under 20 chars are expected. No over-2000-char
outliers in any category; no missed section boundaries.

**Finding 4 confirmed:** Corpus inspection of short USLM provision_candidates
identified three distinct fragment patterns requiring separate treatment.
See heuristic decision below.

---

### Decision: Normalizer Atomicity Heuristic (Session 7)

**Three fragment patterns identified in corpus, each requiring distinct
treatment:**

**Pattern A — Em-dash continuation stubs**
Examples: `"The Secretary shall—"`, `"is amended—"`, `"That Congress—"`.
The em-dash is a USLM drafting convention for "followed by a list." The
`<text>` element at this node holds only the introductory clause; the
operative content is distributed across child nodes. Semantically incomplete
regardless of word count — a length heuristic would miss long stubs like
`"Section 236(c)(1) of the Immigration and Nationality Act (8 U.S.C.
1226(c)(1)) is amended—"` (88 chars) entirely.

**Pattern B — Bare noun/verb phrase list items**
Examples: `"airboats;"`, `"motorboats;"`, `"hovercraft;"`, `"swimming; and"`.
Semicolon-terminated list items from an enumerated list. No finite verb, no
subject, no modality. The operative obligation lives in a parent provision
several levels up.

**Pattern C — Definition block intros**
Examples: `"In this Act:"`, `"In this section:"`, `"In this subsection:"`.
Colon-terminated intro lines for definition blocks. No deontic content.
Occur at nesting_depth 0–2 across 9 documents.

**Decided heuristics:**

| Pattern | Detection signal | Assigned value |
|---------|-----------------|----------------|
| Em-dash stub | `raw_text` ends with `—` (U+2014) | `chunk_flag = 'review_boundary'` |
| Bare fragment | No legislative modal verb AND ≤15 words AND no trailing em-dash | `chunk_flag = 'review_boundary'` |
| Definition block intro | Matches `^In (this\|the) [A-Za-z ]+[:—]` | `element_type = 'header'` |

**Legislative modal verb list (for bare fragment detection):**
`shall`, `may`, `must`, `will`, `is`, `are`, `was`, `were`, `be`, `been`,
`have`, `has`, `do`, `does`, `did`.
The 15-word threshold is approximate, calibrated against the corpus sample.

**chunk_flag priority order (highest wins):**
1. `condition_stack` depth > 2 → `review_nested_conditional`
2. `legal_address_raw` not None OR inline citation detected → `review_cross_reference`
3. Atomicity heuristic fires → `review_boundary`
4. Otherwise → `clean`

**Why em-dash signal is length-independent:**
A length threshold would miss longer stubs. The trailing em-dash is the
correct signal regardless of text length.

---

### Decision: Normalizer element_type Override — Extension to 'header'

**Session 5 sanctioned:** normalizer may override `provision_candidate →
boilerplate` (semantic judgment about formulaic non-substantive content).

**Session 7 extends this to:** normalizer may also override `provision_candidate
→ header` for definition block intro lines.

**Rationale:** Definition block intros (`"In this Act:"`) are structural
navigation markers, not provisions — they have no independent deontic content.
`header` is more accurate than `boilerplate`:
- `boilerplate` = formulaic legal immunity/limitation language (substantive
  but predictable); tagged `domain:governmental_structure` at annotation
- `header` = structural navigation marker; skipped for annotation

The two normalizer overrides are the same kind of thing: both are cases where
the extractor correctly identified a `<text>` element (structural observation)
and the normalizer determines the content has no deontic substance (semantic
judgment). The Session 5 rationale applies identically.

**Known artifact:** `element_type = 'header'` now has two assignment origins —
extractor-assigned (structural headers from XML) and normalizer-assigned
(definition block intros). The `extracted_unit` record always preserves the
original extractor assignment (`provision_candidate`); lineage is fully
traceable.

---

### Decision: Boilerplate Child Inheritance

**Observation:** EO Sec. 3(a) `"Nothing in this order shall be construed to
impair or otherwise affect:"` correctly triggers boilerplate detection. Its
child list items (`"the authority granted by law to an executive department..."`,
`"the functions of the Director..."`) do not contain the trigger phrase but
are semantically part of the same boilerplate clause.

**Decision:** When a unit is classified `boilerplate`, all path prefixes of
its section_path are registered in a `boilerplate_section_prefixes` set. Child
units whose section_path has any registered prefix inherit the `boilerplate`
classification, regardless of their text content.

**Why:** Child list items are continuations of the parent boilerplate clause —
they have no independent deontic content. Leaving them as `provision_candidate`
would send semantically meaningless fragments to the annotation model.

**Implementation:** `_has_boilerplate_ancestor()` checks strict prefixes only.
Applied before `_classify_element_type()` in the processing loop.

---

### Decision: context_text Section Path Fallback

**Observation:** FR documents produce no `header` element_type units from the
extractor — section headings are embedded inline in paragraph text, not in
separate XML elements. The `section_heading_map` built from extractor header
units is therefore always empty for FR documents.

**Decision:** `_build_context_text()` accepts an optional `section_path`
parameter. When `section_heading` is None and `section_path` is non-empty,
the joined section path (e.g. `"Sec. 2(b)"`) is used as the section label
in the context_text header. Explicit heading always takes priority.

**Result:** FR provision context_text now reads:
`"[executive_order — EO Title — Sec. 2]"`
rather than `"[executive_order — EO Title]"`, providing meaningful section
context for vector embedding.

---

### Decision: Inline Citation Detection for chunk_flag

**Observation:** `legal_address_raw` is null across the entire corpus —
citations appear in prose text, not in structured XML attributes. The original
`review_cross_reference` trigger (`legal_address_raw is not None`) never fired.

**Decision:** `_assign_chunk_flag()` falls back to inline citation detection
via `_CITATION_RE` when `legal_address_raw` is None. Two citation variants
detected:
1. Short form: `N U.S.C. [§] section` (e.g. `"8 U.S.C. 1226(c)(1)"`)
2. Long form: `section N of title N, United States Code`
   (e.g. `"section 553 of title 5, United States Code"`)

**Corpus impact:** 92 provision_candidates with inline citations now correctly
receive `chunk_flag = 'review_cross_reference'` rather than `'clean'`.

---

### Decision: jurisdiction_scope Backfill (Session 7 — Post-extraction)

**Problem:** `migrate_session6b.sql` added `jurisdiction_scope` to
`extracted_units` with `DEFAULT 'federal_only'`. This defaulted all 1,410
existing rows to `federal_only` without applying the `_INVOLVES_STATES_PATTERN`
regex to their text. Five units with genuine state-related language were
missed; 20 total units had incorrect `federal_only` assignments.

**Fix:** One-time SQL backfill applied in Session 7. 20 rows updated across
11 documents. Affected documents reset to `status='extracted'` and
re-normalized.

**Prevention:** This problem cannot recur for new documents — new ingestion
runs through the extractor which applies `_INVOLVES_STATES_PATTERN` at
extraction time. The backfill was a one-time repair for the pre-Session-6b
corpus.

**Artifact:** `policylens/db/migrate_session7_jurisdiction_backfill.sql`
committed in Session 9. Contains the exact SQL applied, for audit trail.

---

### Session 7 Corpus Results (Final)

**Total provisions:** 943

**By doc_type and element_type:**
| doc_type | element_type | count |
|----------|-------------|-------|
| executive_order | boilerplate | 30 |
| executive_order | provision_candidate | 79 |
| bill | header | 9 |
| bill | provision_candidate | 682 |
| resolution | provision_candidate | 143 |

**chunk_flag distribution:**
| flag | count |
|------|-------|
| clean | 474 (50%) |
| review_boundary | 349 (37%) |
| review_cross_reference | 120 (13%) |
| review_nested_conditional | 0 |

**condition_stack depth:**
| depth | count |
|-------|-------|
| 0 (unconditional) | 862 |
| 1 | 78 |
| 2 | 3 |
| 3+ | 0 |

**jurisdiction:**
| value | count |
|-------|-------|
| federal_only | 926 |
| creates_floor | 8 |
| involves_states | 5 |
| preempts_state | 3 |
| defers_to_state | 1 |

**context_text:** 943/943 populated, 0 nulls.
**Documents at status='transformed':** 120/120.

---

## Session 8: Product Strategy and Phase Structure

### Decision: Persona Definitions

Three personas defined. See project_plan.md for full descriptions.

**Key relationship between personas:**
Persona 1 (Overwhelmed Citizen) is an end user of what Persona 2
(Data Builder) could build on top of PolicyLens. PolicyLens building
the Persona 1 UI directly does not create technical debt for Persona 2,
as long as the API is the contract and the UI is a consumer of it.

**Why start with Persona 1 despite Persona 2 being the scale story?**
The Persona 1 UI is the first client of the API and the proof that the
API works. It provides tangibility for early product development and
attracts builders. The reading experience does not constrain the data
model — any UI decision that would constrain the data model is wrong by
definition.

---

### Decision: API-First Architecture

**Decision:** PolicyLens is a product, not purely a platform, but built
API-first so the UI is the first client of the API, not the other way
around.

**Why API-first?**
The only way to serve Persona 1 and Persona 2 without creating debt is
to ensure the API is the contract and the UI is a consumer. If the UI
drives the data model — denormalized fields for display convenience,
schema assumptions baked into rendering — then Persona 2 builders are
constrained by Persona 1 design decisions that have nothing to do with
their use cases. API-first prevents this structurally, not by convention.

**Why not platform-only?**
A platform without a Persona 1 UI has no proof of concept, no early
distribution channel, and no tangible product for attracting builders.
The UI is not a distraction from the platform — it is the first
demonstration that the platform works.

---

### Decision: chunk_flag Resolution Strategy (chunk-resolve pipeline stage)

**The problem:** 469 of 943 provisions (50%) carry chunk_flag ≠ 'clean'
after Session 7 normalization. This is a blocking prerequisite for any
user-facing surface — a corpus where half the provisions have unresolved
chunking uncertainty cannot be the source of truth Persona 1 requires.

**Decision: deterministic resolution first, LLM agent on residual.**

This reverses the Session 5 "no auto-merge" decision for bare noun phrase
fragments. The Session 5 decision was correct at the time — before the
full corpus run, the scope of the flag problem was unknown and caution
was appropriate. The Session 7 corpus results (349 review_boundary flags,
50% of total provisions) make clear that human review of this volume is
not the right path. The USLM XML structure is well-defined enough that
deterministic merge is reliable.

**Layer 1 — Deterministic fixes:**

Em-dash stubs: The USLM XML structure is known. The stub always has child
nodes containing the operative content. Deterministic merger: concatenate
the stub with its immediate children in document order. Structural fix,
no model needed. Rationale: the em-dash is a drafting convention that
always signals "followed by a list" in USLM XML; the child nodes are
always the continuation.

Bare noun phrase fragments: Walk up section_path until a unit with a
finite verb and modality is found. Attach fragment as a list item under
that parent. USLM nesting makes this traversal well-defined. Structural
fix, no model needed. Rationale: bare fragments always participate in the
obligation of their nearest ancestor with deontic content; the section_path
array makes the ancestry explicit.

Inline cross-references (review_cross_reference): These are not chunking
problems — the provision text is correctly bounded. Resolution is reference
extraction: parse the USC citation, upsert to legal_addresses, insert the
provision_references junction record with ref_type = 'references'. Flag
clears when the reference is resolved. Deterministic extraction task.

**Layer 2 — LLM agent pass:**
Whatever remains genuinely ambiguous after deterministic fixes — provisions
where boundary judgment requires understanding legal meaning, not just XML
structure — is the correct input for an LLM agent review pass. This
residual set is expected to be small. This is chunk boundary validation,
not annotation work (Phase 3).

**Why LLM agent, not human review?**
Chunk boundary validation is a structural judgment (is this a complete
deontic proposition?), not a classification judgment (what domain is this
provision in?). LLM agents can reliably evaluate structural completeness.
Human reviewers are the right resource for annotation decisions where
domain expertise and judgment about constitutional doctrine are required.
Misapplying human review to structural decisions is an expensive error.

**Implementation:** A new `chunk-resolve` CLI command, parallel in
structure to `chunk-normalize`. Runs after `chunk-normalize`. Design the
deterministic merge pass against actual flagged provisions in the DB before
writing any code. Same sequencing discipline as Session 7.

---

### Decision: Corpus Expansion — Ingest Everything

**Decision:** Full Federal Register PRESDOCU back catalog and full
Congressional USLM back catalog. No artificial scope limit.

**Why everything?**
- The major policy domains Persona 1 arrives with (immigration, healthcare,
  taxation, education, firearms) need meaningful result sets. A 120-document
  corpus returning 8 results for a real query is not a product. Full
  coverage is what makes search actually useful.
- Full back catalog makes the temporal chain meaningful — legal address
  evolution across administrations becomes queryable with real data.
- Full coverage is what makes RAG and agent use cases qualitatively
  valuable for Persona 2, not just incrementally better.
- Both sources are already wired. This is a scale operation on existing
  infrastructure, not new build work.
- API rate limits are an engineering throttle, not a scope constraint.
- Storage cost is negligible (established Session 4).

**Sequencing:** After chunk-resolve is proven stable at 120 documents.
Stress test at ~500 documents before full scale. This surfaces extractor
edge cases that did not appear at 120 documents.

---

### Decision: User Journey Before Technology

**Decision:** Feature and user journey design precedes technology selection
in all future sessions. Technology serves the user experience, not the
reverse.

**Why record this as an explicit decision?**
Session 8 began with technology considerations (web framework, hosting,
frontend architecture) before the user personas and journeys were defined.
This ordering produced analysis that could not be grounded in product
requirements. The correct order is: personas → journeys → features →
technology. This standing rule makes the correct order explicit and
prevents recurrence.

**Implication for Session 9:** Technology decisions are on the agenda but
are preceded by Persona 1 user journey mapping. Technology is selected
against the concrete journey, not in the abstract.