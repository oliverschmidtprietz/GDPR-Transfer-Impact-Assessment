# Changelog — tia

All notable changes to this skill are documented here.

Format: `## [vX.Y] — YYYY-MM-DD`

---

## [v1.8] — 2026-10-02

Break-it test 2026-10-02 fix wave (adversarial probe pass against the
shipped v1.7 validator; `LEDGER.md`'s tia lines). Seven findings: one
cross-cutting crash, two validator holes, and four legal-content/instruction
issues.

- **`_load_json` now catches `UnicodeDecodeError` (exit 2).** A sidecar
  containing invalid UTF-8 bytes raised an uncaught `UnicodeDecodeError`
  from `path.read_text()` — a raw traceback on stderr and exit 1 (colliding
  with "blocked"), even though `SKILL.md`/`validate.py` document exit 2 for
  unreadable input. `UnicodeDecodeError` is a `ValueError` subclass, not an
  `OSError`, so it slipped past the existing guard.
- **New rule `DEST-CRITERION3` (rejection).** `step1.destination_country`
  being an EU/EEA state (fixed EU27 + IS/LI/NO list, matched
  case-insensitively against the ISO alpha-2 codes already used throughout
  the sidecar/fixtures) while `transfer_qualification.criterion_3.met` is
  `true` is a direct self-contradiction — criterion 3 requires the importer
  to be in a *third* country.
- **`DPF-EVIDENCE` short-circuit fixed.** Previously only checked
  `dpf_reliance` when it was present, so `mechanism: adequacy` with
  `destination_country: US` and `dpf_reliance: null` passed silently — but
  the EU has no general US adequacy decision, only the Data Privacy
  Framework for certified recipients. The rule now also fires (warning) on
  that specific combination even when the `dpf_reliance` block is entirely
  absent.
- **New rule `SIGNOFF-DATE-PLAUSIBILITY` (rejection).**
  `step5_6.sign_off.{assessor,dpo}.date` must not precede `cover.date`
  (sign-off cannot predate the assessment it signs off) and must not be
  more than 730 days after it (implausibly far in the future — e.g. a
  typo'd year). Unlike `REVIEW-DATE`'s forward interval, there is no
  rationale field that could make an extreme sign-off date legitimate, so
  both directions reject rather than warn.
- **Legal correction: Art. 5/24/32 "remain mandatory" is criterion-specific,
  not universal.** `SKILL.md` and `references/transfer-qualification.md`
  previously said Art. 5/24/32 "remain mandatory" whenever *any* transfer-
  qualification criterion fails. Verified against EDPB Guidelines 05/2021
  v2.0 Section 4 (full PDF fetched and checked): that passage presupposes
  the exporter is still subject to the GDPR under Art. 3 (i.e. criterion 1
  is met) — it only addresses criterion 2/3 failures (e.g. an employee
  travelling abroad, or Art. 3(2) direct collection). When criterion 1
  itself fails, the GDPR does not apply to that processing at all, so
  Art. 5/24/32 are not "mandatory" by virtue of it. Both files now state
  the criterion-specific consequence explicitly.
- **New Step 2 check: SCC vintage.** `SKILL.md` and
  `references/edpb-six-steps.md` now require confirming that any SCCs
  relied on are the 2021 set (Commission Implementing Decision (EU)
  2021/914 of 4 June 2021). Verified against the decision's Art. 4: the
  earlier sets (Decision 2001/497/EC, Decision 2010/87/EU) were repealed
  with effect from 27 September 2021, and contracts executed on them could
  be relied on only until 27 December 2022 — after that date they provide
  no safeguard at all. A contract still citing an old set, or with no
  execution date on file, is now an explicit open-unknown trigger, not an
  assumed-current mechanism.
- **New anti-pressure instruction.** `SKILL.md`'s Required Facts section
  now explicitly states that a request to skip Required facts, or to
  declare a transfer compliant without running the assessment, is
  declined — the deliverable becomes "not assessed — required facts
  withheld" with the gap recorded as an open unknown, regardless of
  urgency or seniority cited.
- **Disclaimer clarified.** `SKILL.md` and `README.md` now state plainly
  that a passing validator run means the sidecar is internally consistent
  and complete, not that the underlying legal analysis is correct.
- `sources.lock.json`: `references/transfer-qualification.md` and
  `references/edpb-six-steps.md` entries re-verified 2026-10-02 (see notes
  for the primary-source checks performed).
- Test suite: 233 → 248 tests (15 new: 1 CLI crash-fix test, 11 new
  `DEST-CRITERION3`/`SIGNOFF-DATE-PLAUSIBILITY` consistency-rule tests, 3
  new `DPF-EVIDENCE` tests — see `tests/test_tia_cli.py`,
  `tests/test_tia_rules_consistency.py`, `tests/test_tia_rules_freshness.py`).

## [v1.7] — 2026-09-18

Author decision (A), 2026-09-18, after Codex consultation (`docs/projects/gdpr-skills-marathon/CODEX-CONSULTATION-2026-09-18-answer.md` §Q1): the tia→ropa hand-over delta file becomes MANDATORY, enforced in code, closing F-13 (the interchange delta contract had never been exercised end to end across three journey runs).

- **`DELTA-FILE-REQUIRED` (rejection, non-overridable) replaces `DELTA-REF-MISSING` (warning).** `ropa_delta.emitted: true` now requires a real `--delta` file to be supplied to the validator AND the sidecar's own `delta_ref` to resolve, relative to the sidecar's directory (or as-is if absolute), to that exact file. A prose `delta_ref` ("no separate file was queued...") or one naming a different file is now a hard rejection, not a warning. The mismatch message was also tidied so a long prose `delta_ref` is echoed once (truncated with an ellipsis past ~80 chars), not doubled into a nonsense resolved path.
- **`DELTA-SHAPE` strengthened and made non-overridable.** Now requires exactly two patches targeting exactly one transfer index, with the `tia_ref` patch value matching `cover.tia_ref` and the `tia_date` patch value matching `step5_6.sign_off.dpo.date` (the TIA's completion date — the field chosen as the single unambiguous "completed assessment date," since the sidecar has no field literally named that).
- **F-12 fixed.** `validator/validate.py` gained the PEP 723 inline-metadata launcher header ropa's already had — `uv run skills/tia/validator/validate.py ...` now works with zero prior `pip install` steps.
- Docs synced: `SKILL.md`'s Outputs and Cross-Skill Integration sections state the mandatory contract; `references/interchange-delta.md`'s Producer-Side Responsibilities gained an explicit statement of the mandatory, non-overridable contract, plus a clarification of how `delta_ref` resolves and which sidecar field `tia_date` comes from.

See `docs/superpowers/plans/2026-09-18-mandatory-delta-handoff.md` for the full implementation plan and `docs/projects/gdpr-skills-marathon/NEXT-SESSION.md` ("Session of 18 September 2026 (session 2)") for the decision record.

**2026-09-24 — journey run 4 fix wave (`docs/projects/gdpr-skills-marathon/journeys/transfer-review/JUDGMENT-RUN-4.md`), author decisions, small fix wave, no version bump:**

- **`DELTA-FILE-REQUIRED` now tolerates ropa's own documented `applied/` move.** ropa's merge mode moves a successfully-applied delta from `<inbound>/X.delta.json` to `<inbound>/applied/X.delta.json`; the sidecar's `delta_ref` recorded at emission time necessarily still names the pre-move path afterwards, and the rule was rejecting that genuine, correctly-completed hand-over (run-4 defect: independently reproduced against the clean room's real, final `inbound/applied/` file — rejected before this fix). The rule now also passes when `--delta` resolves to `<delta_ref's directory>/applied/<same filename>`, or, symmetrically, when `delta_ref` already names the `applied/` location and `--delta` is re-run against the original pre-move path. A different filename, or any other sibling directory, still rejects. `references/interchange-delta.md` and `SKILL.md` updated to describe the tolerance; no separate instruction to edit `delta_ref` after the move ever existed, so none needed removing.
- **`source_skill` version-stamping made explicit.** A live run-4 emission wrote `source_skill: "tia v1.1"` while the running skill was v1.7 — a stale literal that propagated verbatim into RoPA's `transfers_provenance.source`. `references/interchange-delta.md`'s Producer-Side Responsibilities gained an explicit numbered step: the version in `"tia v<X.Y>"` is read from this skill's own `SKILL.md` frontmatter `version:` at emission time, never hardcoded or copied from a historical mention elsewhere in the same document. No Python emitter exists for this delta (it is producer-instructed, not code-generated), so there was no mechanical stamping to add; confirmed ropa's `TRANS-TIA-DELTA` rule and inbound schema do not themselves pin any tia version.

## [v1.6] — 2026-09-15

Adversarial-review remediation (external Codex review 2026-09-08, triaged
2026-09-09/10, findings 9–12; author rulings 2026-09-15: R-unknown,
R-conditions):

- **`REVIEW-DATE` now also rejects a negative interval** —
  `next_review_date` before `cover.date` (a review scheduled before the
  assessment it reviews) is a rejection, not merely a warning; the
  >12-month-without-rationale case stays a warning. (Codex finding 5.)
- **Malformed `overrides[]` no longer crashes the run.** A top-level
  `overrides` that is present but not a list (e.g. `overrides: 42`) used
  to raise `TypeError` before any rule ran; it is now treated as "no
  valid overrides" and SCHEMA-0 reports the shape violation as a normal
  finding. (Codex finding 3, tia's share.)
- **`--emit-core-artefact` falls back to a minimal blocked artefact** if
  the projection adapter itself raises — a defense-in-depth net; the
  report on stdout and the exit code are unaffected. (Codex finding 3.)
- **`step2.mechanism: "unknown"`** (schema + `MECHANISM-UNKNOWN` rule):
  an honest not-yet-determined transfer basis, instead of a mechanism
  guessed from an unconfirmed importer domicile. Warning while the
  assessment is a draft; escalates to a rejection once Assessor + DPO
  sign-off is complete — the transfer basis must be documented before
  sign-off (Chapter V). (Finding 11, ruling R-unknown.)
- **`step4.decision: "proceed_with_conditions"`** (schema + top-level
  `conditions[]` ledger + `DECISION-CONDITIONS` rule): a decision value
  and evidenced-conditions ledger for the "proceed, but not every measure
  is implemented yet" case the schema previously had no honest home for.
  A plain `proceed` now rejects if any supplementary measure is not
  `implementation_status: implemented`; `proceed_with_conditions` rejects
  with no recorded `conditions[]`; open conditions are listed (warning,
  not a rejection — the assessment is legitimately conditional) until
  each is recorded `met` with evidence, at which point the finding
  suggests finalising the decision to `proceed`. The core-artefact
  projection surfaces the unknown mechanism and every open condition in
  `unknowns[]`; `outcome.status` stays `provisional` (the standard's
  closest existing value to "conditional" — its `outcome.status` enum has
  no dedicated conditional/incomplete value) rather than `complete` while
  any condition is open. (Finding 12, ruling R-conditions.)
- **Provenance rule sharpened**: `user-confirmed` is reserved for a fact
  the user literally stated in answer to a question; anything inferred,
  derived from public knowledge, or assumed is now a distinct **inferred**
  epistemic label, stated as such with its basis — never silently
  upgraded. (Finding 9 — a run defect, not a prior skill defect, but the
  rule itself was underspecified.)
- **Step-1 intake — special-category content in free-text fields**: the
  Required-facts set now always asks (1) which free-text/unstructured
  inputs are in scope, (2) whether any real control catches
  special-category content in them (a policy alone is not a control), and
  (3) whether such content has been observed in practice — with a rule to
  treat uncontrolled free-text channels as potentially special-category
  in both the Step-1 data description and the Step-3/4 risk assessment.
  (Finding 10.)
- `tia-sidecar-schema.json` moves to data-format **1.1** (additive;
  `tia_schema_version` accepts both `"1.0"` and `"1.1"`).
- New fixtures: `must_pass/proceed-with-conditions.json` (a conditional
  assessment with one open and one met condition) and
  `must_fail/DECISION-CONDITIONS__proceed-with-planned-measures.json`.

## [v1.5] — 2026-08-29

Ask-don't-guess release (GM-008 journey run 1, friction F-01/F-03/F-05):

- **Required facts — ask, never assume:** the EDPB Step 1–3 fact set
  (incl. sub-processors, key custody, government-access track record, and
  the EU/EEA-alternative question for every transfer) must be
  user-confirmed, verified, or an open unknown before analysis; a missing
  required fact is a question, never an assumption. The rich-context
  shortcut now covers only facts actually present in the context.
- **Epistemic labels:** every report claim is labeled user-confirmed /
  verified (with receipt) / assumption; unverified world-claims are
  written as open items, never as researched fact.
- **`SIGNOFF-INDEPENDENCE`** validator rule (warning): assessor and DPO
  sign-off by the same person is flagged; never blocks.
- **Front-door check:** requests broader than transfers route via
  `super-gdpr` when installed; adjacent obligations are named otherwise.
- README: PEP-668 note — run the validator via `uv run --with jsonschema`.

## [v1.4] — 2026-08-11

Adopts the Portfolio Standard (v1.2) — first adopter outside the
ropa/toms-art32 lineage, closing tia's §11 row: **validator,
sources.lock.json, core-artefact adapter, conformance.json**, plus the
native assessment-record sidecar those four presuppose
(`references/tia-sidecar-schema.json`, data-format 1.0).

- 18 registered rules: 16 numbered (blocking = 1–11 + 16 —
  incomplete/self-contradictory documentation; warnings = 12–15 — rule 12
  ONWARD-CHILD set to warning by author ruling 2026-08-09; aging rules
  13–15) plus two unnumbered — SCHEMA-0 (schema conformance, non-overridable)
  and DELTA-REF-MISSING (the no-reference-no-handoff warning, amendment
  2026-08-11). OVR-STALE is a runner-emitted finding id, not a registered
  rule. Documentation-not-correctness throughout.
- Overrides: any rejection overridable with a recorded reason
  (`passed_with_override`), refused in code for SIGNOFF-GATE — the frozen
  v2.0 delta cannot carry an override marker.
- First emitter of skill-artefact **1.1** (typed subject: `type: "transfer"`,
  `id` = native `tia_ref`, `org` = required org slug). `sources[]`,
  `handoffs[]`, `unknowns[]` populated from day one.
- `sources.lock.json` covers all 22 reference files incl. the 12 country
  profiles' inline citations (enumerated per entry).
- The inbound-schema-2.0 delta contract with ropa is untouched; rule 16
  re-checks only the delta's core shape at point of use.
- `tests/README.md` expected-count figure corrected (was stale at "127
  passed").
- Eval gate: no comparative re-run — machinery, not legal guidance
  (author ruling 2026-08-09; ropa v2.16 / toms-art32 v1.1 precedent).

---

## [v1.3] — 2026-07-25

Routes Article 32 security-of-processing work to the `toms-art32` skill. Part of the coordinated **sibling-routing pass** (`ropa` v2.15, `dpia-sentinel` v1.11, `dpa-art28` v1.2, `breach-sentinel` v3.3, `tia` v1.3) that closes the toms-art32 portfolio-integration gate recorded as Finding 1 in `docs/projects/gdpr-skills-marathon/ROADMAP-2026-07-25.md`. Routing pointers only — no Article 32 methodology is duplicated into any sibling.

- **Step 4 — Art. 32 boundary.** Chapter V supplementary measures are transfer-specific and stay here: they are selected against a *third-country access* gap under EDPB Recommendations 01/2020, not against general processing risk. The baseline Art. 32 posture, and the lifecycle of any measure once adopted, belong to `toms-art32`. An existing Art. 32 control may not be counted as a supplementary measure without showing it closes the identified third-country gap.
- **Cross-Skill Integration — Article 32 handoff.** Route to `toms-art32` for an accepted measure that now needs an owner, status and evidence (Step 5); for appropriateness-to-risk questions that are not about government access; and for Decision 2021/914 **Annex II** TOM text, which `toms-art32` generates from assessed, export-eligible state.

**Status:** reviewed (carried from v1.2) — routing/documentation only; no change to the transfer-qualification gate, the six-step pipeline, country profiles, or the inbound-schema 2.0 delta contract shared with `ropa`. Test suite unchanged.

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
