# PolicyLens — Session 7 Handoff
## Complete Decisions Log (Sessions 0–6b) + Session 7 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 6b)

**Annotation strategy:** Model-primary annotation. Human annotators
sample-check, with stratified sampling that oversamples structurally
complex and domain-ambiguous provisions (not random). The IRR pilot
(15 provisions) is a prompt calibration instrument, not a human annotator
training gate.

**Sequencing:** Chunking first. Annotation fields are not populated at
chunking time. The taxonomy exists and is fully specified; it is not
needed until Phase 3 (Annotation). The project is currently in Phase 1
(Chunk & Store), Layer 2b (Normalization).

**Pipeline architecture:** Layer 2a (extraction) complete as of Session 5.
Session 6b added jurisdiction_scope to the extraction layer.
Session 7 implements Layer 2b (normalization).

**Artifacts in repo:**
- provision_schema.yaml — full provision record schema (updated Session 6b)
- controlled_vocabulary.yaml — all enumerated field definitions + cross-rules
- baseline_doctrine.yaml — per-sub-domain constitutional baseline table
- decisions_log.md — rationale layer (updated Session 6b)
- project_plan.md — phased project plan through Phase 5

---

## Decisions Log — Sessions 0–4

*(Full text preserved — see decisions_log.md in repo)*

**Session 0:** Provision definition (Hohfeldian triple); top-level structure.

**Session 1:** Clustering mechanism; required tag space; axis separability.

**Session 2:** Constitutional baseline; controlled vocabulary; Hohfeldian
primary set; independence assumption pilot design.

**Session 3:** Nested conditional rule; cross-reference provisions;
domain:pending workflow; annotation strategy; adjudication procedure;
κ failure protocol; κ targets; domain:mixed projection Option B;
baseline doctrine table; chunking approach.

**Session 4:** Pipeline architecture (extractor/normalizer split);
ExtractedUnit as persisted intermediate; LegalAddress as first-class entity;
context_text field; temporal fields (nullable); boilerplate classification;
doc_status enum extension; pipeline idempotency; storage layer (Postgres only);
source XML structure confirmed; three UX modes.

---

## Decisions Log — Session 5

**DECIDED: Session scope split — extraction Session 5, normalization Session 6**
Rationale: normalizer heuristics should be designed against real
extracted_units output. Extracting first and inspecting before writing
the normalizer produces better heuristics and catches extractor design
problems before they propagate into the provision table.

**DECIDED: DDL applied**
Four tables created: extracted_units, provisions, legal_addresses,
provision_references. doc_status enum extended with 'extracted' (AFTER 'raw').
All UNIQUE constraints, FK constraints, and indexes applied.

**DECIDED: Provision id separator**
Provisions primary key format: {doc_id}|{section_id}|{provision_index}
Pipe character used as separator (not colon).

**DECIDED: element_type assignment responsibility**
Extractors assign: provision_candidate | preamble | header
Normalizer assigns: boilerplate (semantic judgment on provision_candidate units)
Extractors never assign boilerplate.

**DECIDED: FRPresdocuExtractor and USLMExtractor implementation complete**
Handles EXECORD, PROCLA, PRNOTICE, DETERM (FR) and bill/resolution (USLM).
41-test suite passing.

**DECIDED: chunk-extract CLI command implemented**
Dispatches by source field. Idempotent. Processes status='raw' documents.
Advances to status='extracted'.

**EXTRACTION OUTPUT** *(Session 5 corpus run)*

```
 source_schema |    element_type     | count | avg_depth | max_depth | with_citation
---------------+---------------------+-------+-----------+-----------+---------------
 fr_presdocu   | preamble            |   118 |      0.00 |         0 |             0
 fr_presdocu   | provision_candidate |   109 |      0.71 |         1 |             0
 uslm          | header              |   349 |      0.85 |         3 |             0
 uslm          | provision_candidate |   834 |      1.66 |         6 |             0
```

Total extracted_units: 1,410. Documents with extraction errors: 0.
Provisions with legal_address_raw populated: 0 (expected).

**Pre-normalization findings:**

Finding 1 — Proclamations are entirely preamble (expected, not a bug).
Finding 2 — USLM nesting depth reaches 6 (handled correctly by recursive walking).
Finding 3 — FR nesting depth max 1 (matches expectations).
Finding 4 — Bare noun phrase list items at depth 6 (affects normalizer):
  Units like "the Defense Intelligence Agency;" — no verb, no modality.
  Normalizer must flag chunk_flag = 'review_boundary'. No auto-merge.

---

## Decisions Log — Session 6b: Jurisdiction Scope Field

**Decision:** Add `jurisdiction` field to provisions and coarse
`jurisdiction_scope` signal to `ExtractedUnit`.

**Two-layer design:**
- Extractor sets `jurisdiction_scope` on `ExtractedUnit`:
  values: `federal_only` | `involves_states` | `unknown`
  Default: `federal_only`. Detection via `_INVOLVES_STATES_PATTERN` regex.
- Normalizer refines `involves_states` into the full provision-level enum:
  `federal_only` | `preempts_state` | `defers_to_state` | `creates_floor`
  | `involves_states` | `unknown`

**Why add at the extractor layer now:**
Field must exist on ExtractedUnit before extraction runs so the normalizer
has the coarse signal without requiring re-extraction. Migration is additive
and idempotent; existing rows default to 'federal_only'.

**Why not detect fine-grained jurisdiction in the extractor:**
Preemption vs. deference vs. floor is a semantic judgment — same class as
boilerplate detection, same reason it belongs to the normalizer. Extractor
only signals pattern-present/absent (structural), not what the pattern means
(semantic). Preserves the extractor/normalizer boundary from Session 5.

**Why not ingest state legislation:**
50+ source schemas, inconsistent API coverage, separate baseline_doctrine
supplement needed per jurisdiction. The federalism dimension visible from
federal documents already in the corpus is the higher-value capture with
zero additional source work. State legislation deferred; field design is
forward-compatible.

**Detection signals for normalizer (textual heuristics):**
- preempts_state:  "preempt", "supersede", "displace", "occupy the field",
                   "no State may", "State law is preempted"
- defers_to_state: "State may", "States may", "subject to State law",
                   "as determined by the State", "State government"
                   (without preemption marker)
- creates_floor:   "minimum", "at least", "not less than",
                   "may provide greater", "more protective"

**Schema changes delivered and committed:**
- `policylens/chunker/types.py`: `jurisdiction_scope` field + frozenset +
  `validate()` enforcement
- `policylens/ontology/provision_schema.yaml`: `jurisdiction` field added
  after `doc_type`
- `policylens/extractors/fr_presdocu.py`: `_INVOLVES_STATES_PATTERN` +
  `_jurisdiction_scope()` helper wired into all ExtractedUnit constructors
- `policylens/extractors/uslm.py`: same; header units hardcoded
  to 'federal_only'
- `policylens/db/extracted_units.py`: `jurisdiction_scope` in upsert
- `policylens/db/migrate_session6b.sql`: run and verified on live DB;
  `jurisdiction_scope` on `extracted_units`, `jurisdiction` on `provisions`,
  both NOT NULL DEFAULT 'federal_only'
- `policylens/docs/decisions_log.md`: Session 6b entry added
- `tests/test_extractors.py`: 46 tests passing (up from 34); two new XML
  fixtures: `EO_STATE_DIRECTED_XML`, `BILL_PREEMPTION_XML`

**Deferred:** Full state legislative ingestion (LegiScan/OpenStates).
Separate source family, separate scoping session. Not gated on this field.

---

## Session 7 Primary Agenda

### 0. Review extraction output (before writing any code)
The extraction output is recorded in the Session 5 section above.
Before implementation begins, answer:
- Are there extracted_units with unexpectedly long or short raw_text
  that suggest extractor boundary errors?
- Any documents stuck at status='extracted'? Investigate before normalizing.
- Review Finding 4 (bare noun phrase list items) — confirm the heuristic
  below is appropriate before coding it.

### 1. Decide normalizer atomicity heuristic

**Candidate approach (updated for Finding 4):**

Flag chunk_flag = 'review_boundary' if any of the following apply:
- Contains more than one sentence with distinct grammatical subjects
- Has condition_stack depth > 2 (mandatory per Session 3 decision)
  → chunk_flag = 'review_nested_conditional' (higher priority)
- Contains coordinating conjunction connecting two independent clauses
  each with their own subject and verb
- Bare noun phrase (Finding 4): raw_text contains no finite verb AND
  is under ~15 words → chunk_flag = 'review_boundary'

Flag chunk_flag = 'review_cross_reference' if legal_address_raw is not None
(lower priority than review_nested_conditional).

This is auditable and structural, not semantic. Normalizer flags; it does
not restructure.

Record the decided heuristic in decisions_log.md before writing code.

### 2. Implement policylens/chunker/normalize.py

Source-agnostic. Reads ExtractedUnit records, writes to provisions,
legal_addresses, provision_references.

**Input:** extracted_units rows for a given doc_id (status='extracted')
**Output:** provision rows, legal_address rows, provision_reference rows

**Processing steps per extracted_unit:**

Step 1 — Skip non-provision units
- element_type = 'preamble': skip. Retain for context_text construction.
- element_type = 'header': skip.
- element_type = 'provision_candidate': proceed.

Step 2 — Boilerplate detection
Inspect text for General Provisions boilerplate patterns:
- "Nothing in this order shall be construed to impair or otherwise affect"
- "This order shall be implemented consistent with applicable law"
- "This order is not intended to, and does not, create any right or benefit"
- "The costs for publication of this order shall be borne by"
If matched: element_type = 'boilerplate'. Otherwise: 'provision_candidate'.

Step 3 — condition_stack detection
Scan text for conditional antecedents:
- Existence condition: "if [noun phrase] exists", "in the event that"
- Threshold condition: "if [quantity] exceeds", "when [metric] reaches"
- Temporal condition: "upon", "after [date/event]", "before [date/event]"
- Other: "if", "unless", "provided that", "except that"
Build condition_stack as list of {condition_type, text} objects.

Step 4 — jurisdiction refinement
If jurisdiction_scope = 'involves_states': apply normalizer heuristics
(preempts_state / defers_to_state / creates_floor) to set jurisdiction
on the provision record. If jurisdiction_scope = 'federal_only' or
'unknown': pass through unchanged.

Step 5 — chunk_flag assignment
Priority order (highest wins):
1. condition_stack depth > 2 → 'review_nested_conditional'
2. legal_address_raw not None → 'review_cross_reference'
3. Atomicity heuristic fires → 'review_boundary'
4. Otherwise → 'clean'

Step 6 — context_text construction
Query preamble units for this doc_id. Build:
  "[{doc_type} — {doc_title} — {section_heading}]
   {condition_stack_summary if non-empty}
   Text: {provision_text}"

Step 7 — legal_address resolution
If legal_address_raw not None: parse, upsert to legal_addresses,
insert to provision_references with ref_type = 'references'.

Step 8 — provision_index assignment
Zero-based within each (doc_id, section_id) group, ordered by
extracted_units.id ASC.

Step 9 — Write provision record
id = "{doc_id}|{section_id}|{provision_index}"
INSERT ... ON CONFLICT DO UPDATE.

### 3. CLI — chunk-normalize command
Add to policylens/cli.py:

```
python3 -m policylens.cli chunk-normalize [--doc-id N]
```

- Without --doc-id: all documents with status='extracted'
- With --doc-id: single document (for testing)
- Advances status to 'transformed'
- Idempotent

Output: per-document summary (provisions written, chunk_flag distribution).
Final summary: totals across corpus.

### 4. Full corpus run + chunking report
Run chunk-normalize on all 120 documents. Generate and record:

```sql
-- Provision totals by doc_type and element_type
SELECT d.doc_type, p.element_type, COUNT(*) as count
FROM provisions p JOIN documents d ON p.doc_id = d.id
GROUP BY d.doc_type, p.element_type ORDER BY d.doc_type, p.element_type;

-- chunk_flag distribution
SELECT chunk_flag, COUNT(*) as count
FROM provisions GROUP BY chunk_flag ORDER BY count DESC;

-- condition_stack depth distribution
SELECT jsonb_array_length(condition_stack) as depth, COUNT(*) as count
FROM provisions WHERE condition_stack IS NOT NULL
GROUP BY depth ORDER BY depth;

-- jurisdiction distribution
SELECT jurisdiction, COUNT(*) as count
FROM provisions GROUP BY jurisdiction ORDER BY count DESC;

-- context_text populated check
SELECT
  COUNT(*) FILTER (WHERE context_text IS NOT NULL) as with_context,
  COUNT(*) FILTER (WHERE context_text IS NULL) as without_context
FROM provisions;
```

Record all results in session8_handoff.md before closing Session 7.

### 5. decisions_log.md and project_plan.md updates
Update both to reflect Session 7 decisions.

---

## Phase 1 Completion Criteria
(Checklist to verify before moving to Phase 2)

- [ ] All 120 documents at status = 'transformed'
- [ ] Zero documents at status = 'raw' or 'extracted' (unless explicitly
      excluded with documented rationale)
- [ ] context_text populated on all provision records
- [ ] chunk_flag populated on all provision records
- [ ] jurisdiction populated on all provision records
- [ ] Chunking report reviewed; edge case distribution understood
- [ ] No silent omissions: every source element accounted for in at least
      one extracted_unit record or explicit exclusion log
- [ ] All pipeline stages idempotent (verified by re-running on 5 documents)
- [ ] decisions_log.md updated through Session 7

---

## Deferred (not Session 7)

- Post-pilot adjudication model
- Front-end scope (Phase 2) — technology and hosting decisions
- Four Hohfeldian correlatives — second annotation pass
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale
- Clustering sensitivity analysis
- k-means parameter selection
- pgvector extension installation (Phase 3/4)
- Temporal field population (effective_date, superseded_by) — opportunistic
- State legislative ingestion (LegiScan/OpenStates) — separate source family,
  separate scoping session; jurisdiction field is forward-compatible
- **Phase 2 scoping session** — required before any Phase 2 work begins.
  A dedicated session to decompose "Phase 2: front-end" into discrete,
  sequenced phases and to complete the security/legal review that gates
  all of them. Three workstreams:

  1. Security/legal review: user data storage, API terms of use (Congress.gov,
     Federal Register), advertising data flows, threat model for a civic
     tech tool that scores legislation ideologically.

  2. Phase decomposition: "Phase 2" as currently described contains multiple
     distinct product surfaces that likely belong in separate phases:
     - Mode A (document browser) — read-only, no annotation required, ships early
     - Mode B (search) — requires pgvector and embedding pipeline
     - Mode C (temporal traversal) — requires temporal chain populated
     - Ideological visualization — requires Phase 3 annotation coverage
     - Legislator profiling / says-vs-does — requires legislator data joins
       (feasibility not yet validated — see below)
     The scoping session assigns phase numbers and sequences these explicitly.

  3. Feasibility checks: legislator data joins are explicitly unresolved in
     the project plan. Validate before sequencing phases that depend on them.

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