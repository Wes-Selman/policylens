# PolicyLens — Session 4 Handoff
## Complete Decisions Log (Sessions 0–3) + Session 4 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 3)

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

**Artifacts produced (available in repo):**
- provision_schema.yaml — full provision record schema
- controlled_vocabulary.yaml — all enumerated field definitions + cross-rules
- baseline_doctrine.yaml — per-sub-domain constitutional baseline table
- decisions_log.md — rationale layer for all major design decisions
- project_plan.md — phased project plan through Phase 5

---

## Decisions Log — Session 0

**DECIDED: Provision definition**
A provision is a single deontic proposition of the form 〈subject, modality,
object〉 — the minimal unit that assigns exactly one Hohfeldian modality to
exactly one subject with respect to exactly one object of legal operation.
Atomicity is operationalized as: a unit is atomic if it cannot be split into
two valid 〈subject, modality, object〉 triples without loss of meaning.

**DECIDED: Top-level structure**
Multi-dimensional tagging taxonomy, designed to be graph-promotable.
Relationships between provisions stored as typed metadata fields from day
one; not graph edges in the initial implementation. Per-dimension structure:
structural layer = flat; normative layer = flat with named traditions as
first-class nodes; topic/mechanism layer = two-level hierarchy, extensible;
rights layer = hierarchy mirroring constitutional doctrine.

---

## Decisions Log — Session 1

**DECIDED: Clustering mechanism**
Multi-dimensional scoring → geometric projection → clustering in the
projection space, validated against known party affiliation. Unsupervised
in the developmental phase.

Each provision scored on signed ordinal dimensions drawn from the normative
and rights layers. Vectors projected onto two primary axes (economic liberty,
social liberty). Clustering is k-means or hierarchical in this 2D projection;
party alignment is post-hoc validation, not a training label.

Borrowed from DW-NOMINATE: two-axis geometry, party-as-validation,
post-hoc axis interpretation. Borrowed from CMP: signed category scoring,
provision-as-unit, position-as-weighted-distribution. Discarded from
DW-NOMINATE: cutting-plane / revealed-preference framework. Discarded
from CMP: topic-semantic categories — replaced with deontic categories
grounded in Hohfeld.

**DECIDED: Required tag space structure**
Value type: Ordinal integers on a signed scale (−2 to +2) for normative
and rights dimensions. Structural and topic dimensions remain nominal.
Normative and rights dimensions must constitute a metric space.

Critical independence assumption: normative layer (Hohfeldian modality)
and rights layer (liberty valence) must be independently scorable.

**DECIDED: Minimum dimensions for axis separability**

| Ideological type | Economic liberty axis | Social liberty axis |
|---|---|---|
| Libertarian | + (expand) | + (expand) |
| Progressive | − (contract) | + (expand) |
| Conservative | + (expand) | − (contract) |
| Communitarian | − (contract) | − (contract) |

Minimum vocabulary tags: domain, valence, subject_type — all three required
jointly.

---

## Decisions Log — Session 2

**DECIDED: Constitutional status quo baseline**
Economic axis: Post-New Deal baseline (West Coast Hotel, 1937 onward).
Social axis: Current doctrine baseline per sub-domain, with version dates.
Mandatory annotation aid: per-sub-domain doctrine summary table
(baseline_doctrine.yaml).

**DECIDED: Controlled vocabulary — three minimum tags**

domain values: economic | social | civil_procedural |
governmental_structure | mixed | pending

Edge case rules: taxation → economic unless behavioral penalty on protected
conduct; anti-discrimination → mixed; agency-delegated with indeterminate
object → domain:pending.

valence scale (−2 to +2):
+2 strong liberty expansion / +1 moderate expansion / 0 neutral /
−1 moderate contraction / −2 strong contraction

Cross-rules (see controlled_vocabulary.yaml for full text):
- A: Subject inversion (duty on government = expansion for protected class)
- B: Modality determines direction (permission ≥ 0; duty/prohibition ≤ 0)
- C: Domain determines axis, not ideology
- D: Baseline anchoring (state baseline before scoring)

subject_type values: individual_natural | individual_commercial |
corporation | government_federal | government_state | government_any | mixed

**DECIDED: Normative layer vocabulary (Hohfeldian)**
Primary set: duty | permission | power | immunity | complex
Four correlatives (disability, liability, no_right, right_claim) deferred
to second annotation pass.
object_class preliminary taxonomy: conduct | resource | information |
status | relation | proceeding

**DECIDED: Independence assumption pilot design**
15 provisions (5 economic, 5 social, 5 mixed). Two separate annotation passes.
Pass A: modality and object_class only.
Pass B: domain, valence, subject_type only.
Independence test: Spearman |ρ| > 0.4 → rubric redesign required.
IRR target: Cohen's κ ≥ 0.70 on valence.

In model-primary context: pilot measures model-human agreement and serves
as prompt calibration, not human annotator training.

---

## Decisions Log — Session 3

**DECIDED: Nested conditional rule**
Collapse up to 2 conditional layers into one provision with condition_stack.
Split when a new subject or new Hohfeldian modality is introduced, or at
3+ layers (mandatory adjudicator review; almost always a split).

condition_stack schema: structured objects {condition_type: [threshold |
existence | temporal | other], text} — not plain strings, to allow
condition-type querying in later analysis.

**DECIDED: Cross-reference provisions**
Cross-reference is the object specification. External definition is metadata
(object_ref: {statute, section}). Domain-tag if determinable from citation
alone; if not, domain:pending with pending_reason: unresolved_object_ref.

**DECIDED: domain:pending workflow**
Re-tag trigger: final rule published in Federal Register (not NPRM).
Responsibility: corpus maintainer.
Each pending record carries: pending_monitor: {agency, docket_id_or_cfr_section}.
Pending provisions: excluded from clustering runs; included in corpus
statistics. Every clustering run report must state pending exclusion count.
Silent omission is prohibited.

**DECIDED: Annotation strategy (revised from earlier framing)**
Model-primary. Human annotators do stratified sample checking — oversampling
structurally complex and domain-ambiguous provisions, not random sampling.
Pilot = prompt calibration instrument.
Cross-rule D (baseline anchoring) is a prompt engineering requirement:
model must output its baseline sentence explicitly so sample-checker can
evaluate reasoning, not just final score.

**DECIDED: Adjudication procedure (pilot phase)**
1. Structured discussion ≤20 minutes: both parties state baseline sentence
   and cross-rule citations.
2. If unresolved: lead adjudicator decides with written rationale.
3. No majority-rule, no third-annotator tiebreak in pilot phase.
Post-pilot adjudication model: deferred to Session 4.

**DECIDED: κ failure protocol**
If κ < 0.70 on valence:
1. Dimension isolation: compute κ per dimension.
2. Error typing: Type R (rubric ambiguity) / Type B (baseline disagreement)
   / Type E (execution error).
3. Minimum intervention: address most frequent error type only. Rubric
   redesign only if Type R > 50% of disagreements.
4. Re-pilot with new 15-provision set. Second failure → full rubric review.

**DECIDED: Dimension-specific κ targets**

| Dimension | κ target |
|---|---|
| valence | ≥ 0.70 |
| domain | ≥ 0.80 (pilot fails on domain regardless of valence if below) |
| subject_type | ≥ 0.75 |
| modality | ≥ 0.75 |

**DECIDED: domain:mixed projection — Option B**
Mixed provisions carry valence_economic and valence_social as separate
fields on a single record. Not split into two records.
Projection: mixed provision = fully specified (valence_economic,
valence_social) point. Single-axis: economic = (valence, 0);
social = (0, valence). Zero is structural, not a scored neutral.
Sensitivity analysis (centroid distortion) deferred to Phase 5.

**DECIDED: Baseline doctrine table**
Living document with version dates. See baseline_doctrine.yaml.
Sub-domains covered: privacy_informational, privacy_surveillance, speech,
religion_free_exercise, religion_establishment, bodily_autonomy_abortion
(HIGH VOLATILITY), bodily_autonomy_other, property_rights,
freedom_of_contract, labor_relations, taxation.

**DECIDED: Chunking approach**
Implement chunker at sentence/clause level. Handle edge cases empirically
as they surface during implementation — not deferred. Genuinely ambiguous
boundaries flagged with chunk_flag (clean | review_nested_conditional |
review_cross_reference | review_boundary). Flagged provisions included in
corpus; surfaced for human review in front-end.

---

## Session 4 Primary Agenda

### 1. Chunker implementation
Begin Phase 1. Design and implement the chunker against the 120-document
corpus. Key questions:
- What is the input format of the 120 documents? (PDF, XML, plain text?)
- What parser / extraction pipeline is appropriate for the document types?
- What is the storage layer? (Postgres, SQLite, vector store — still open)
- How are section boundaries detected and encoded in section_id?
- Chunker output review: inspect distribution of chunk_flag values and
  condition_stack depths; resolve edge cases as they appear.

### 2. Storage layer decision
Must be decided before chunker output can be stored. Considerations:
- Full-text search requirement (Phase 2)
- Vector embedding requirement (Phase 3/5)
- Operational simplicity for a project at this scale (120 documents)
- Whether a single store handles both relational queries (filter by domain,
  valence range) and semantic search, or whether two stores are needed.

### 3. Post-pilot adjudication model
Decide whether to move from lead-adjudicator model (pilot) to
three-annotator majority for full corpus, with adjudicator reserved
for three-way disagreements. Specify: annotator assignment logic, what
constitutes a three-way disagreement, escalation criteria.

### 4. Front-end scope for Phase 2
Define the minimum viable front-end for Phase 2 (browse and search,
no annotation fields visible yet). Technology choices, hosting, and
whether Phase 2 and Phase 4 share a codebase or Phase 2 is a prototype.

---

## Deferred (not Session 4)

- Four Hohfeldian correlatives (disability, liability, no_right,
  right_claim) — second annotation pass, post-pilot
- Graph promotion of typed metadata fields — post-validation
- Versioning and re-tagging strategy at scale (Dobbs-class events)
- Clustering sensitivity analysis (mixed-provision centroid distortion)
- k-means parameter selection

---

## Standing Rules

- Every decision entry must include a rationale. A decision without
  rationale is not a valid log entry.
- Deferred items carry forward verbatim until decided or explicitly dropped.
- New open questions surfaced in a session are added to the next session's
  agenda before the session closes.
- The handoff document is the single source of truth. Anything not in
  the handoff did not happen.