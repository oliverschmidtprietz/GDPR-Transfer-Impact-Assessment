# Changelog — tia

All notable changes to this skill are documented here.

Format: `## [vX.Y] — YYYY-MM-DD`

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
