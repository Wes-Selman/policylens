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