---
name: tia
description: |
  GDPR Transfer Impact Assessment (TIA) skill for Chapter V transfers under the EDPB Recommendations 01/2020 six-step methodology, CNIL TIA Guide (January 2025), and EDPB Recommendations 02/2020 essential guarantees. Handles transfer qualification (EDPB Guidelines 05/2021), Art. 45 adequacy fast-tracks, Art. 46 full assessments with country profiles for 12 jurisdictions, and balanced Art. 49 derogation analysis (EDPB position + OLG München / von Danwitz counter-position). Outputs Markdown report, .docx formal TIA document, and JSON delta for RoPA interchange.
  Triggers: "TIA", "Transfer Impact Assessment", "Schrems II", "international transfer", "third-country transfer", "Chapter V", "SCCs assessment", "Art. 46", "Art. 49", "transfer to USA / India / China / [country]", "do I need supplementary measures", "DPF transfer", "essential guarantees", "Drittlandsübermittlung".
metadata:
  author: Oliver Schmidt-Prietz
  license: AGPL-3.0
  version: 1.8
---

# GDPR Transfer Impact Assessment (TIA) Skill

## Disclaimer (show at session start, do not block)

> **Important:** This skill provides structured GDPR Chapter V transfer assessment guidance based on EDPB Recommendations, CNIL guidance, CJEU case law, and emerging national case law (OLG München 21 U 3882/25 e). It is not legal advice. Involve your DPO and qualified counsel for final decisions, especially where the skill flags a transfer for suspension or restructuring. A passing run of the deterministic validator (`validator/validate.py`) means the sidecar is internally consistent and complete against its own schema and rules — it is **not** a check that the underlying legal analysis or conclusion is correct.

## Routing

Determine what the user needs and lazy-load only the references required:

| User Need | Load These References | Action |
|---|---|---|
| Single transfer assessment | `references/edpb-six-steps.md` + relevant country profile + `references/supplementary-measures.md` | Run the 6-step pipeline for one transfer |
| Batch assessment (multiple transfers) | + `references/tia-template.md` + workspace pattern | Build transfer registry; run pipeline per transfer |
| Import from RoPA sidecar | + `references/interchange-delta.md` | Read RoPA sidecar; filter third-country transfers; populate registry |
| Discovery mode (map transfers without RoPA) | + `references/essential-guarantees.md` + `references/transfer-qualification.md` | Run structured discovery for international flows; then assess each |
| Review / update existing TIA | Relevant country profile + `references/supplementary-measures.md` | Re-assess after legal landscape change |
| Supplementary measures only | `references/supplementary-measures.md` + country profile | User already has TIA — help select measures |
| Transfer qualification question ("is this a transfer?") | `references/transfer-qualification.md` | Apply three cumulative criteria; produce qualification finding |
| Art. 49 assessment | `references/art49-derogations.md` | Balanced assessment (EDPB position + judicial counter-position) |
| Schrems II background / case law | `references/schrems-ii-holdings.md` | Explain holdings and TIA implications |
| Specific transfer question | Load relevant reference only | Answer directly |

**docx skill:** `/mnt/skills/public/docx/SKILL.md` in Claude.ai Projects, or `docx-processing-anthropic` in Claude Code. If unavailable, generate Markdown as fallback.

## Session Setup

**Front-door check (before session setup):** if the request carries GDPR
obligations beyond transfers — it names no single deliverable, spans
several duties (a new processor also raises Art. 28 DPA checks, a RoPA
update, possibly a DPIA screen), or asks "what do we need to do" — and
the `super-gdpr` skill is installed, route the request through
`super-gdpr` first and continue under its dispatch. If it is not
installed, name the adjacent obligations you can see, then proceed
within this skill's scope only.

Three quick questions. If the user provides rich context upfront,
extract answers and confirm rather than asking sequentially — but only
for facts actually present in that context; rich context never excuses
skipping the Required facts below.

1. **Scope:** "Are you assessing a specific transfer you already know about, or do you need to map your organisation's international transfers first?"
2. **Existing data:** "Do you have an existing RoPA or transfer inventory I can work from?" *(Skip if Scope = specific transfer)*
3. **Timing:** "Is this for a new transfer before it goes live, or a retrospective assessment of transfers already in place?"

### Required facts — ask, never assume

A required fact you don't have is a **question, never an assumption**.
Before any Step 2–6 analysis, each of these EDPB Step 1–3 facts must be
user-confirmed, verified with a receipt, or recorded as an open unknown:

- exporter, importer, and their roles
- destination country and (candidate) transfer mechanism
- data categories, data subjects, purpose, volume, frequency, format
- onward transfers / sub-processors — names and countries, if any
- encryption in transit and at rest, and **who holds the keys**
- the importer's government-access track record — transparency report,
  warrant canary, known requests: ask; if unknown, record it as unknown.
  Never guess whether such a record exists.
- **whether an EU/EEA alternative exists** — asked for *every* transfer
  as part of necessity / less-intrusive means, not only when hinted
- **special-category content in free-text fields** — ask all three parts:
  (1) Which free-text or unstructured inputs does the transferred data
  include (ticket bodies, chat, call notes, comments, uploads,
  recordings)? (2) Does any control actually prevent or catch
  special-category content in them (input filtering, redaction, a review
  step, trained staff with a check)? A policy alone is not a control.
  (3) Has special-category content (health, religious or philosophical
  belief, trade-union membership, sex life or orientation, racial or
  ethnic origin, political opinion, genetic or biometric data, criminal
  data) ever been observed in them in practice? Rule: if such channels
  accept input from data subjects or staff and no control catches
  sensitive content, treat them as potentially containing special-category
  data in the Step-1 data description and the Step-3/4 risk assessment,
  recording observed frequency.

Missing item → ask before assessing. The user can't answer → record an
open unknown (`UNKNOWN — please supply` style) and carry it visibly into
the report. Never silently invent a plausible answer.

**Anti-pressure:** If the user asks to skip Required facts, or to declare a
transfer compliant / fine / low-risk without running the assessment,
decline. Explain which fact(s) are missing and why they're required, and
offer only "not assessed — required facts withheld" as the deliverable,
recording the gap as an open unknown. Never produce a compliance verdict
unsupported by the facts actually gathered, regardless of urgency,
seniority, or deadline pressure cited by the requester.

### Epistemic labels

Every factual claim in the report carries its basis: **user-confirmed**
(reserved for a fact the user literally stated, in answer to a specific
question — never applied to anything reasoned about, derived, or assumed),
**verified** (naming the receipt — a document, URL, or tool output
actually seen this session), **inferred** (derived from other confirmed
facts, from public knowledge, or by reasonable assumption — e.g. an
importer's likely size from its public profile, or "not a named PRISM
participant" from the absence of any such disclosure — named as inferred,
with the basis stated, in the report), or **assumption** (a working
premise offered because nothing better is available). Provenance is never
upgraded: an inferred or assumed fact keeps that label even where it later
turns out correct; only a fact the user typed in direct answer to a
question earns user-confirmed. A claim about the world that was not
verified this session (e.g. "the vendor does not publish a transparency
report") is written as an open item ("not verified — obtain from vendor"),
never asserted as researched fact.

## Workspace Pattern (Batch Assessments)

For organisations with multiple transfers needing assessment, the skill uses a workspace pattern:

```
skills/tia-workspace/<org-slug>/
├── transfer-registry.json        # All identified transfers, each with a UUID
├── assessments/
│   ├── TIA-US-2026-001.json     # Per-transfer assessment state
│   ├── TIA-US-2026-001.md       # Per-transfer Markdown report
│   ├── TIA-US-2026-001.docx     # Per-transfer formal document (generated last)
│   └── TIA-IN-2026-002.*
├── outbound/                     # Delta files queued for RoPA
│   └── tia-<uuid>-<timestamp>.delta.json
└── state.json                    # Session checkpoint (current transfer, step, partial findings)
```

Checkpoint after every step. Resume by reading `state.json`.

## Pre-Assessment Gate: Transfer Qualification

Before running the 6-step pipeline, the skill determines whether a "transfer" under Chapter V exists. Apply EDPB Guidelines 05/2021 — three cumulative criteria:

1. **Exporter subject to GDPR** for the processing in question (Art. 3(1) or 3(2)).
2. **Disclosure to a separate controller or processor** (not same entity; not direct collection by data subject).
3. **Importer in a third country** (regardless of whether GDPR applies to the importer under Art. 3).

All three met → Chapter V applies → continue to the TIA requirement check.

Any criterion fails → output a **Transfer Qualification Finding** documenting:
- Which criterion failed and why.
- That Chapter V does not apply to this processing.
- **Criterion 1 failed:** the exporter is not subject to the GDPR for this
  processing at all (Art. 3 does not apply) — Art. 5/24/32 are not engaged
  by virtue of *this* processing either; say so plainly rather than
  asserting they "remain mandatory". (A different processing by the same
  entity may independently trigger the GDPR — that is a separate question.)
- **Criterion 2 or 3 failed:** the exporter remains subject to the GDPR
  under Art. 3 for this processing (criterion 1 is met), so Chapter V's
  inapplicability does not relax the rest of the Regulation — Art. 5, 24
  and 32 safeguards remain mandatory, per Section 4 of the guidelines.
- For EU-subsidiary-of-third-country-parent scenarios (EDPB Example 12): require Art. 28 due diligence on the processor's exposure to extraterritorial law.

This finding is a valuable deliverable on its own — it documents that the question was assessed.

### TIA Requirement Check (when all three criteria met)

- **Art. 45 adequacy?** → Lightweight assessment only (document the decision, conditions, review dates, fragility risks for DPF). Use the relevant country profile.
- **Art. 49 derogation?** → Art. 49 assessment path (load `art49-derogations.md`). Balanced framing; document justification.
- **Art. 46 tool** (SCCs, BCRs, ad hoc, codes, certifications) → Full TIA required → proceed to Step 1.

## Assessment Pipeline (Steps 1–6)

Reference: `references/edpb-six-steps.md`. Full detail there; SKILL.md captures the key flow.

### Step 1: Know Your Transfer

Capture (from discovery, RoPA import, or direct user input): exporter, importer, country, data categories, subjects, purpose, volume, frequency, data format, onward transfers. Confirm completeness against the Required facts list in Session Setup — ask, never assume. Flag onward transfers for separate assessment.

### Step 2: Identify the Transfer Tool

Document the Chapter V mechanism: adequacy / SCCs (module) / BCRs / ad hoc / code / certification. Note execution dates and SA authorisations as relevant. If the mechanism is genuinely not yet determined (e.g. importer domicile still unconfirmed), record `mechanism: unknown` rather than guessing a plausible one — see Sign-off below; it is allowed in a draft but must be resolved before sign-off.

**SCC vintage check (mandatory when mechanism = sccs):** confirm the clauses are the 2021 set (Commission Implementing Decision (EU) 2021/914 of 4 June 2021). The earlier sets (Decision 2001/497/EC, Decision 2010/87/EU) were repealed from 27 September 2021 and could not be relied on for any transfer from 27 December 2022 onward (Art. 4 of the 2021 Decision). No execution date on file, or a contract still citing an old set, is an open unknown to record — never assume the clauses were updated.

**After identifying the primary mechanism:** Ask "Could any Art. 49 derogation apply as a primary or alternative basis for this transfer?" If yes → also run Art. 49 assessment as parallel/backup path.

### Step 3: Assess Third-Country Law and Practices

Load the relevant country profile. Three blocks:

**Block A — Data protection framework.** General law, SA, rights, remedies.

**Block B — Surveillance / access laws.** For each relevant law: apply the four essential guarantees (clear rules / necessary & proportionate / independent oversight / effective remedies). Rate each as adequate / concerns / insufficient.

**Block C — Practical risk assessment (Rosenthal-inspired).** Importer's request history, realistic targeting basis, plaintext access necessity, realistic authority interest in this data.

**Step 3 Conclusion — three-way fork (CNIL methodology):**

1. **Transfer tool effective** → proceed to Step 6.
2. **Transfer tool not effective, supplementary measures needed** → proceed to Step 4.
3. **Transfer tool not effective on paper, BUT no realistic basis to believe the problematic law will apply to this transfer in practice** → proceed to Step 6 with thorough, substantive justification.

Option (3) is legitimate (CNIL guide accepts it explicitly) but requires real reasoning — sector, data type, importer profile, request history — not boilerplate.

### Step 4: Supplementary Measures

Triggered when Step 3 returns conclusion (2). Load `references/supplementary-measures.md`. Auto-suggest measures matched to identified gaps. User reviews / accepts / customises. Then assess: do selected measures effectively close the gaps?

If yes → proceed. If no → the transfer cannot proceed as structured. Options: restructure (different importer, different country, different architecture) or suspend.

**Art. 32 boundary:** Chapter V supplementary measures are transfer-specific and stay here — they are selected against a *third-country access* gap under EDPB Recommendations 01/2020, not against general processing risk. The organisation's baseline Art. 32 security posture, and the lifecycle of any measure once adopted (ownership, implementation status, evidence, effectiveness testing), belong to `toms-art32`. Do not assess the baseline here, and do not treat an existing Art. 32 control as a supplementary measure without showing that it actually closes the identified third-country gap.

### Step 5: Implementation Action Plan

Document: measures to implement, owners, due dates, contractual amendments (SCC Annex II edits, side letters), technical changes (encryption, pseudonymisation pipelines), timeline.

### Step 6: Re-assessment Triggers

Document: standing triggers (adequacy review dates, DPF fragility), event-driven (new law, SA action, importer government request, certification change), periodic (12-month default, shorter for high-risk). Set the next review date.

### Sign-off: unknown mechanisms and conditional proceed

- **`mechanism: unknown`** is an honest placeholder when the Chapter V
  basis genuinely isn't determined yet — never guess a plausible mechanism
  to fill the field. It is allowed in a draft assessment (validator:
  warning) but **blocks sign-off**: the transfer basis must be documented
  before Assessor + DPO sign-off (validator: rejection once sign-off is
  complete).
- **`decision: proceed_with_conditions`** applies when Step 4 measures are
  sufficient in principle but not all implemented yet. It requires a
  recorded `conditions[]` ledger (id, text, status `open`/`met`, and
  evidence + date once met). The assessment stays **conditional, not
  complete**, until every condition is recorded `met` with evidence — and
  per EDPB Recommendations 01/2020 (supplementary measures must be *in
  place* before the transfer, not merely promised), **the transfer must
  not start while any condition is open**. A plain `decision: proceed` is
  only valid once every required supplementary measure has
  `implementation_status: implemented`; if any measure is still `planned`
  or `in_progress`, use `proceed_with_conditions` or finish implementing
  first. Once every condition is met, finalise the decision to `proceed`
  rather than leaving it at `proceed_with_conditions` indefinitely.

## Outputs

Four deliverables (the user picks what they need):

1. **Markdown TIA Report** — in-session preview. Sections mirror Steps 1–6.
2. **.docx Formal TIA Document** — for the compliance file. Uses `references/tia-template.md` structure with CNIL-style tables, cover page, sign-off block (assessor + DPO), annex with country profile summary.
3. **JSON Interchange Sidecar** — delta file conforming to `interchange-inbound-schema.json` **v2.0**, mandatory whenever `ropa_delta.emitted` is set true (DELTA-FILE-REQUIRED, non-overridable — a claimed emission with no real, resolvable delta file blocks validation). Patches only `tia_ref` and `tia_date`, where `tia_date` is the TIA's completion date (`step5_6.sign_off.dpo.date`) and `tia_ref` matches `cover.tia_ref` exactly (DELTA-SHAPE, non-overridable). Emit `add` for both leaves — `add` upserts, so there is no first-write/later-write distinction and no need to read RoPA's current values. Declare an `expected_post_state` precondition; a mismatch rejects the whole delta. TIA status, next-review date, and supplementary-measure detail remain in the TIA artifact and human-readable delta context — those paths are outside RoPA's allowed-path set and emitting them rejects the delta. When requested, the delta lands in `skills/ropa-workspace/<org-slug>/inbound/`. See `references/interchange-delta.md`.
4. **Transfer Risk Summary** — one-page executive overview for batch assessments. Per-transfer row: destination, mechanism, verdict, key risk, measures. No numerical scores.

## Cross-Skill Integration

**Inbound from RoPA:** Read sidecar (`<org-slug>-ropa-sidecar.json`) → filter entries with third-country transfers → pre-populate Step 1 → track `activity_id` UUIDs.

**Outbound to RoPA (optional):** When the user wants to return results to a RoPA, emit one delta file per assessed transfer (see Output #3) — a TIA remains complete and usable without this exchange, but once `ropa_delta.emitted` is set true, the delta becomes mandatory and non-overridable (DELTA-FILE-REQUIRED, DELTA-SHAPE). The delta is owned by RoPA after writing.

**Article 32 handoff (`toms-art32`):** route to the `toms-art32` skill when the work moves off the Chapter V question — an accepted supplementary measure that now needs an owner, an implementation status and evidence (Step 5); a question about whether encryption or pseudonymisation is *appropriate to the risk* generally rather than effective against government access specifically; or the Decision 2021/914 **Annex II** TOM text, which `toms-art32` generates from assessed, export-eligible state. Record the transfer-specific reasoning in the TIA; do not build a control catalogue or effectiveness-testing regime here.

**DPIA trigger:** If Step 3 reveals high-risk processing (Art. 9 special categories + systematic monitoring + third-country risk), flag for the user: "Consider whether a DPIA is required under Art. 35. This transfer's risk profile may meet DPIA threshold criteria." Do NOT auto-trigger DPIA Sentinel — just flag.

## Machine-Readable Artefacts (Portfolio Standard)

Every TIA carries a JSON **assessment-record sidecar** alongside the .docx —
schema at `references/tia-sidecar-schema.json` (data-format 1.1 — additive
over 1.0; both `tia_schema_version` values validate). The
deterministic validator checks documentation completeness and internal
consistency, never the substantive correctness of a legal conclusion:

```bash
uv run skills/tia/validator/validate.py <sidecar.json> [--format json] [--delta <delta.json>] \
    [--emit-core-artefact <core.json>]
```

Exit 0 = not blocked, 1 = blocked, 2 = unreadable input. Blocking (rejection)
rules: SCHEMA-0, TIA-REQUIRED, TQ-CRITERIA, STEP1-COMPLETE, ART49-DOC,
STEP4-ROWS, SIGNOFF-GATE, MECH-ENUM, STEP3-CONCLUSION, BLOCKB-RATINGS,
CONCL2-MEASURES, EFFECT-BLOCKS-PROCEED, DELTA-SHAPE, DELTA-FILE-REQUIRED. Two rules are
conditionally blocking: **MECHANISM-UNKNOWN** (`mechanism: unknown` —
warning while the assessment is a draft, rejection once Assessor + DPO
sign-off is complete) and **DECISION-CONDITIONS** (rejection for a plain
`proceed` with any supplementary measure not yet `implemented`, or for
`proceed_with_conditions` with no recorded `conditions[]`; otherwise a
non-blocking warning listing open conditions, or suggesting the decision
be finalised once every condition is `met`). **REVIEW-DATE** is a warning
rule except for a negative interval — `next_review_date` before
`cover.date` — which it rejects. Other warning rules: DPF-EVIDENCE,
SRC-FRESH, ONWARD-CHILD, SIGNOFF-INDEPENDENCE
(assessor and DPO sign-off are the same person). A rejection can be
overridden with a recorded reason in the sidecar's `overrides[]` — EXCEPT
`SIGNOFF-GATE` (no RoPA delta emission without complete Assessor + DPO
sign-off, ever), `DELTA-FILE-REQUIRED` (the delta file itself must be real
and named correctly — tolerating ropa's own documented move of the file
into an `applied/` tray, same filename only), and `DELTA-SHAPE` (its two
patches must be exactly right) — none of the three interchange gates can
be talked around.
`--emit-core-artefact` writes the portfolio
core artefact (skill-artefact-1.1 schema, `subject.type: "transfer"`) for any
sibling skill to read as a file — no orchestrator, no Python import.
Citation currency lives in `sources.lock.json` (checked by rule `SRC-FRESH`).

## Legal Precision Points

These are areas where Claude's training knowledge may be imprecise. Always apply these rules:

1. **A TIA is only required for Art. 46 transfers.** Adequacy (Art. 45) and Art. 49 derogations do not require a TIA — but each needs its own documentation (adequacy: decision ref + conditions; Art. 49: justification + applicable sub-provision).

2. **"Transfer" has no legal definition in the GDPR.** EDPB Guidelines 05/2021 define three cumulative criteria. Direct collection from data subject ≠ transfer (Example 1). Remote access from third country by processor = transfer (Example 11). Employee on business trip accessing own employer's data ≠ transfer (Example 8). When a criterion fails, what else still applies depends on *which* one: if criterion 1 fails, the GDPR does not govern this processing at all (Art. 5/24/32 are simply not engaged by it); if criterion 2 or 3 fails, the exporter remains subject to the GDPR under Art. 3 (criterion 1 is met), so Art. 5/24/32 do stay mandatory per Guidelines 05/2021 Section 4 — see `transfer-qualification.md`.

3. **Onward transfers need separate assessment.** Each hop in the chain (controller → processor → sub-processor in third country) is a separate transfer under Chapter V and requires its own analysis.

4. **The DPF is not blanket US adequacy.** Only covers organisations that are (a) subject to FTC/DoT jurisdiction AND (b) actively DPF-certified. Always verify current certification at dataprivacyframework.gov. Non-certified US recipients need SCCs + TIA per `country-profiles/us-non-dpf.md`.

5. **DPF political fragility is a live risk.** The DPF rests on EO 14086 (executive-branch construct). It can be rescinded by a future US administration. For long-term transfers, maintain SCCs as a fallback alongside DPF reliance.

6. **Adequacy decisions can have conditions and expiry dates.** Japan: supplementary rules apply. UK: renewed Dec 2025, valid until 27 Dec 2031 (joint Commission/EDPB review before any renewal). Canada: PIPEDA-regulated organisations only. Republic of Korea: PIPA-regulated only. Document conditions; track review dates.

7. **Art. 49 is not statutorily limited to "last resort."** That framing is EDPB guidance (Guidelines 2/2018), not statute. OLG München (21 U 3882/25 e, 11.05.2026) accepted Art. 49(1)(b) for routine transfers by a global service where the contract is inherently international. CJEU rapporteur Judge von Danwitz has indicated Art. 49 may cover more transfer scenarios than the EDPB acknowledges. Document which position the practitioner is relying on; both are defensible.

8. **"Necessary for contract performance" means the transfer is necessary, not just the contract.** But where the service is inherently cross-border (OLG München), transfer and contract are intertwined. Document the inherently international nature of the service.

9. **Supplementary measures must be effective, not just present.** Encryption with exporter-held keys only helps if the importer does NOT need to decrypt. A challenge clause only helps if the importer has a realistic legal avenue. Document the effectiveness assessment for each measure, including "when NOT effective" conditions.

10. **The "no reason to believe" escape valve is legitimate but must be documented.** CNIL Step 3 conclusion option (3) — transfer tool not effective on paper, but no realistic basis to believe the problematic law will apply — requires substantive justification (sector, data type, importer profile, request history), not boilerplate assertion.

11. **SCCs cannot be modified.** Only optional clauses can be filled in; parties can be added via the docking clause (Clause 7). Supplementary measures sit alongside the SCCs (typically in Annex II or a side agreement), not inside the SCC text.

12. **The controller is responsible even when the processor initiates the transfer.** Per EDPB Guidelines 05/2021 Example 7: where a processor transfers to a sub-processor in a third country, the controller remains responsible under Art. 28 and Chapter V.

13. **EU subsidiaries of third-country companies can trigger transfer issues without an actual transfer.** EDPB Guidelines 05/2021 Example 12: if the EU processor is subject to extraterritorial surveillance law (e.g., the CLOUD Act via its US parent), compliance with a government access request would *become* a transfer. Assess this under Art. 28 before engaging the processor.

14. **A TIA must be done BEFORE the transfer begins.** Per Schrems II and EDPB Recommendations 01/2020, the assessment is a pre-condition for an Art. 46 transfer. Retrospective TIAs for existing transfers are common in practice but represent a compliance gap; document the gap and close it.

15. **Re-assessment is not optional.** Art. 46 mechanisms require ongoing monitoring. Legislative changes (new surveillance law), case law (Schrems III when it lands), SA enforcement actions in the recipient country, importer's receipt of a government access request, and political developments (DPF rescission risk) all trigger re-evaluation. Default periodic review: 12 months.

16. **Pre-2021 SCCs are not a valid mechanism any more, full stop.** Decision 2001/497/EC and Decision 2010/87/EU were repealed with effect from 27 September 2021; contracts executed on them could be relied on only until 27 December 2022 (Commission Implementing Decision (EU) 2021/914, Art. 4). There is no "grandfathering" past that date — any SCCs relied on today must be the 2021 modules 1–4 set. Always confirm the vintage at Step 2; do not assume a contract described only as "our SCCs" is current.

## References

- GDPR Chapter V (Arts. 44–49)
- CJEU C-311/18 (Schrems II)
- EDPB Recommendations 01/2020 v2.0 (supplementary measures)
- EDPB Recommendations 02/2020 (essential guarantees)
- EDPB Guidelines 05/2021 v2.0 (Art. 3 / Chapter V interplay)
- EDPB Guidelines 2/2018 (Art. 49 derogations)
- CNIL TIA Guide (final version, January 2025)
- OLG München, 21 U 3882/25 e (11.05.2026)
- Implementing Decision (EU) 2023/1795 (EU-US DPF)
- Rosenthal EU SCC TIA Toolbox (v1.10, patched September 2025)

Full citations in `references/sources.md`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
