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

raw:        Layer 1 complete; document in documents table; no extracted_units
extracted:  Layer 2a complete; extracted_units populated; provisions not yet written
transformed: Layer 2b complete; provisions populated; annotation fields empty
classified: Layer 3 complete; annotation fields populated

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