# interpretation_notes.md
# PolicyLens — Interpretation Notes
#
# Purpose: capture observations during implementation that will seed
# user-facing training documentation after Phase 2, when real annotated
# provisions are available as examples.
#
# This is NOT user-facing documentation. It is a working notes file.
# Audience: whoever writes the training docs later (probably you).
#
# How to use:
# When you encounter something during implementation or corpus review that
# a user would need explained — an edge case, a counterintuitive result,
# a good example of a concept — add a note here. Don't polish it.
# Just capture it with enough context to be useful later.
#
# Structure: dated entries under thematic headings. Add headings as needed.

---

## On Reading Provisions

**2026-06-07 — Proclamations vs. Executive Orders: the declaratory/deontic distinction**

When users first encounter PolicyLens, they may be surprised to find that
presidential proclamations show no provisions — just context/preamble text.
This is not a gap in the system. It reflects a real and legally meaningful
distinction between document types.

An executive order is a directive. It tells someone to do something, permits
something, or prohibits something. "The CDC shall review the vaccine schedule."
"Each agency must ensure compliance." These sentences have a subject (CDC,
each agency), a modality (duty: shall, must), and an object (reviewing the
schedule, ensuring compliance). That's a provision.

A proclamation is a declaration. "I hereby proclaim May 8 as Victory Day for
World War II." No one is being told to do anything. No one is being given a
permission or a power. The President is performing a speech act — announcing
something to the world — not issuing a legal directive. There is nothing to
parse into a 〈subject, modality, object〉 triple because there is no modality.

The practical upshot for users: if you're looking for what the government is
legally required or permitted to do, proclamations are not the right document
type. If you're tracking ceremonial designations, commemorations, or public
announcements, proclamations are exactly right — but PolicyLens will show you
the text as context rather than as parsed provisions, because that's what it
is.

A good analogy: a proclamation is like a press release. An executive order is
like a policy memo. Both come from the same office, but one is communication
and one is instruction.

**Corpus evidence (Session 5, 2026-06-07):** All 8 presidential proclamations
in the 120-document corpus extracted as preamble-only. All 5 executive orders
produced provision_candidates. This pattern is expected to hold across a
larger corpus — it reflects the inherent nature of these document types, not
a quirk of this particular sample.

---

## On the Hohfeldian Framework

*(Notes on how duty/permission/power/immunity play out in real legislative
text. Cases where the modality was non-obvious. Good plain-language
analogies for each term.)*

---

## On Valence Scoring

*(Notes on what −2, −1, 0, +1, +2 look like on real provisions. Cases
where the score was counterintuitive. The subject-inversion cases
(Cross-rule A) are likely to need the most explanation — a duty on
government scoring as a positive for citizens is not obvious.)*

---

## On Constitutional Baselines

*(Notes on cases where the baseline mattered — where the same provision
would score differently under a different baseline. The Dobbs sub-domain
is likely to generate the most notable examples.)*

---

## On Boilerplate vs. Substantive Provisions

**2026-06-07 — The preamble/boilerplate/provision trichotomy**

Users in the document reading view will encounter three types of text that
look similar on the surface but are treated differently by the system:

Preamble ("By the authority vested in me as President by the Constitution
and the laws of the United States..."): This is the opening formula of
executive orders and similar documents. It establishes the legal basis for
what follows but doesn't itself impose any obligation or grant any permission.
PolicyLens displays it as context. It's the legal equivalent of "whereas"
clauses in a contract — scene-setting, not operative.

Boilerplate General Provisions ("This order is not intended to, and does not,
create any right or benefit, substantive or procedural, enforceable at law
or in equity by any party against the United States..."): This IS deontic
content — it's an immunity clause. It limits what legal claims can be made
based on the order. PolicyLens stores it as a provision record but tags it
as boilerplate and classifies it domain:governmental_structure. It's visible
in the document reading view but excluded from ideological scoring. Users
should understand this text as real legal content that just happens to be
formulaic — it appears in nearly every executive order in identical or
near-identical form.

Substantive provisions: Everything else. These are the operative directives
that assign actual duties, permissions, and powers. These are what get scored
on the liberty axes.

The user-facing question to ask: "Does this text tell someone to do
something, allow something, or forbid something?" If yes, it's a provision.
If it's just establishing context or limiting liability in boilerplate
language, it's preamble or boilerplate respectively.

---

## On the Two-Axis Space

*(Notes on what the economic × social liberty visualization looks like
with real data. Cases that landed in unexpected quadrants. What the
axes feel like in practice versus in the abstract.)*

---

## Edge Cases Worth Explaining to Users

**2026-06-07 — "No provisions found" is a valid and informative result**

Users may interpret a document showing zero provisions as a system error.
Training documentation should proactively explain that certain document types
(proclamations, purely ceremonial resolutions) genuinely contain no deontic
content. The system correctly identifies this and displays it transparently.
The absence of provisions is itself information — it tells the user what kind
of document they are looking at.

Candidate language for the UI: "No deontic provisions identified in this
document. This document appears to be declaratory rather than directive in
nature. The full text is displayed below as context."

---

## Methodology Notes for Sophisticated Users

*(Notes aimed at researchers, journalists, or policy professionals who
will want to understand the methodology in depth — the DW-NOMINATE
borrowings, the CMP differences, the independence assumption, the IRR
protocol. These feed a methodology appendix, not the main user guide.)*

**2026-06-07 — Bare noun phrase list items: technically extracted,
semantically incomplete; resolved by deterministic merge in Phase 2**

During corpus inspection of extracted_units (Session 5), the deepest USLM
nesting (depth 6) produced units like this:

  section_path: {2.,(2),(B),(ii),(II),(aa),(AA)}
  raw_text: "the Defense Intelligence Agency;"

This is a single agency name — a bare noun phrase with no verb, no modality,
no subject-object relationship. It is technically a valid extraction (there
is a <text> element at this hierarchy level in the USLM XML), but it is
semantically meaningless in isolation. The legal obligation this text
participates in lives entirely in a parent provision several levels up —
something like "the following agencies shall comply with X: ... (AA) the
Defense Intelligence Agency."

**Why this matters for users:**
A user reading this provision would see "the Defense Intelligence Agency;"
with no context and no idea what it means. This is a failure of the reading
experience even if it is not a failure of extraction logic.

**How the system resolves this (Phase 2 — chunk-resolve):**
The normalizer flags these with chunk_flag = 'review_boundary'. In Phase 2,
the chunk-resolve pipeline stage applies a deterministic merge: walk up
section_path until a unit with a finite verb and modality is found, then
attach the fragment as a list item under that parent. The USLM nesting
structure makes this traversal unambiguous. After chunk-resolve, these
fragments appear as part of their parent provision rather than as isolated
cards.

**What training docs should explain:**
In deeply nested legislation, some list items only make sense when read with
their parent provision. PolicyLens resolves this automatically via the
chunk-resolve stage, but users looking at the raw corpus (e.g. via API)
before chunk-resolve has run may encounter fragments with chunk_flag =
'review_boundary'. These are accurately flagged — they are not ready for
display or analysis until resolved.

**Methodology note:**
The chunk-resolve deterministic merge is a structural operation, not an
editorial one. The system is not interpreting the meaning of the provision —
it is reconstructing the complete deontic proposition that the drafting
convention (USLM list enumeration) distributed across multiple XML nodes.
The merged provision is what the drafter wrote; the fragment was an artifact
of how the XML was structured, not a separate legal statement.

---

## On Editorial Neutrality

**2026-06-13 — Why PolicyLens does not editorialize and why that matters
to users**

PolicyLens shows what the law says. It does not tell users what to think
about it. This is a deliberate product decision, not a limitation.

The editorial neutrality principle means:
- Party alignment is derived from the text after analysis, never used as
  an input label during processing
- Provisions are scored on liberty axes anchored to constitutional baselines,
  not on whether they are "good" or "bad" for any group
- The source link to the government document is always present — users can
  verify every provision against the original

For Persona 1 (the overwhelmed citizen), this is the entire reason to trust
PolicyLens. Every other source of political information has an editorial
stance. PolicyLens's stance is: here is what the law actually says.

For Persona 3 (researchers and journalists), this is what makes the
methodology citeable. A study that references PolicyLens provision scores
needs to be able to explain that those scores are anchored to constitutional
baselines and derived from text, not assigned by editors with a point of view.

**User-facing implication:**
The methodology page is load-bearing for both these personas. It is not
marketing copy. It should explain the Hohfeldian framework, the constitutional
baseline choices and their rationale, the scoring geometry, and the
annotation validation protocol at a level of rigor that a policy researcher
would find credible. See decisions_log.md for the full rationale on each
of these choices.