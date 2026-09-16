"""Enum and consistency rules 7-12 and 16 (MECH-ENUM, STEP3-CONCLUSION,
BLOCKB-RATINGS, CONCL2-MEASURES, EFFECT-BLOCKS-PROCEED, ONWARD-CHILD,
DELTA-SHAPE) plus the DELTA-REF-MISSING warning (amendment 2026-08-11) —
spec §5.1 rows 7-12/16.

Documentation-not-correctness still applies: these rules check that the
sidecar's own fields agree with each other (or with a fixed enum), never
whether the underlying legal conclusion is right. All rules are pure
functions (sidecar, ctx) -> list[Finding) and tolerate arbitrarily malformed
input via .get() chains / isinstance guards — they must never raise.

Rule 12 (ONWARD-CHILD) is a warning, not a rejection — author ruling at spec
review 2026-08-09 (design spec §5.1 row 12, §12): an onward transfer whose
child assessment isn't linked yet warns, it does not block, because the
child assessment may legitimately not exist yet when the parent is assessed.

Rule 16 (DELTA-SHAPE) is deliberately thin: it checks the five frozen
envelope facts of a supplied --delta payload locally, at the one place the
repo's interchange contract tests never run. It must NOT re-assert the full
acceptance check — that stays ropa's job (interchange-inbound-schema.json:7).
"""
import re

from ..findings import Finding
from ..registry import rule
from .completeness import _signoff_complete

_SPEC_MECH = "references/edpb-six-steps.md#step-2"
_SPEC_STEP3 = "references/tia-template.md#section-3"
_SPEC_BLOCKB = "references/tia-template.md#block-b"
_SPEC_CONCL2 = "references/tia-template.md#section-4"
_SPEC_EFFECT = "references/tia-template.md#section-4"
_SPEC_ONWARD = "SKILL.md#legal-precision-points"
_SPEC_DELTA_SHAPE = "references/interchange-delta.md#canonical-ropa-fields-and-write-semantics"
_SPEC_DELTA_REF = "references/interchange-delta.md#producer-side-responsibilities"
_SPEC_MECHANISM_UNKNOWN = "SKILL.md#legal-precision-points"
_SPEC_DECISION_CONDITIONS = "references/tia-template.md#section-4"

_MECHANISMS = {"adequacy", "sccs", "bcrs", "ad_hoc", "code_of_conduct",
               "certification", "art49", "unknown"}
_CONCLUSIONS = {"1", "2", "3"}
_BLOCKB_KEYS = ("legality_clarity", "necessity_proportionality",
                "oversight", "redress")
_BLOCKB_RATINGS = {"adequate", "concerns", "insufficient"}
_DELTA_PATH_RE = re.compile(r"^/transfers/[0-9]+/(tia_ref|tia_date)$")
_DELTA_OPS = {"add", "replace"}


def _non_empty_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


@rule(id="MECH-ENUM", severity="rejection", category="enum",
      description="step2.mechanism is missing or not one of the seven "
                  "recognised Art. 46/45/49 mechanisms.",
      spec_anchor=_SPEC_MECH)
def mech_enum(sidecar, ctx):
    step2 = sidecar.get("step2") if isinstance(sidecar, dict) else None
    step2 = step2 if isinstance(step2, dict) else {}
    mechanism = step2.get("mechanism")
    if mechanism not in _MECHANISMS:
        return [Finding(
            rule_id="MECH-ENUM", category="enum", severity="rejection",
            message=f"step2.mechanism {mechanism!r} is missing or not one "
                    f"of {sorted(_MECHANISMS)}.",
            spec_anchor=_SPEC_MECH, field="mechanism")]
    return []


@rule(id="MECHANISM-UNKNOWN", severity="warning", category="consistency",
      description="step2.mechanism 'unknown' is an honest not-yet-determined "
                  "basis: allowed (warning) while the assessment is "
                  "unsigned, but escalates to a rejection once Assessor + "
                  "DPO sign-off is complete — the transfer basis must be "
                  "documented before sign-off (author ruling R-unknown, "
                  "2026-09-15, adversarial review finding 11).",
      spec_anchor=_SPEC_MECHANISM_UNKNOWN)
def mechanism_unknown(sidecar, ctx):
    step2 = sidecar.get("step2") if isinstance(sidecar, dict) else None
    step2 = step2 if isinstance(step2, dict) else {}
    if step2.get("mechanism") != "unknown":
        return []

    step5_6 = sidecar.get("step5_6") if isinstance(sidecar, dict) else None
    signed = _signoff_complete(step5_6)
    if signed:
        return [Finding(
            rule_id="MECHANISM-UNKNOWN", category="consistency",
            severity="rejection",
            message="step2.mechanism is 'unknown' but Assessor + DPO "
                    "sign-off is complete — the transfer basis must be "
                    "documented before sign-off (Chapter V).",
            spec_anchor=_SPEC_MECHANISM_UNKNOWN, field="mechanism")]
    return [Finding(
        rule_id="MECHANISM-UNKNOWN", category="consistency",
        severity="warning",
        message="step2.mechanism is 'unknown' — allowed while the "
                "assessment is a draft, but the transfer basis must be "
                "documented before sign-off (Chapter V).",
        spec_anchor=_SPEC_MECHANISM_UNKNOWN, field="mechanism")]


@rule(id="STEP3-CONCLUSION", severity="rejection", category="enum",
      description="step3.conclusion in {1,2,3} with a non-empty justification.",
      spec_anchor=_SPEC_STEP3)
def step3_conclusion(sidecar, ctx):
    step3 = sidecar.get("step3") if isinstance(sidecar, dict) else None
    if not isinstance(step3, dict):
        return []

    findings = []
    if step3.get("conclusion") not in _CONCLUSIONS:
        findings.append(Finding(
            rule_id="STEP3-CONCLUSION", category="enum", severity="rejection",
            message=f"step3.conclusion {step3.get('conclusion')!r} is not "
                    "one of '1', '2', '3'.",
            spec_anchor=_SPEC_STEP3, field="conclusion"))
    if not _non_empty_str(step3.get("justification")):
        findings.append(Finding(
            rule_id="STEP3-CONCLUSION", category="enum", severity="rejection",
            message="step3.justification is missing or empty.",
            spec_anchor=_SPEC_STEP3, field="justification"))
    return findings


@rule(id="BLOCKB-RATINGS", severity="rejection", category="enum",
      description="All four step3.block_b_guarantees keys rated "
                  "adequate/concerns/insufficient.",
      spec_anchor=_SPEC_BLOCKB)
def blockb_ratings(sidecar, ctx):
    step3 = sidecar.get("step3") if isinstance(sidecar, dict) else None
    if not isinstance(step3, dict):
        return []
    guarantees = step3.get("block_b_guarantees")
    guarantees = guarantees if isinstance(guarantees, dict) else {}

    findings = []
    for key in _BLOCKB_KEYS:
        if guarantees.get(key) not in _BLOCKB_RATINGS:
            findings.append(Finding(
                rule_id="BLOCKB-RATINGS", category="enum", severity="rejection",
                message=f"step3.block_b_guarantees.{key} "
                        f"{guarantees.get(key)!r} is missing or not one of "
                        f"{sorted(_BLOCKB_RATINGS)}.",
                spec_anchor=_SPEC_BLOCKB, field=key))
    return findings


@rule(id="CONCL2-MEASURES", severity="rejection", category="consistency",
      description="conclusion '2' carries a step4 block with >=1 measure "
                  "and an overall_effectiveness verdict.",
      spec_anchor=_SPEC_CONCL2)
def concl2_measures(sidecar, ctx):
    step3 = sidecar.get("step3") if isinstance(sidecar, dict) else None
    step3 = step3 if isinstance(step3, dict) else {}
    if step3.get("conclusion") != "2":
        return []

    step4 = sidecar.get("step4") if isinstance(sidecar, dict) else None
    if not isinstance(step4, dict):
        return [Finding(
            rule_id="CONCL2-MEASURES", category="consistency", severity="rejection",
            message="conclusion '2' requires a step4 block, which is absent.",
            spec_anchor=_SPEC_CONCL2, field="step4")]

    findings = []
    measures = step4.get("measures")
    if not isinstance(measures, list) or len(measures) == 0:
        findings.append(Finding(
            rule_id="CONCL2-MEASURES", category="consistency", severity="rejection",
            message="conclusion '2' requires step4.measures to be non-empty.",
            spec_anchor=_SPEC_CONCL2, field="measures"))
    if not _non_empty_str(step4.get("overall_effectiveness")):
        findings.append(Finding(
            rule_id="CONCL2-MEASURES", category="consistency", severity="rejection",
            message="conclusion '2' requires step4.overall_effectiveness, "
                    "which is missing or empty.",
            spec_anchor=_SPEC_CONCL2, field="overall_effectiveness"))
    return findings


@rule(id="EFFECT-BLOCKS-PROCEED", severity="rejection", category="consistency",
      description="overall_effectiveness 'insufficient' forbids decision "
                  "'proceed' — the two step4 fields deliberately split apart "
                  "what the .docx template encodes in one line.",
      spec_anchor=_SPEC_EFFECT)
def effect_blocks_proceed(sidecar, ctx):
    step4 = sidecar.get("step4") if isinstance(sidecar, dict) else None
    step4 = step4 if isinstance(step4, dict) else {}
    if (step4.get("overall_effectiveness") == "insufficient"
            and step4.get("decision") == "proceed"):
        return [Finding(
            rule_id="EFFECT-BLOCKS-PROCEED", category="consistency",
            severity="rejection",
            message="step4.overall_effectiveness is 'insufficient' but "
                    "step4.decision is 'proceed' — insufficient measures "
                    "cannot license proceeding.",
            spec_anchor=_SPEC_EFFECT, field="decision")]
    return []


@rule(id="DECISION-CONDITIONS", severity="rejection", category="consistency",
      description="step4.decision 'proceed' requires every step4.measures[] "
                  "row to be implementation_status 'implemented'; "
                  "'proceed_with_conditions' requires a non-empty top-level "
                  "conditions[]. Open conditions are listed (not rejected — "
                  "the assessment is legitimately conditional); once every "
                  "condition is 'met', the finding suggests finalising the "
                  "decision to 'proceed' (author ruling R-conditions, "
                  "2026-09-15, adversarial review finding 12).",
      spec_anchor=_SPEC_DECISION_CONDITIONS)
def decision_conditions(sidecar, ctx):
    step4 = sidecar.get("step4") if isinstance(sidecar, dict) else None
    step4 = step4 if isinstance(step4, dict) else {}
    decision = step4.get("decision")
    measures = step4.get("measures")
    measures = measures if isinstance(measures, list) else []

    if decision == "proceed":
        not_implemented = sum(
            1 for m in measures
            if isinstance(m, dict) and m.get("implementation_status") != "implemented")
        if not_implemented:
            return [Finding(
                rule_id="DECISION-CONDITIONS", category="consistency",
                severity="rejection",
                message=f"step4.decision is 'proceed' but {not_implemented} "
                        "supplementary measure(s) are not yet "
                        "implementation_status 'implemented' — use "
                        "'proceed_with_conditions' or implement the "
                        "measures first.",
                spec_anchor=_SPEC_DECISION_CONDITIONS, field="decision")]
        return []

    if decision != "proceed_with_conditions":
        return []

    conditions = sidecar.get("conditions") if isinstance(sidecar, dict) else None
    conditions = conditions if isinstance(conditions, list) else []
    if not conditions:
        return [Finding(
            rule_id="DECISION-CONDITIONS", category="consistency",
            severity="rejection",
            message="step4.decision is 'proceed_with_conditions' but "
                    "conditions[] is missing or empty.",
            spec_anchor=_SPEC_DECISION_CONDITIONS, field="conditions")]

    open_conditions = [c for c in conditions
                       if isinstance(c, dict) and c.get("status") == "open"]
    if open_conditions:
        ids = ", ".join(str(c.get("id", "?")) for c in open_conditions)
        return [Finding(
            rule_id="DECISION-CONDITIONS", category="consistency",
            severity="warning",
            message=f"step4.decision is 'proceed_with_conditions' with "
                    f"{len(open_conditions)} open condition(s): {ids}. The "
                    "transfer must not start, and the assessment stays "
                    "conditional (not complete), until each is recorded "
                    "'met' with evidence (EDPB Recommendations 01/2020: "
                    "measures in place before transfer).",
            spec_anchor=_SPEC_DECISION_CONDITIONS, field="conditions")]

    return [Finding(
        rule_id="DECISION-CONDITIONS", category="consistency",
        severity="warning",
        message="step4.decision is 'proceed_with_conditions' but every "
                "conditions[] entry is 'met' — finalise the decision to "
                "'proceed'.",
        spec_anchor=_SPEC_DECISION_CONDITIONS, field="decision")]


@rule(id="ONWARD-CHILD", severity="warning", category="consistency",
      description="An onward transfer ('yes') carries a non-empty "
                  "child_assessment_ref. Warning only — the child "
                  "assessment may legitimately not exist yet when the "
                  "parent is assessed (author ruling 2026-08-09).",
      spec_anchor=_SPEC_ONWARD)
def onward_child(sidecar, ctx):
    step1 = sidecar.get("step1") if isinstance(sidecar, dict) else None
    step1 = step1 if isinstance(step1, dict) else {}
    onward = step1.get("onward_transfers")
    onward = onward if isinstance(onward, dict) else {}
    if onward.get("present") != "yes":
        return []
    if not _non_empty_str(onward.get("child_assessment_ref")):
        return [Finding(
            rule_id="ONWARD-CHILD", category="consistency", severity="warning",
            message="step1.onward_transfers.present is 'yes' but "
                    "child_assessment_ref is missing or empty.",
            spec_anchor=_SPEC_ONWARD, field="child_assessment_ref")]
    return []


@rule(id="DELTA-SHAPE", severity="rejection", category="interchange",
      description="Supplied --delta carries the five frozen envelope facts "
                  "and only tia_ref/tia_date add|replace patches. Thin, "
                  "point-of-use shape check — not a re-assertion of the "
                  "full ropa acceptance check.",
      spec_anchor=_SPEC_DELTA_SHAPE)
def delta_shape(sidecar, ctx):
    if not ctx.delta_provided:
        return []
    if not isinstance(ctx.delta, dict):
        # Round 2 fix: name the shape problem plainly rather than silently
        # coercing to {} and letting the generic "missing source_skill/..."
        # findings below stand in for it — still a thin shape check, not an
        # expansion of rule 16's remit.
        kind = "null" if ctx.delta is None else type(ctx.delta).__name__
        return [Finding(
            rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
            message=f"--delta must be a JSON object; got {kind}.",
            spec_anchor=_SPEC_DELTA_SHAPE)]
    delta = ctx.delta

    findings = []
    if delta.get("schema_version") != "2.0":
        findings.append(Finding(
            rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
            message=f"delta.schema_version {delta.get('schema_version')!r} "
                    "!= '2.0'.",
            spec_anchor=_SPEC_DELTA_SHAPE, field="schema_version"))
    for envelope_field in ("source_skill", "produced_at", "target_activity_id"):
        if not _non_empty_str(delta.get(envelope_field)):
            findings.append(Finding(
                rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
                message=f"delta.{envelope_field} is missing or empty.",
                spec_anchor=_SPEC_DELTA_SHAPE, field=envelope_field))

    patches = delta.get("patches")
    if not isinstance(patches, list) or len(patches) == 0:
        findings.append(Finding(
            rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
            message="delta.patches is missing, not an array, or empty.",
            spec_anchor=_SPEC_DELTA_SHAPE, field="patches"))
        return findings

    for idx, patch in enumerate(patches):
        if not isinstance(patch, dict):
            findings.append(Finding(
                rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
                message=f"delta.patches[{idx}] is not an object.",
                spec_anchor=_SPEC_DELTA_SHAPE, entry_type="patch",
                entry_id=str(idx)))
            continue
        path = patch.get("path")
        if not isinstance(path, str) or not _DELTA_PATH_RE.match(path):
            findings.append(Finding(
                rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
                message=f"delta.patches[{idx}].path {path!r} is not "
                        "/transfers/<n>/tia_ref or /transfers/<n>/tia_date.",
                spec_anchor=_SPEC_DELTA_SHAPE, entry_type="patch",
                entry_id=str(idx), field="path"))
        if patch.get("op") not in _DELTA_OPS:
            findings.append(Finding(
                rule_id="DELTA-SHAPE", category="interchange", severity="rejection",
                message=f"delta.patches[{idx}].op {patch.get('op')!r} is "
                        "not 'add' or 'replace'.",
                spec_anchor=_SPEC_DELTA_SHAPE, entry_type="patch",
                entry_id=str(idx), field="op"))
    return findings


@rule(id="DELTA-REF-MISSING", severity="warning", category="consistency",
      description="ropa_delta.emitted is true but delta_ref is missing or "
                  "empty — an emission claim pointing at no file.",
      spec_anchor=_SPEC_DELTA_REF)
def delta_ref_missing(sidecar, ctx):
    ropa_delta = sidecar.get("ropa_delta") if isinstance(sidecar, dict) else None
    ropa_delta = ropa_delta if isinstance(ropa_delta, dict) else {}
    if ropa_delta.get("emitted") is True and not _non_empty_str(ropa_delta.get("delta_ref")):
        return [Finding(
            rule_id="DELTA-REF-MISSING", category="consistency", severity="warning",
            message="ropa_delta.emitted is true but delta_ref is missing "
                    "or empty.",
            spec_anchor=_SPEC_DELTA_REF, field="delta_ref")]
    return []
