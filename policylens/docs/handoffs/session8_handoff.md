# PolicyLens — Session 8 Handoff
## Complete Decisions Log (Sessions 0–7) + Session 8 Agenda
*Paste this entire document at the start of the next chat.*

---

## Strategic Context (updated Session 8)

**Phase 1 complete as of Session 7.** 120/120 documents at status='transformed'.
943 provisions written. Pipeline fully implemented through Layer 2b.

**Session 8 was the product scoping session.** No code was written. The output
is a validated product strategy and a revised phase structure. The session 7
handoff framed Session 8 as a technology and security scoping session; that
framing was superseded — the correct starting point was product strategy, which
then determines technology choices, not the reverse.

**Core product framing decided in Session 8:**
- PolicyLens is a product, not purely a platform, but built API-first so the
  UI is the first client of the API — not the other way around.
- The API is the contract. The UI is a consumer of it. No UI decision drives
  the data model. This means Persona 2 (data builders) can integrate against
  the API without being affected by UI changes.
- Party/ideological alignment remains a derived output, never an input label.
  Editorial neutrality is the core trust signal for all three personas.

---

## Persona Definitions (decided Session 8)

**Persona 1 — The Overwhelmed Citizen**
Somewhere in the middle politically. Finds all available information
overwhelming. Wants a source of truth. Does not do deep research but wants
to trust that someone has. Core problem is not access — it is trust. Cannot
verify what is actually in a bill versus what someone is saying about it.
Arrives with a vague topic ("what does the new immigration order actually
say?"), has maybe 5 minutes. The editorial neutrality constraint is the entire
reason they would use PolicyLens over anything else. Journey is pull, not
push: something happens in the news, they want to verify, they land here.

**Persona 2 — The Data Builder**
Builds on top of the corpus programmatically. Use cases include: training
models, building prediction markets, simulating policy scenarios, joining with
external data, gamifying politics, building polls, automating social content,
powering policy newsletters, constituent engagement tools. Does not need a
beautiful interface — needs reliable schema, stable identifiers, good corpus
coverage, and terms of use that permit building on top. The provision ID
format, context_text field, and Hohfeldian structure are the product for them.
The API is their entry point, not the UI.

**Persona 3 — The Researcher / Journalist**
Formal consumption. Tracks trends over time, informs studies, needs citeable
sources. Needs to trust the methodology, not just the output. Will want to
understand how provisions are classified, what the constitutional baseline is,
and where the edge cases are. Uses both the UI and the API. Needs methodology
disclosure rigorous enough to reference in a footnote or a published study.

**Key relationship between personas:**
Persona 1 is an end user of a downstream product that Persona 2 could build
on top of PolicyLens. PolicyLens building the Persona 1 UI directly does not
create debt for Persona 2 as long as the API is the contract and the UI is
a consumer. The Persona 1 UI is also proof that the API works, and provides
the vanity/tangibility signal useful for early product development and
attracting builders.

---

## Critical Gap Identified: chunk_flag Resolution (Session 8)

**The problem:** 469 of 943 provisions (50%) carry a chunk_flag other than
'clean'. These were correctly flagged by the normalizer — the machinery worked
as designed. But an unresolved flag queue means the corpus is not yet
trustworthy enough to be the source of truth that Persona 1's value
proposition requires. This gap was underweighted in prior sessions because
the pipeline framing dominated; it must be resolved before any user-facing
surface ships.

**Flag breakdown:**
- review_boundary (349): chunking uncertainty — em-dash stubs, bare fragments
- review_cross_reference (120): inline USC citations present; reference not
  yet resolved into legal_addresses / provision_references

**Resolution strategy (decided Session 8):**

Layer 1 — Deterministic fixes (priority, before any LLM involvement):

  Em-dash stubs: The USLM XML structure is known. The stub always has child
  nodes containing the operative content. Deterministic merger: concatenate
  the stub with its immediate children in order. Structural fix, no model
  needed.

  Bare noun phrase fragments: Walk up section_path until a unit with a finite
  verb and modality is found. Attach fragment as a list item under that parent.
  USLM nesting makes this traversal well-defined. Structural fix, no model
  needed.

  Inline cross-references (review_cross_reference): These are not chunking
  problems — the provision text is correctly bounded. Resolution is reference
  extraction: parse the USC citation, upsert to legal_addresses, insert
  provision_references junction record. Flag clears when reference is resolved.
  Deterministic extraction task.

Layer 2 — LLM agent pass on residual: Whatever remains genuinely ambiguous
after deterministic fixes — provisions where boundary judgment requires
understanding legal meaning, not just XML structure — is the correct input
for an LLM agent review pass. This residual set is expected to be small.
This is not annotation work (Phase 3); it is chunk boundary validation.

**Implementation:** A new pipeline stage — `chunk-resolve` — runs after
`chunk-normalize` and before any user-facing surface. Deterministic resolution
first, LLM agent pass on residual. Output: corpus where chunk_flag='clean'
is genuinely earned.

---

## Corpus Expansion (decided Session 8)

**Decision: ingest everything.**

Full Federal Register PRESDOCU back catalog (all executive orders, notices,
proclamations, determinations going back decades) and full Congressional USLM
back catalog (all bills and resolutions from the 93rd Congress onward). Both
sources are already wired. No new extractors required. This is a scale
operation on existing infrastructure, not new build work.

**Rationale:**
- API rate limits are an engineering throttle, not a scope constraint.
- Storage cost is negligible (decisions log Session 4 established this).
- Full back catalog makes the temporal chain meaningful — legal address
  evolution across administrations becomes queryable.
- Full coverage is what makes RAG and agent use cases genuinely valuable,
  not just incrementally better. A RAG query can retrieve provisions across
  the full legislative history. An agent can traverse the temporal chain
  via superseded_by across real version history.
- context_text was designed for embedding stability from the start. Expanding
  the corpus does not require rethinking the embedding strategy.

**Sequencing constraint:** Corpus expansion runs after chunk-resolve is
proven stable. Run a stress test at ~500 documents before opening the
throttle to the full back catalog. This surfaces extractor edge cases that
did not appear at 120 documents before they multiply.

---

## Phase Structure (revised Session 8)

### Phase 1 — Chunk & Store ✅ Complete (Session 7)
See project_plan.md for full record. One carry-forward:
- ⬜ migrate_session7_jurisdiction_backfill.sql committed to repo (Session 9
  task — SQL is written in session 7 handoff)

### Phase 2 — Pipeline Hardening + Corpus Expansion + Lightweight UI

Three workstreams, with dependency order:

**2a — chunk-resolve pipeline stage**
Deterministic merge pass (em-dash stubs, bare fragments, cross-reference
extraction), then LLM agent pass on residual. Output: corpus where
chunk_flag='clean' is trustworthy. Must complete before UI ships to real
users.

**2b — Corpus expansion**
Full Federal Register PRESDOCU back catalog + full Congressional USLM back
catalog. Runs after chunk-resolve is proven stable. Stress test at ~500
documents before full scale.

**2c — Lightweight UI**
Search and provision reading experience. Built as a clean consumer of the
API — no UI decision drives the data model. Can be built in parallel with
2a and 2b but does not ship to real users until 2a is complete and 2b has
meaningful topic coverage.

**Topic coverage threshold for UI launch:** Not a document count target.
Coverage of the major policy domains Persona 1 arrives with: immigration,
healthcare, taxation, education, firearms. Search on any of those topics
must return a meaningful, trustworthy result set before the UI is opened
to users.

**Technology decisions:** Deferred to Session 9. Technology follows from
the user experience requirements; scoping the UI journeys first is the
correct order. Security and legal review also deferred to Session 9 —
conducted against the concrete UI plan, not in the abstract.

### Phase 3 — Annotation Pipeline
Model-primary annotation. IRR pilot, stratified sample check. Populates
domain, valence, subject_type, modality on provision records. Unblocks
all annotation-dependent features.

### Phase 4 — Semantic Search
pgvector, embedding job on context_text, vector similarity search. Significant
infrastructure addition — its own phase. context_text field already designed
for this; no schema changes needed.

### Phase 5 — Annotation-Aware Filtering + Ideological Visualization
Requires Phase 3 complete. Domain/valence filters, 2D liberty-space
visualization, document-level ideological profiles.

### Phase 6 — Clustering and Analysis
k-means projection, party alignment validation, sensitivity analysis.
Requires Phase 5 data coverage.

### Deferred (no phase assigned)
- Temporal traversal (Mode C) — opportunistic; populate effective_date /
  superseded_by as data allows; surface in UI when chains exist
- Legislator profiling / says-vs-does — feasibility partially validated
  (House roll call votes available via Congress.gov API beta from 118th
  Congress onward; Senate votes require separate source); sequence after
  Phase 3; House-only at launch is acceptable
- State legislative ingestion (LegiScan/OpenStates)
- Four Hohfeldian correlatives — second annotation pass
- Graph promotion of typed metadata fields
- Versioning and re-tagging strategy at scale
- Clustering sensitivity analysis / k-means parameter selection
- pgvector installation (Phase 4)
- db/__init__.py singleton refactor — required before Phase 2 web tier;
  replace global pool with explicit create_pool(dsn) factory

---

## Decisions Log — Sessions 0–7

*(Full text in decisions_log.md in repo)*

Sessions 0–4: Provision definition, ontology, clustering mechanism,
constitutional baseline, annotation strategy, pipeline architecture,
ExtractedUnit as persisted intermediate, LegalAddress as first-class entity,
context_text, temporal fields, boilerplate classification, doc_status enum,
pipeline idempotency.

Session 5: Extractor dispatch registry, deferred psycopg import, element_type
assignment boundary, provision ID separator, proclamations produce zero
provisions (expected), bare noun phrase list items (Finding 4).

Session 6b: jurisdiction_scope field added to ExtractedUnit; two-layer
jurisdiction design; migrate_session6b.sql applied.

Session 7: Atomicity heuristic (em-dash stubs, bare fragments, definition
block intros); element_type override extension to header; boilerplate child
inheritance; context_text section_path fallback; inline citation detection;
jurisdiction_scope backfill (20 rows, 11 documents). Full corpus results:
943 provisions, 120/120 documents transformed.

---

## Session 9 Primary Agenda

### 0. Carry-forward from Session 7
Commit migrate_session7_jurisdiction_backfill.sql. SQL content is in the
session 7 handoff. Create the file, commit, done.

### 1. UI journey mapping for Phase 2c
Before any technology decisions, map the Persona 1 user journey through
the lightweight UI. What do they arrive with? What do they see? What does
a successful session look like? What do they leave with? Features fall out
of the journey, not the other way around.

### 2. Technology decisions (after journey mapping)
Web framework, hosting, frontend architecture, DB connection from web tier,
CI/CD. Decided against the concrete journey requirements, not in the abstract.

### 3. Security and legal review
Conducted against the concrete Phase 2 plan. Key areas: API terms of use
(Congress.gov, Federal Register), user data storage (anonymous-first
strongly preferred for Phase 2), advertising data flows (contextual only —
Carbon Ads / Ethical Ads; no behavioral or political advertising), threat
model (methodology transparency as primary defense; full methodology
disclosure is load-bearing for Persona 1 trust and Persona 3 citability).

### 4. chunk-resolve design
Design the deterministic merge pass before writing any code. Review the
actual flagged provisions in the DB to confirm the merge heuristics are
correct before implementing. Empirical grounding first — same sequencing
discipline as Session 7 atomicity heuristic.

### 5. decisions_log.md and project_plan.md updates
Update both to reflect Session 8 decisions.

---

## Standing Rules

- Every decision entry must include a rationale.
- Deferred items carry forward verbatim until decided or explicitly dropped.
- New open questions surfaced in a session are added to the next session's
  agenda before the session closes.
- The handoff document is the single source of truth.
- **Implementation review:** before any implementation decision, evaluate
  from the perspectives of data engineer, product manager, data scientist,
  UX, and user journey. Assess feasibility and testability explicitly.
- **Incremental test suite:** after each implementation change, write
  tests before moving to the next task. Tests are never deferred.
- **Security and legal:** a standing consideration at every session.
- **User journey before technology:** feature and journey design precedes
  technology selection. Technology serves the user experience, not the
  reverse. This rule was established in Session 8 after technology
  considerations were incorrectly prioritized over product strategy.