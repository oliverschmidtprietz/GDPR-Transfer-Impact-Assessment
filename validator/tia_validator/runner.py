"""Runner: fail-closed, never-raise, override machinery, report 2.0.

Override design (spec 2026-08-09 §5.2 — tia-new; NOT a ropa copy, ropa's
--draft is a CLI boolean logged out-of-band): overrides come from the
sidecar's overrides[] entries. An applied override keeps the finding at
severity "rejection" (a findings-level consumer stays conservative) and
appends the recorded reason to the message; only the status/exit-code
path opens. SIGNOFF-GATE is excluded in code, not convention: the frozen
v2.0 delta cannot carry an override marker, so an overridden emission
would be indistinguishable in RoPA's records from a signed one.
SCHEMA-0 and crashed rules are likewise non-overridable (amendment
2026-08-11): a broken override must never license the document carrying
it, and a crash finding reports a broken check, not an accepted risk.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .findings import Finding
from .registry import RULES

SKILL_NAME = "tia"
VALIDATOR_VERSION = "v0.1.0"
NON_OVERRIDABLE = frozenset({"SIGNOFF-GATE", "SCHEMA-0"})
_BLOCKING = {"rejection"}


@dataclass
class Context:
    schema_path: Path
    references_dir: Path
    mode: str = "internal"
    artefact_path: str = "(in-memory)"
    delta: Optional[dict] = None            # parsed --delta payload (rules 6/16)
    # True iff --delta was supplied on the CLI, independent of what it parsed
    # to. Needed because a JSON `null` payload also parses to Python None,
    # which would otherwise be indistinguishable from "no --delta flag at
    # all" (round 2 fix): auto-set True whenever `delta` is not None, so
    # every existing direct-dict Context(...) construction is unaffected;
    # the CLI is the only caller that must set it explicitly for the
    # delta-parses-to-null edge case.
    delta_provided: bool = False
    sources_lock_override: Optional[dict] = None   # fixture testing (rule 15)

    def __post_init__(self):
        if self.delta is not None:
            self.delta_provided = True


@dataclass
class Result:
    status: str
    summary: dict
    findings: List[Finding]
    mode: str
    validated_at: str
    artefact_path: str
    validator_version: str = VALIDATOR_VERSION
    report_schema_version: str = "2.0"


def _now() -> str:
    return (datetime.now(timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _valid_overrides(sidecar: dict) -> dict:
    """rule_id -> reason for FULLY well-formed overrides[] entries: all four
    fields (rule_id, reason, recorded_by, recorded_at) present and non-empty.
    A partial entry is never applied — it is also a SCHEMA-0 violation, and
    SCHEMA-0 is non-overridable, so a broken override cannot license the
    document that carries it (amendment 2026-08-11).

    Adversarial review finding 3 (tia's share): a top-level `overrides`
    that is present but not a list (e.g. `overrides: 42`) used to reach
    `for entry in sidecar.get("overrides") or []` and raise TypeError on a
    non-iterable value, before any rule ran — no findings report, no
    artefact, just a traceback. A malformed `overrides` shape is instead
    treated as "no valid overrides" here; SCHEMA-0 still reports the shape
    violation as a normal rejection finding once the rule loop runs."""
    out = {}
    raw = sidecar.get("overrides") if isinstance(sidecar, dict) else None
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        fields = [entry.get(k) for k in ("rule_id", "reason",
                                         "recorded_by", "recorded_at")]
        if all(isinstance(v, str) and v.strip() for v in fields):
            out[entry["rule_id"]] = entry["reason"].strip()
    return out


def validate(sidecar: dict, ctx: Context,
             rule_filter: Optional[set] = None) -> Result:
    findings: List[Finding] = []
    if not RULES:
        findings.append(Finding(
            rule_id="RUNNER-0", category="runner", severity="rejection",
            message="No rules are registered — the rule registry is empty, so "
                    "nothing was actually validated. Import tia_validator.rules "
                    "before calling validate(); importing tia_validator.runner "
                    "alone does not.",
            spec_anchor="docs/standards/PORTFOLIO-STANDARD.md#2",
            fix_hint="Add `import tia_validator.rules` (or use validate.py, "
                     "which does this) before calling validate()."))
        return Result(status="failed",
                      summary={"rejections": 1, "warnings": 0, "info": 0,
                               "rules_evaluated": 0},
                      findings=findings, mode=ctx.mode,
                      validated_at=_now(), artefact_path=ctx.artefact_path)

    rules_evaluated = 0
    crashed: set = set()   # rule ids that raised — their findings are never overridable
    for rid, (spec, fn) in RULES.items():
        if rule_filter and rid not in rule_filter:
            continue
        rules_evaluated += 1
        try:
            findings.extend(fn(sidecar, ctx) or [])
        except Exception as exc:  # a rule must never crash the run (standard §2)
            crashed.add(rid)
            findings.append(Finding(
                rule_id=rid, category=spec.category, severity="rejection",
                message=f"Rule {rid} raised {type(exc).__name__}: {exc}",
                spec_anchor=spec.spec_anchor,
                fix_hint="Internal: a rule raised on this input; the data likely "
                         "violates a structural assumption reported by SCHEMA-0."))

    overrides = _valid_overrides(sidecar)
    fired_rejections = {f.rule_id for f in findings if f.severity == "rejection"}

    processed: List[Finding] = []
    overridden_ids = set()
    for f in findings:
        if (f.severity == "rejection" and f.rule_id in overrides
                and f.rule_id not in NON_OVERRIDABLE
                and f.rule_id not in crashed):
            overridden_ids.add(f.rule_id)
            processed.append(dataclasses.replace(
                f, message=f"{f.message} [overridden: {overrides[f.rule_id]}]"))
        else:
            processed.append(f)
    findings = processed

    for rule_id in sorted(set(overrides) & (NON_OVERRIDABLE | crashed)
                          & fired_rejections):
        if rule_id in crashed:
            why = (f"rule {rule_id} crashed on this input — a crash finding "
                   "reports a broken check, not an accepted risk, and cannot "
                   "be overridden")
        elif rule_id == "SCHEMA-0":
            why = ("SCHEMA-0 is non-overridable: overriding schema "
                   "conformance would disable the check that detects a "
                   "malformed override entry")
        else:
            why = (f"{rule_id} is non-overridable (the frozen v2.0 delta "
                   "cannot carry an override marker)")
        findings.append(Finding(
            rule_id="OVR-REFUSED", category="override", severity="warning",
            message=f"Override of {rule_id} refused: {why}. "
                    "The rejection still gates.",
            spec_anchor="references/tia-sidecar-schema.json#overrides"))
    for rule_id in sorted(set(overrides) - fired_rejections):
        findings.append(Finding(
            rule_id="OVR-STALE", category="override", severity="warning",
            message=f"overrides[] entry for {rule_id} matches no firing "
                    "rejection — stale, points at nothing.",
            spec_anchor="references/tia-sidecar-schema.json#overrides",
            fix_hint=f"Remove the stale overrides[] entry for {rule_id}."))

    standing = [f for f in findings if f.severity == "rejection"
                and f.rule_id not in overridden_ids]
    has_rejection = any(f.severity in _BLOCKING for f in findings)
    has_warning = any(f.severity == "warning" for f in findings)
    if standing:
        status = "failed"
    elif has_rejection:
        status = "passed_with_override"
    elif has_warning:
        status = "passed_with_warnings"
    else:
        status = "passed"

    summary = {
        "rejections": sum(1 for f in findings if f.severity == "rejection"),
        "warnings": sum(1 for f in findings if f.severity == "warning"),
        "info": sum(1 for f in findings if f.severity == "info"),
        "rules_evaluated": rules_evaluated,
    }
    return Result(status=status, summary=summary, findings=findings,
                  mode=ctx.mode, validated_at=_now(),
                  artefact_path=ctx.artefact_path)


def to_findings_json(result: Result, *, skill_version: str) -> dict:
    """Serialize a Result into the portfolio findings-report 2.0 envelope."""
    return {
        "report_schema_version": result.report_schema_version,
        "status": result.status,
        "skill": SKILL_NAME,
        "skill_version": skill_version,
        "validator_version": result.validator_version,
        "validated_at": result.validated_at,
        "artefact_path": result.artefact_path,
        "mode": result.mode,
        "summary": result.summary,
        "findings": [f.to_dict() for f in result.findings],
    }
