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

Users in Mode A (document reading) will encounter three types of text that
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
in Mode A but excluded from ideological scoring. Users should understand this
text as real legal content that just happens to be formulaic — it appears in
nearly every executive order in identical or near-identical form.

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

**2026-06-07 — Bare noun phrase list items: technically extracted, semantically incomplete**

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
A user reading this provision in Mode A would see "the Defense Intelligence
Agency;" with no context and no idea what it means. This is a failure of
the reading experience even if it is not a failure of extraction logic.

**What the normalizer should do:**
Flag these with chunk_flag = 'review_boundary'. A bare noun phrase (no
finite verb, no modality marker) is a strong signal that the unit is a
list item fragment rather than a self-contained provision. The human
reviewer queue should surface these prominently.

**What training docs should explain:**
Some provisions in deeply nested legislation are intentionally fragmentary —
they are list items that only make sense when read with their parent. Mode A
must display these with sufficient parent context (at minimum the section
heading and the immediate parent provision text) so the fragment is
interpretable. A provision card that shows only "the Defense Intelligence
Agency;" with no parent context is not useful to anyone.

**Normalizer heuristic candidate (for Session 6):**
A unit is likely a bare list-item fragment if: (a) its raw_text contains
no finite verb, OR (b) its raw_text is under ~15 words and matches the
pattern of a noun phrase ending in a semicolon or comma. Flag as
review_boundary. Do not auto-merge — the parent structure needs human
confirmation.