# PolicyLens — Session 6 Handoff
## Complete Decisions Log (Sessions 0–5) + Session 6 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 5)

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
Session 6 implements Layer 2b (normalization).

**Artifacts in repo:**
- provision_schema.yaml — full provision record schema
- controlled_vocabulary.yaml — all enumerated field definitions + cross-rules
- baseline_doctrine.yaml — per-sub-domain constitutional baseline table
- decisions_log.md — rationale layer (updated Session 5)
- project_plan.md — phased project plan through Phase 5

---

## Decisions Log — Sessions 0–4

*(Full text preserved — see session5_handoff.md or decisions_log.md in repo)*

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
Additional indexes added: provisions(doc_id, provision_index),
provisions(chunk_flag), provisions(element_type).

**DECIDED: Provision id separator**
Provisions primary key format: {doc_id}|{section_id}|{provision_index}
Pipe character used as separator (not colon) to avoid ambiguity if
section_id contains a colon. Enforced in types.py id constructor.

**DECIDED: legal_addresses upsert pattern**
INSERT ... ON CONFLICT (statute, section) DO UPDATE SET statute =
EXCLUDED.statute RETURNING id — always returns id regardless of
insert or conflict path.

**DECIDED: element_type assignment responsibility**
Extractors assign: provision_candidate | preamble | header
Normalizer assigns: boilerplate (semantic judgment on provision_candidate units)
Extractors never assign boilerplate.

**DECIDED: FRPresdocuExtractor implementation complete**
Handles EXECORD, PROCLA, PRNOTICE, DETERM.
Section boundaries: <FP> containing <E T="04">.
Preamble: opening FP elements containing authority-vested formula.
Boilerplate tags stripped: PRTPAGE, GPH, PSIG, PLACE, DATE, FRDOC,
FILED, BILCOD, TITLE3, PRES.
Tested against EO 14407 and proclamation 2026-09506.

**DECIDED: USLMExtractor implementation complete**
Walks <legis-body> → <section> → <subsection> → <paragraph> (and deeper).
section_path from <enum> elements. source_element_id from id attributes.
Tested against 119-S-31 (bill) and 119-SRES-7 (resolution).

**DECIDED: chunk-extract CLI command implemented**
Dispatches by source field. Idempotent. Processes status='raw' documents.
Advances to status='extracted'.

**EXTRACTION OUTPUT** *(Session 5 corpus run — 2026-06-07)*

```
 source_schema |    element_type     | count | avg_depth | max_depth | with_citation
---------------+---------------------+-------+-----------+-----------+---------------
 fr_presdocu   | preamble            |   118 |      0.00 |         0 |             0
 fr_presdocu   | provision_candidate |   109 |      0.71 |         1 |             0
 uslm          | header              |   349 |      0.85 |         3 |             0
 uslm          | provision_candidate |   834 |      1.66 |         6 |             0
```

Total extracted_units: 1,410
Documents with extraction errors: 0
Max nesting_depth observed: 6 (uslm), 1 (fr_presdocu)
Provisions with legal_address_raw populated: 0 (expected — citations appear
  in prose text, not in structured XML attributes; normalizer will detect
  via regex in provision text for review_cross_reference flagging)

**Pre-normalization findings (review before Session 6 implementation):**

Finding 1 — Proclamations are entirely preamble (expected, not a bug):
All 8 presidential proclamations in the corpus extracted as preamble-only,
producing zero provision_candidate units. Proclamations are declaratory
documents ("I hereby proclaim X as Y Day") — they do not assign duties,
permissions, or powers to any subject. They have no deontic content and
therefore no provisions by definition. In the product, a user navigating
to a proclamation in Mode A will see the full text labeled as context/
preamble with a note that no deontic provisions were identified. This is
correct and informative — it tells the user something real about the
nature of the document. EOs and notices that continue national emergencies
DO contain operative legal clauses and extracted provision_candidates as
expected. See interpretation_notes.md for the user-facing framing of this.

Finding 2 — USLM nesting depth reaches 6:
Some bills have six levels of hierarchy (section → subsection → paragraph
→ subparagraph → clause → subclause). The 2-layer condition_stack collapse
rule applies to conditional logic within a provision, not to structural
hierarchy. Deep USLM nesting is handled correctly by recursive walking —
each level with a <text> child becomes its own extracted_unit. No
adjustment to the collapse rule needed.

Finding 3 — FR nesting depth max 1:
FR documents are structurally flat (section-level paragraphs and one level
of sub-paragraphs). Max depth 1 matches expectations from corpus inspection.

Finding 4 — Bare noun phrase list items at depth 6 (NEW — affects normalizer):
Corpus inspection of depth-6 USLM units (bill 119-S-23) revealed units with
raw_text like "the Defense Intelligence Agency;" — a bare noun phrase with
no verb and no modality. These are list items in a deeply enumerated
structure whose operative obligation lives in a parent provision several
levels up. They are technically correct extractions (a <text> element
exists at that hierarchy level) but semantically incomplete in isolation.
The normalizer needs an explicit heuristic to detect and flag these.
See normalizer atomicity heuristic section below — bare noun phrase
detection added as a fourth flag condition. See interpretation_notes.md
for the user-facing framing.

*The normalizer agenda below is a candidate design, updated to reflect
Finding 4. Review all findings above before implementation begins.*

---

## Session 6 Primary Agenda

### 0. Review extraction output (before writing any code)
Read the extraction output recorded above. Answer:
- What is the actual nesting_depth distribution? Does the 2-layer
  collapse rule need adjustment?
- Are there extracted_units with unexpectedly long or short raw_text
  that suggest extractor boundary errors?
- What fraction of units have legal_address_raw populated? Is this
  plausible given the document types?
- Any source_schema values other than 'fr_presdocu' and 'uslm'?
  (Should be none — flag if present.)
- Any documents stuck at status='raw' after extraction? Investigate before
  normalizing.

Decisions made in this review go in the decisions log before implementation.

### 1. Decide normalizer atomicity heuristic

**Candidate approach (updated based on corpus inspection — Finding 4):**

Phase 1 atomicity heuristic — flag chunk_flag = 'review_boundary' if any
of the following apply to the extracted_unit text:
- Contains more than one sentence with distinct grammatical subjects
  (heuristic: >1 occurrence of a subject-verb pattern with different subjects)
- Has condition_stack depth > 2 (mandatory per Session 3 decision)
- Contains a coordinating conjunction ("and", "or") connecting two
  independent clauses each with their own subject and verb
- Bare noun phrase detection (NEW — from corpus Finding 4): raw_text
  contains no finite verb AND is under ~15 words. These are list-item
  fragments whose operative obligation lives in a parent provision.
  Flag as review_boundary; do not auto-merge or auto-split.

This is an auditable heuristic, not a semantic judgment. The intent is
to surface candidates for human review, not to auto-split or auto-merge.
The normalizer flags; it does not restructure.

The bare noun phrase heuristic will fire on the depth-6 USLM units
observed in 119-S-23 and likely similar structures in other large bills.
Expect a meaningful number of review_boundary flags from this condition.

Record the decided heuristic in the decisions log before writing code.

### 2. Implement policylens/chunker/normalize.py

The normalizer is source-agnostic. It reads ExtractedUnit records from
the extracted_units table and writes to provisions, legal_addresses,
and provision_references.

**Input:** extracted_units rows for a given doc_id (status='extracted')
**Output:** provision rows, legal_address rows, provision_reference rows

**Processing steps per extracted_unit:**

Step 1 — Skip non-provision units
- element_type = 'preamble': skip (no provision record). Retain in
  extracted_units; will be queried for context_text construction.
- element_type = 'header': skip (no provision record).
- element_type = 'provision_candidate': proceed.

Step 2 — Boilerplate detection
Inspect text for General Provisions boilerplate patterns:
- "Nothing in this order shall be construed to impair or otherwise affect"
- "This order shall be implemented consistent with applicable law"
- "This order is not intended to, and does not, create any right or benefit"
- "The costs for publication of this order shall be borne by"
If matched: set element_type = 'boilerplate' on the provision record.
Otherwise: element_type = 'provision_candidate'.

Step 3 — condition_stack detection
Scan text for conditional antecedents:
- Existence condition: "if [noun phrase] exists", "in the event that"
- Threshold condition: "if [quantity] exceeds", "when [metric] reaches"
- Temporal condition: "upon", "after [date/event]", "before [date/event]"
- Other: any remaining "if", "unless", "provided that", "except that"
Build condition_stack as list of {condition_type, text} objects.
Set nesting_depth = len(condition_stack).

Step 4 — chunk_flag assignment
- condition_stack depth > 2: chunk_flag = 'review_nested_conditional'
- legal_address_raw is not None: chunk_flag = 'review_cross_reference'
  (unless already set to review_nested_conditional)
- Atomicity heuristic fires: chunk_flag = 'review_boundary'
  (lowest priority — only if no other flag set)
- Otherwise: chunk_flag = 'clean'

Step 5 — context_text construction
Query extracted_units WHERE doc_id = [this doc_id] AND
element_type = 'preamble' to get preamble text for the document.
Build context_text as:
  "[{doc_type} — {doc_title} — {section_heading}]
   {condition_stack_summary if non-empty}
   Text: {provision_text}"

Where condition_stack_summary = "Condition: {text}" for each entry,
joined by "; ".

Step 6 — legal_address resolution
If legal_address_raw is not None:
- Parse statute and section from the raw citation string
- Upsert to legal_addresses (ON CONFLICT DO UPDATE RETURNING id)
- Insert to provision_references with ref_type = 'references'
- Set chunk_flag = 'review_cross_reference' if not already flagged higher

Step 7 — provision_index assignment
Provisions within a section are ordered by their position in the
extracted_units table (ORDER BY id ASC within the section).
provision_index is zero-based within each (doc_id, section_id) group.

Step 8 — Write provision record
Construct id as "{doc_id}|{section_id}|{provision_index}".
INSERT INTO provisions ... ON CONFLICT (doc_id, section_id, provision_index)
DO UPDATE SET [all fields] WHERE the record has changed.

### 3. CLI — chunk-normalize command
Add to policylens/cli.py:

```
python3 -m policylens.cli chunk-normalize [--doc-id N]
```

Behavior:
- Without --doc-id: queries all documents with status='extracted'
- With --doc-id: processes single document (useful for testing and debugging)
- Reads extracted_units for each document, runs normalizer
- Writes provisions, legal_addresses, provision_references
- Advances document status to 'transformed'
- Idempotent: re-running on an already-transformed document is a no-op

Output: per-document summary (doc_id, doc_type, provisions written,
chunk_flag distribution). Final summary: total provisions written,
chunk_flag breakdown, element_type breakdown, pending count.

### 4. Full corpus run + chunking report
Run chunk-normalize on all 120 documents (status='extracted').
Generate and record the chunking report:

```sql
-- Provision totals by doc_type and element_type
SELECT
    d.doc_type,
    p.element_type,
    COUNT(*) as count
FROM provisions p
JOIN documents d ON p.doc_id = d.id
GROUP BY d.doc_type, p.element_type
ORDER BY d.doc_type, p.element_type;

-- chunk_flag distribution
SELECT chunk_flag, COUNT(*) as count
FROM provisions
GROUP BY chunk_flag
ORDER BY count DESC;

-- condition_stack depth distribution
SELECT
    jsonb_array_length(condition_stack) as depth,
    COUNT(*) as count
FROM provisions
WHERE condition_stack IS NOT NULL
GROUP BY depth
ORDER BY depth;

-- context_text populated check
SELECT COUNT(*) FILTER (WHERE context_text IS NOT NULL) as with_context,
       COUNT(*) FILTER (WHERE context_text IS NULL) as without_context
FROM provisions;
```

Record all results in this handoff before Session 7.

### 5. decisions_log.md and project_plan.md updates
Update both files to reflect Session 5 and Session 6 decisions.

---

## Phase 1 Completion Criteria
(Checklist to verify before moving to Phase 2)

- [ ] All 120 documents at status = 'transformed'
- [ ] Zero documents at status = 'raw' or 'extracted' (unless explicitly
      excluded with documented rationale)
- [ ] context_text populated on all provision records
- [ ] chunk_flag populated on all provision records
- [ ] Chunking report reviewed; edge case distribution understood
- [ ] No silent omissions: every source element accounted for in at least
      one extracted_unit record or explicit exclusion log
- [ ] All pipeline stages idempotent (verified by re-running on 5 documents)
- [ ] decisions_log.md updated with Session 5 and Session 6 decisions

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