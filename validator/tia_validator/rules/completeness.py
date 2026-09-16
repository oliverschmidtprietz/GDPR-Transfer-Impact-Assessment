"""Completeness rules 1-6 (TIA-REQUIRED, TQ-CRITERIA, STEP1-COMPLETE,
ART49-DOC, STEP4-ROWS, SIGNOFF-GATE) — spec §5.1 rows 1-6.

Documentation-not-correctness is absolute: every rule here tests whether the
sidecar's record of the six EDPB steps is complete and internally consistent
with itself, never whether the underlying legal conclusion is right. All
rules are pure functions (sidecar, ctx) -> list[Finding] and tolerate
arbitrarily malformed input via .get() chains / isinstance guards — they
must never raise (the runner's never-raise wrapper would catch a raise, but
a rule that *relies* on that catch is wrong, per the task brief).
"""
from ..findings import Finding
from ..registry import rule

_SPEC_TIA_REQUIRED = "SKILL.md#legal-precision-points"
_SPEC_TQ_CRITERIA = "references/transfer-qualification.md#the-three-cumulative-criteria"
_SPEC_STEP1 = "references/edpb-six-steps.md#step-1"
_SPEC_ART49 = "references/art49-derogations.md#documentation-duties"
_SPEC_STEP4 = "references/tia-template.md#section-4"
_SPEC_SIGNOFF = "references/interchange-delta.md#producer-side-responsibilities"

_ART46 = {"sccs", "bcrs", "ad_hoc", "code_of_conduct", "certification"}

_STEP1_STRING_FIELDS = (
    "exporter", "importer", "roles", "destination_country",
    "importer_sector", "purpose", "volume", "frequency",
)
_STEP1_ARRAY_FIELDS = ("data_categories", "data_subjects", "formats")

_ART49_FIELDS = (
    "derogation", "primary_or_fallback", "justification",
    "edpb_view_considered", "broader_view_considered",
    "documentation_evidence", "risk_acknowledgement",
)

_MEASURE_FIELDS = ("type", "addresses_gap", "implementation_status", "effectiveness")


def _non_empty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _non_empty_array(v) -> bool:
    return isinstance(v, list) and len(v) > 0


def _signoff_complete(step5_6) -> bool:
    """True iff all four of assessor/dpo x name/date are non-empty strings."""
    sign_off = (step5_6 or {}).get("sign_off") if isinstance(step5_6, dict) else None
    if not isinstance(sign_off, dict):
        return False
    for who in ("assessor", "dpo"):
        entry = sign_off.get(who)
        if not isinstance(entry, dict):
            return False
        if not _non_empty_str(entry.get("name")) or not _non_empty_str(entry.get("date")):
            return False
    return True


@rule(id="TIA-REQUIRED", severity="rejection", category="completeness",
      description="Art. 46 mechanism carries a Step 3 assessment block; "
                  "adequacy/Art. 49 carry the matching alternative record.",
      spec_anchor=_SPEC_TIA_REQUIRED)
def tia_required(sidecar, ctx):
    step2 = sidecar.get("step2") if isinstance(sidecar, dict) else None
    step2 = step2 if isinstance(step2, dict) else {}
    mechanism = step2.get("mechanism")

    if mechanism in _ART46:
        step3 = sidecar.get("step3") if isinstance(sidecar, dict) else None
        if not isinstance(step3, dict):
            return [Finding(
                rule_id="TIA-REQUIRED", category="completeness", severity="rejection",
                message=f"mechanism {mechanism!r} requires a step3 assessment "
                        "block, which is absent.",
                spec_anchor=_SPEC_TIA_REQUIRED, field="step3")]
    elif mechanism == "adequacy":
        if not isinstance(step2.get("adequacy"), dict):
            return [Finding(
                rule_id="TIA-REQUIRED", category="completeness", severity="rejection",
                message="mechanism 'adequacy' requires step2.adequacy, "
                        "which is absent.",
                spec_anchor=_SPEC_TIA_REQUIRED, field="step2.adequacy")]
    elif mechanism == "art49":
        if not isinstance(step2.get("art49"), dict):
            return [Finding(
                rule_id="TIA-REQUIRED", category="completeness", severity="rejection",
                message="mechanism 'art49' requires step2.art49, which is absent.",
                spec_anchor=_SPEC_TIA_REQUIRED, field="step2.art49")]
    return []


@rule(id="TQ-CRITERIA", severity="rejection", category="completeness",
      description="All three EDPB transfer-qualification criteria addressed, "
                  "or one named failing criterion.",
      spec_anchor=_SPEC_TQ_CRITERIA)
def tq_criteria(sidecar, ctx):
    tq = sidecar.get("transfer_qualification") if isinstance(sidecar, dict) else None
    tq = tq if isinstance(tq, dict) else {}
    failing = tq.get("failing_criterion")

    findings = []
    parsed = {}
    for n in ("1", "2", "3"):
        c = tq.get(f"criterion_{n}")
        if isinstance(c, dict) and isinstance(c.get("met"), bool):
            parsed[n] = c["met"]
        else:
            findings.append(Finding(
                rule_id="TQ-CRITERIA", category="completeness", severity="rejection",
                message=f"criterion_{n} is missing or lacks a boolean 'met'.",
                spec_anchor=_SPEC_TQ_CRITERIA, field=f"criterion_{n}"))

    for n, met in parsed.items():
        if met is False and failing != n:
            findings.append(Finding(
                rule_id="TQ-CRITERIA", category="completeness", severity="rejection",
                message=f"criterion_{n} is not met, but failing_criterion "
                        f"does not name '{n}'.",
                spec_anchor=_SPEC_TQ_CRITERIA, field="failing_criterion"))
        elif met is True and failing == n:
            findings.append(Finding(
                rule_id="TQ-CRITERIA", category="completeness", severity="rejection",
                message=f"failing_criterion names criterion_{n}, but "
                        f"criterion_{n}.met is true.",
                spec_anchor=_SPEC_TQ_CRITERIA, field="failing_criterion"))
    return findings


@rule(id="STEP1-COMPLETE", severity="rejection", category="completeness",
      description="All 12 Step-1 fields present and non-empty.",
      spec_anchor=_SPEC_STEP1)
def step1_complete(sidecar, ctx):
    step1 = sidecar.get("step1") if isinstance(sidecar, dict) else None
    step1 = step1 if isinstance(step1, dict) else {}

    findings = []
    for f in _STEP1_STRING_FIELDS:
        if not _non_empty_str(step1.get(f)):
            findings.append(Finding(
                rule_id="STEP1-COMPLETE", category="completeness", severity="rejection",
                message=f"step1.{f} is missing or empty.",
                spec_anchor=_SPEC_STEP1, field=f))
    for f in _STEP1_ARRAY_FIELDS:
        if not _non_empty_array(step1.get(f)):
            findings.append(Finding(
                rule_id="STEP1-COMPLETE", category="completeness", severity="rejection",
                message=f"step1.{f} is missing or empty.",
                spec_anchor=_SPEC_STEP1, field=f))

    onward = step1.get("onward_transfers")
    present = onward.get("present") if isinstance(onward, dict) else None
    if not _non_empty_str(present):
        findings.append(Finding(
            rule_id="STEP1-COMPLETE", category="completeness", severity="rejection",
            message="step1.onward_transfers.present is missing or empty.",
            spec_anchor=_SPEC_STEP1, field="onward_transfers"))
    return findings


@rule(id="ART49-DOC", severity="rejection", category="completeness",
      description="mechanism == art49 carries all 7 derogation-template fields.",
      spec_anchor=_SPEC_ART49)
def art49_doc(sidecar, ctx):
    step2 = sidecar.get("step2") if isinstance(sidecar, dict) else None
    step2 = step2 if isinstance(step2, dict) else {}
    if step2.get("mechanism") != "art49":
        return []

    art49 = step2.get("art49")
    if not isinstance(art49, dict):
        return []  # TIA-REQUIRED already reports the absent block

    findings = []
    for f in _ART49_FIELDS:
        if not _non_empty_str(art49.get(f)):
            findings.append(Finding(
                rule_id="ART49-DOC", category="completeness", severity="rejection",
                message=f"step2.art49.{f} is missing or empty.",
                spec_anchor=_SPEC_ART49, field=f))
    return findings


@rule(id="STEP4-ROWS", severity="rejection", category="completeness",
      description="Every step4.measures[] row carries type, addresses_gap, "
                  "implementation_status and effectiveness.",
      spec_anchor=_SPEC_STEP4)
def step4_rows(sidecar, ctx):
    step4 = sidecar.get("step4") if isinstance(sidecar, dict) else None
    if not isinstance(step4, dict):
        return []
    measures = step4.get("measures")
    if not isinstance(measures, list):
        return []

    findings = []
    for idx, row in enumerate(measures):
        if not isinstance(row, dict):
            findings.append(Finding(
                rule_id="STEP4-ROWS", category="completeness", severity="rejection",
                message=f"step4.measures[{idx}] is not an object.",
                spec_anchor=_SPEC_STEP4, entry_type="measure", entry_id=str(idx)))
            continue
        missing = [f for f in _MEASURE_FIELDS if not _non_empty_str(row.get(f))]
        if missing:
            findings.append(Finding(
                rule_id="STEP4-ROWS", category="completeness", severity="rejection",
                message=f"step4.measures[{idx}] is missing: {', '.join(missing)}.",
                spec_anchor=_SPEC_STEP4, entry_type="measure", entry_id=str(idx),
                field=missing[0]))
    return findings


@rule(id="SIGNOFF-GATE", severity="rejection", category="completeness",
      description="No ropa interchange-delta emission without complete "
                  "Assessor + DPO sign-off. Non-overridable.",
      spec_anchor=_SPEC_SIGNOFF)
def signoff_gate(sidecar, ctx):
    ropa_delta = sidecar.get("ropa_delta") if isinstance(sidecar, dict) else None
    ropa_delta = ropa_delta if isinstance(ropa_delta, dict) else {}
    # ctx.delta_provided, not `ctx.delta is not None` (round 3 fix): a
    # --delta file whose content is the JSON literal `null` also parses to
    # Python None, which would otherwise be indistinguishable from "no
    # --delta flag at all" and let this non-overridable gate be bypassed
    # via an overridden DELTA-SHAPE finding on exactly that input.
    emission_claimed = bool(ropa_delta.get("emitted")) or ctx.delta_provided
    if not emission_claimed:
        return []

    step5_6 = sidecar.get("step5_6") if isinstance(sidecar, dict) else None
    if _signoff_complete(step5_6):
        return []

    return [Finding(
        rule_id="SIGNOFF-GATE", category="completeness", severity="rejection",
        message="ropa interchange delta emission is claimed (ropa_delta.emitted "
                "or --delta supplied) without complete Assessor + DPO sign-off.",
        spec_anchor=_SPEC_SIGNOFF)]


@rule(id="SIGNOFF-INDEPENDENCE", severity="warning", category="completeness",
      description="Assessor and DPO sign-off should be different people. "
                  "Warning only — small organisations may legitimately "
                  "overlap, but role independence is the intent of the "
                  "sign-off gate (GM-008 friction F-05).",
      spec_anchor=_SPEC_SIGNOFF)
def signoff_independence(sidecar, ctx):
    step5_6 = sidecar.get("step5_6") if isinstance(sidecar, dict) else None
    sign_off = step5_6.get("sign_off") if isinstance(step5_6, dict) else None
    sign_off = sign_off if isinstance(sign_off, dict) else {}
    assessor = sign_off.get("assessor")
    dpo = sign_off.get("dpo")
    a = (assessor.get("name") or "") if isinstance(assessor, dict) else ""
    d = (dpo.get("name") or "") if isinstance(dpo, dict) else ""
    a, d = a.strip().lower(), d.strip().lower()
    if a and d and a == d:
        return [Finding(
            rule_id="SIGNOFF-INDEPENDENCE", category="completeness",
            severity="warning",
            message="step5_6.sign_off assessor and dpo are the same person; "
                    "the sign-off gate expects independent roles.",
            spec_anchor=_SPEC_SIGNOFF, field="sign_off")]
    return []
