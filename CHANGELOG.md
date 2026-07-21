# Changelog — tia

All notable changes to this skill are documented here.

Format: `## [vX.Y] — YYYY-MM-DD`

---

## [v1.2] — 2026-07-21

The TIA→RoPA delta contract moves to **inbound schema 2.0**. `add` now upserts, determinism moves to an `expected_post_state` precondition, and patch paths are constrained to a declared allowed-path set. Coordinated release with `ropa` v2.14 — the two must move together.

**Why 2.0 and not 1.1.** The combined surface is narrowing, not widening. Relaxing `add` is widening for producers, but the allowed-path set and the precondition both *reject* payloads that 1.0 accepted — most importantly a delta from the shipped `tia` v1.1, which wrote four fields RoPA does not recognise. A 1.0 delta is now rejected outright rather than reinterpreted under 2.0 rules, because silent reinterpretation is the defect 2.0 exists to close.

**The merge semantics (decided 2026-07-21).**

- `add` **upserts** — it writes the value whether or not the leaf is present; `replace` is an exact synonym. The producer is stateless (it never reads RoPA's sidecar to choose an operation), a re-send is idempotent, there is no time-of-check/time-of-use window, and `add` now matches RFC 6902 §4.1, so the "RFC 6902 subset" label is accurate again and standard JSON-Patch libraries work on both sides.
- **`expected_post_state.values`** is a hard precondition: a mismatch **rejects** the whole delta (it was a warning). Declaring a value for a field the delta does *not* patch is the idiomatic concurrent-edit check.
- **The allowed-path set** is declared as the `path` pattern in `interchange-inbound-schema.json` and rejects the whole delta on any path outside it. With `add` permissive this is the primary guard on the register.

**Producer changes:**

- `references/interchange-delta.md` — the canonical example now declares `schema_version` 2.0, emits `add` for both leaves, and carries an `expected_post_state`. The first-write/later-write `replace` block is **removed**: there is no longer any reason for the producer to inspect leaf presence. The example's `rationale_doc_sha256` was a placeholder (`<sha256 hex of the docx>`) that failed the schema's `^[a-f0-9]{64}$` pattern — the documented artifact a model copies at runtime was itself schema-invalid, and is now a valid sample and validated by the suite.
- `SKILL.md`, `README.md`, `evals/evals.json`, `index.html` — aligned to 2.0. The landing page had continued to advertise the removed contract (`tia_status`, `supplementary_measures[]`, `tia_completed_date`, `tia_review_date`) after those fields were withdrawn; that page is published, so the correction ships with this release.

**Test suite — it can now fail.**

- Assertions are derived from the **documented example** and that example is run through the applier. The previous suite extracted only `path` and never `op`, and its one op assertion compared two static fixtures against each other — a tautology over test data. It stayed green when the exact defect it was written to eliminate was reintroduced.
- The applier reads the allowed-path set **from the JSON Schema** rather than from a constant in the test file, so the guarantee lives in the contract an adapter validates against.
- Verified by mutation: corrupting a patch path fails 10 tests; breaking a precondition value fails 5; reverting the applier to 1.0's strict leaf-presence fails 3. Flipping `add`↔`replace` is deliberately *not* a probe any more.
- `tests/README.md` added, recording the working invocation (`uv run --with pytest --with jsonschema …`) — the suite previously depended on undocumented local setup.
- The redundant `tia-result-first-write.json` / `tia-result-replacement.json` fixtures are removed; the documented example now covers both base states.

**Status:** reviewed (carried from v1.1).

---

## [v1.1] — 2026-05-31

US-surveillance currency refresh. The US country profiles are sharpened to reflect developments since the v1.0 source date (2026-05-29); methodology and country ratings unchanged.

- **FISA 702 status concretised.** `us-non-dpf.md`: the RISAA reauthorisation lapsed at the 20 April 2026 sunset; Section 702 is now operating on short-term extensions (clean 45-day extension to ~12 June 2026; no long-term deal; warrant reform unresolved). Still operative; the standing Step 6 monitoring trigger is retained with the next cliff dated.
- **PCLOB quorum collapse + SCOTUS added to Guarantee C.** Both `us-dpf.md` and `us-non-dpf.md`: the PCLOB lost its quorum in January 2025 (reinstatement ordered then stayed on appeal, deferred pending the Supreme Court), and *Trump v. Slaughter* (decision expected ~June 2026) may end for-cause removal protection for FTC/PCLOB members — degradations of the DPF's independent-oversight foundations that post-date the 2023 adequacy snapshot.
- **Latombe sharpened.** The EU General Court **dismissed** Latombe and upheld the DPF on 3 September 2025 (judging only the 2023 adequacy facts); the CJEU appeal (filed 31 October 2025) is pending. Reflected in the fragility and monitoring sections.
- **EDPB Guidelines 02/2024 (Art. 48) cited.** `sources.md`: a third-country authority's order is not itself a transfer/disclosure ground absent an international agreement — reinforces the CLOUD Act / compelled-disclosure analysis.
- **"Last verified" bumped to 2026-05-31** on the two US profiles only (the other country profiles are unchanged and remain at 2026-05-29).

**Status:** reviewed (carried from v1.0).

---

## [v1.0] — 2026-05-29

First reviewed release. Promoted from v0.9 after the iteration-1 skill-vs-no-skill eval benchmark.

### Benchmark (iteration-1)

- **Skill-vs-no-skill differential: +31.2pp** (with-skill **100.0% ± 0%** vs no-skill baseline **68.8% ± 27%**, mean per-eval pass rate across the 12 behavioural evals, graded against each eval's `expectations[]`). Upper end of the repo's historical accepted band (+6.41 to +35.5pp).
- With-skill passed **12/12 evals at 100%**; **no eval under-performed the baseline**. 10/12 evals showed a positive differential; 2 ties.
- Highest-value cases: eval-7 +100pp (emerging OLG München 21 U 3882/25 e case law the base model cannot know), eval-10 +50pp (RoPA interchange schema v1.0 + workspace machinery), evals 5/6/8 +37pp (four-essential-guarantees ratings, named supplementary-measure codes, CNIL Step-3 option-(3) documentation framework).
- The differentiator is skill-specific substance, not verbosity: gaps clustered on emerging/post-cutoff case law, cross-skill interchange/workspace conventions, and named structured frameworks + monitoring triggers.

### Notes

- **Non-discriminating evals (2, 11)** — baseline also scored 100% (foundational transfer-qualification and the encryption-gap honesty case). The skill does not lose there; these are candidates for sharpening in a future iteration, not promotion blockers.
- **Date-sensitive facts remain human-verification items before real client use** (not a benchmark blocker — the evals test reasoning, not live legal currency): OLG München 21 U 3882/25 e (11.05.2026); FISA 702 post-RISAA-sunset status (20 Apr 2026); UK Dec-2025 adequacy renewal. Each is already flagged inside the relevant country profiles as a monitoring/verification trigger.
- No skill content changed in this release; v1.0 reflects validation only.

---

## [v0.9] — 2026-05-29

Initial pre-review release.

### Added

- **SKILL.md** — routing table, session setup, transfer qualification gate, EDPB 6-step pipeline, Art. 49 balanced assessment path, 15 legal precision points.
- **9 core reference files** — `edpb-six-steps.md`, `essential-guarantees.md`, `transfer-qualification.md`, `art49-derogations.md`, `supplementary-measures.md`, `schrems-ii-holdings.md`, `tia-template.md`, `interchange-delta.md`, `sources.md`.
- **12 pre-built country profiles** — US (non-DPF), US (DPF), UK (post-adequacy), India, China, Brazil, Australia, Singapore, Turkey, UAE, South Africa, Russia.
- **Generic country questionnaire** — `generic-assessment.md` for countries without a pre-built profile.
- **12 behavioural test cases** in `evals/evals.json`.
- **Cross-skill integration with RoPA** — emits delta files conforming to RoPA's `interchange-inbound-schema.json` v1.0.

### Methodology

- **EDPB Recommendations 01/2020** v2.0 — six-step process as backbone.
- **EDPB Recommendations 02/2020** — four essential guarantees framework for Step 3 Block B.
- **EDPB Guidelines 05/2021** v2.0 — three cumulative criteria for the transfer qualification gate, with 12 example scenarios.
- **CNIL TIA Guide** (final version, January 2025) — structured assessment tables and the three-way Step 3 conclusion.
- **Rosenthal method** — pragmatic-lens influence on Step 3 Block C (focus on realistic risk to *this* data), without the statistical probability engine.
- **OLG München, 21 U 3882/25 e (11.05.2026)** — judicial counter-position on Art. 49(1)(b) for inherently international services.
