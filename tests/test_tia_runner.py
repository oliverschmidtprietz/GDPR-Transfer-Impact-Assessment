"""Runner contract: RUNNER-0 fail-closed, never-raise, override machinery,
report 2.0 envelope. Uses synthetic rules registered directly into RULES."""
import json
import sys
from pathlib import Path

import jsonschema
import pytest

TIA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TIA_ROOT / "validator"))

from tia_validator import registry                              # noqa: E402
from tia_validator.findings import Finding                      # noqa: E402
from tia_validator.runner import (                              # noqa: E402
    Context, NON_OVERRIDABLE, validate, to_findings_json)

REPORT_SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "standards" / "schemas"
     / "findings-report-2.0.schema.json").read_text(encoding="utf-8"))


def _ctx():
    return Context(schema_path=TIA_ROOT / "references" / "tia-sidecar-schema.json",
                   references_dir=TIA_ROOT / "references")


@pytest.fixture()
def clean_registry():
    # Clear IN PLACE: runner.py binds `from .registry import RULES`, so
    # rebinding registry.RULES (monkeypatch.setattr) would leave the runner
    # reading the original dict and this fixture would test nothing.
    saved = dict(registry.RULES)
    registry.RULES.clear()
    yield registry.RULES
    registry.RULES.clear()
    registry.RULES.update(saved)


def _register(rules_dict, rule_id, severity, findings_fn):
    spec = registry.RuleSpec(id=rule_id, severity=severity, category="test",
                             description="synthetic", spec_anchor="test")
    rules_dict[rule_id] = (spec, findings_fn)


def _rejection(rule_id):
    return lambda sidecar, ctx: [Finding(
        rule_id=rule_id, category="test", severity="rejection",
        message="synthetic rejection", spec_anchor="test")]


def test_empty_registry_fails_closed(clean_registry):
    result = validate({}, _ctx())
    assert result.status == "failed"
    assert result.findings[0].rule_id == "RUNNER-0"


def test_a_raising_rule_becomes_a_rejection_finding(clean_registry):
    def boom(sidecar, ctx):
        raise KeyError("boom")
    _register(clean_registry, "T-BOOM", "rejection", boom)
    result = validate({}, _ctx())
    assert result.status == "failed"
    assert any(f.rule_id == "T-BOOM" and f.severity == "rejection"
               and "KeyError" in f.message for f in result.findings)


def test_override_opens_the_gate_and_keeps_the_finding(clean_registry):
    _register(clean_registry, "T-REJ", "rejection", _rejection("T-REJ"))
    sidecar = {"overrides": [{"rule_id": "T-REJ", "reason": "accepted residual risk",
                              "recorded_by": "dpo", "recorded_at": "2026-08-09"}]}
    result = validate(sidecar, _ctx())
    assert result.status == "passed_with_override"
    f = next(f for f in result.findings if f.rule_id == "T-REJ")
    assert f.severity == "rejection"                       # never silently downgraded
    assert "[overridden: accepted residual risk]" in f.message


def test_unoverridden_rejection_still_fails(clean_registry):
    _register(clean_registry, "T-REJ", "rejection", _rejection("T-REJ"))
    _register(clean_registry, "T-REJ2", "rejection", _rejection("T-REJ2"))
    sidecar = {"overrides": [{"rule_id": "T-REJ", "reason": "r",
                              "recorded_by": "x", "recorded_at": "2026-08-09"}]}
    assert validate(sidecar, _ctx()).status == "failed"


def test_signoff_gate_override_is_refused(clean_registry):
    assert "SIGNOFF-GATE" in NON_OVERRIDABLE
    _register(clean_registry, "SIGNOFF-GATE", "rejection", _rejection("SIGNOFF-GATE"))
    sidecar = {"overrides": [{"rule_id": "SIGNOFF-GATE", "reason": "please",
                              "recorded_by": "x", "recorded_at": "2026-08-09"}]}
    result = validate(sidecar, _ctx())
    assert result.status == "failed"                        # still gates
    assert any(f.rule_id == "OVR-REFUSED" and f.severity == "warning"
               for f in result.findings)


def test_override_without_reason_is_not_applied(clean_registry):
    _register(clean_registry, "T-REJ", "rejection", _rejection("T-REJ"))
    sidecar = {"overrides": [{"rule_id": "T-REJ", "reason": "",
                              "recorded_by": "x", "recorded_at": "2026-08-09"}]}
    assert validate(sidecar, _ctx()).status == "failed"


def test_override_missing_audit_fields_is_not_applied(clean_registry):
    # The self-licensing loop (amendment 2026-08-11): an entry with no
    # recorded_by/recorded_at must never open the gate.
    _register(clean_registry, "T-REJ", "rejection", _rejection("T-REJ"))
    sidecar = {"overrides": [{"rule_id": "T-REJ", "reason": "r"}]}
    assert validate(sidecar, _ctx()).status == "failed"


def test_schema0_override_is_refused(clean_registry):
    assert "SCHEMA-0" in NON_OVERRIDABLE
    _register(clean_registry, "SCHEMA-0", "rejection", _rejection("SCHEMA-0"))
    sidecar = {"overrides": [{"rule_id": "SCHEMA-0", "reason": "looks fine",
                              "recorded_by": "dpo", "recorded_at": "2026-08-09"}]}
    result = validate(sidecar, _ctx())
    assert result.status == "failed"                        # still gates
    assert any(f.rule_id == "OVR-REFUSED" for f in result.findings)


def test_a_crashed_rule_cannot_be_overridden(clean_registry):
    def boom(sidecar, ctx):
        raise KeyError("boom")
    _register(clean_registry, "T-BOOM", "rejection", boom)
    sidecar = {"overrides": [{"rule_id": "T-BOOM", "reason": "r",
                              "recorded_by": "x", "recorded_at": "2026-08-09"}]}
    result = validate(sidecar, _ctx())
    assert result.status == "failed"
    assert any(f.rule_id == "OVR-REFUSED" and "crash" in f.message
               for f in result.findings)


def test_stale_override_warns(clean_registry):
    _register(clean_registry, "T-OK", "warning", lambda sidecar, ctx: [])
    sidecar = {"overrides": [{"rule_id": "NEVER-FIRED", "reason": "r",
                              "recorded_by": "x", "recorded_at": "2026-08-09"}]}
    result = validate(sidecar, _ctx())
    assert any(f.rule_id == "OVR-STALE" and f.severity == "warning"
               for f in result.findings)
    assert result.status == "passed_with_warnings"


def test_report_envelope_validates_against_2_0(clean_registry):
    _register(clean_registry, "T-OK", "warning", lambda sidecar, ctx: [])
    result = validate({}, _ctx())
    envelope = to_findings_json(result, skill_version="9.9")  # synthetic — never the live version (Global Constraints)
    jsonschema.validate(envelope, REPORT_SCHEMA,
                        format_checker=jsonschema.FormatChecker())
    assert envelope["skill"] == "tia"
    assert envelope["report_schema_version"] == "2.0"
