import json
import sys
from pathlib import Path

TIA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TIA_ROOT / "validator"))

import tia_validator.rules                                      # noqa: E402,F401
from tia_validator.runner import Context, validate              # noqa: E402

FIXTURES = TIA_ROOT / "validator" / "fixtures" / "must_pass"


def _ctx(**kw):
    return Context(schema_path=TIA_ROOT / "references" / "tia-sidecar-schema.json",
                   references_dir=TIA_ROOT / "references", **kw)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fired(result):
    return {f.rule_id for f in result.findings}


def test_all_must_pass_fixtures_have_no_rejections():
    for name in ("minimal-signed.json", "adequacy-fast-track.json",
                 "art49-derogation.json", "proceed-with-conditions.json"):
        result = validate(load_fixture(name), _ctx())
        assert result.summary["rejections"] == 0, (name, fired(result))


def test_the_must_fail_fixture_rejects_on_decision_conditions():
    fixture_path = (TIA_ROOT / "validator" / "fixtures" / "must_fail"
                    / "DECISION-CONDITIONS__proceed-with-planned-measures.json")
    doc = json.loads(fixture_path.read_text(encoding="utf-8"))
    result = validate(doc, _ctx())
    assert "DECISION-CONDITIONS" in fired(result)
    assert result.summary["rejections"] > 0
    assert result.status == "failed"


def test_schema0_fires_on_a_schema_violation():
    doc = load_fixture("minimal-signed.json")
    doc["cover"]["org_slug"] = "Not A Slug"
    assert "SCHEMA-0" in fired(validate(doc, _ctx()))


def test_tia_required_fires_when_art46_mechanism_lacks_step3():
    doc = load_fixture("minimal-signed.json")
    del doc["step3"]
    del doc["step4"]
    assert "TIA-REQUIRED" in fired(validate(doc, _ctx()))


def test_tia_required_fires_when_adequacy_lacks_the_adequacy_record():
    doc = load_fixture("adequacy-fast-track.json")
    doc["step2"]["adequacy"] = None
    assert "TIA-REQUIRED" in fired(validate(doc, _ctx()))


def test_tq_criteria_fires_on_unnamed_failing_criterion():
    doc = load_fixture("minimal-signed.json")
    doc["transfer_qualification"]["criterion_2"]["met"] = False
    assert "TQ-CRITERIA" in fired(validate(doc, _ctx()))       # failing_criterion still null


def test_step1_complete_fires_per_empty_field():
    doc = load_fixture("minimal-signed.json")
    doc["step1"]["purpose"] = ""
    doc["step1"]["data_categories"] = []
    result = validate(doc, _ctx())
    step1 = [f for f in result.findings if f.rule_id == "STEP1-COMPLETE"]
    assert {f.field for f in step1} == {"purpose", "data_categories"}


def test_art49_doc_fires_per_missing_field():
    doc = load_fixture("art49-derogation.json")
    doc["step2"]["art49"]["risk_acknowledgement"] = ""
    assert "ART49-DOC" in fired(validate(doc, _ctx()))


def test_step4_rows_fires_on_an_incomplete_row():
    doc = load_fixture("minimal-signed.json")
    doc["step4"]["measures"][0]["addresses_gap"] = ""
    assert "STEP4-ROWS" in fired(validate(doc, _ctx()))


def test_signoff_gate_fires_when_emission_claimed_without_dpo_signoff():
    doc = load_fixture("minimal-signed.json")
    doc["ropa_delta"] = {"emitted": True, "delta_ref": "delta.json"}
    doc["step5_6"]["sign_off"]["dpo"] = {"name": None, "date": None}
    result = validate(doc, _ctx())
    assert "SIGNOFF-GATE" in fired(result)
    assert result.status == "failed"


def test_signoff_gate_fires_when_delta_supplied_without_signoff():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["dpo"] = {"name": None, "date": None}
    result = validate(doc, _ctx(delta={"schema_version": "2.0", "patches": []}))
    assert "SIGNOFF-GATE" in fired(result)


def test_signoff_gate_does_not_fire_without_emission_claim():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["dpo"] = {"name": None, "date": None}
    assert "SIGNOFF-GATE" not in fired(validate(doc, _ctx()))


def test_signoff_gate_still_blocks_a_null_content_delta_with_an_overridden_delta_shape():
    # Exploit chain closed (round 3 fix): a --delta file whose content is
    # the JSON literal `null` parses to Python None. Rule 6 used to key off
    # `ctx.delta is not None`, so it missed this as an emission claim even
    # though DELTA-SHAPE (rule 16) does fire for it. DELTA-SHAPE is
    # overridable (only SIGNOFF-GATE and SCHEMA-0 sit in NON_OVERRIDABLE),
    # so a practitioner could supply a null-content delta, override
    # DELTA-SHAPE, leave ropa_delta.emitted false and the sign-off
    # incomplete -- and the run would pass. That is precisely the state
    # rule 6 was made non-overridable to prevent.
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["dpo"] = {"name": None, "date": None}
    doc["ropa_delta"] = {"emitted": False, "delta_ref": None}
    doc["overrides"] = [{
        "rule_id": "DELTA-SHAPE",
        "reason": "known-bad delta content, re-emitting shortly",
        "recorded_by": "J. Doe",
        "recorded_at": "2026-08-11",
    }]
    # ctx.delta=None + delta_provided=True is exactly how validate.py
    # constructs Context for a --delta file whose content is `null`.
    result = validate(doc, _ctx(delta=None, delta_provided=True))
    assert "SIGNOFF-GATE" in fired(result)
    assert result.status == "failed"
    assert not any(f.rule_id == "SIGNOFF-GATE" and "[overridden:" in f.message
                   for f in result.findings)


# ---------------------------------------------------------------------------
# SIGNOFF-INDEPENDENCE
# ---------------------------------------------------------------------------

def test_signoff_independence_same_person_is_a_warning():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["assessor"]["name"] = "Alex Example"
    doc["step5_6"]["sign_off"]["dpo"]["name"] = "alex example"  # case/space-insensitive match
    result = validate(doc, _ctx())
    findings = [f for f in result.findings if f.rule_id == "SIGNOFF-INDEPENDENCE"]
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert result.status == "passed_with_warnings"  # never blocks


def test_signoff_independence_different_people_no_finding():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["assessor"]["name"] = "Alex Example"
    doc["step5_6"]["sign_off"]["dpo"]["name"] = "Kim Muster"
    result = validate(doc, _ctx())
    assert "SIGNOFF-INDEPENDENCE" not in fired(result)


def test_signoff_independence_missing_names_no_finding():
    doc = load_fixture("minimal-signed.json")
    doc["step5_6"]["sign_off"]["assessor"]["name"] = ""
    result = validate(doc, _ctx())
    assert "SIGNOFF-INDEPENDENCE" not in fired(result)
